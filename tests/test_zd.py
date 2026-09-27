"""Execution contract checks; real Docker behavior is covered by controlled CI."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("zd", ROOT / "scripts/zd.py")
zd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zd)
IMAGE_ID = "sha256:" + "a" * 64


class ExecutionContract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "fixture").write_text("original")
        self.output = self.root / "evidence"
        self.inventory = patch.object(zd.subprocess, "check_output", return_value="fixture\0")
        self.inventory.start()
        self.addCleanup(self.inventory.stop)

    def arguments(self, *extra):
        return ["run", "--image", IMAGE_ID, "--profile", "runtime", "--source", str(self.source),
                "--output", str(self.output), *extra, "--", "zsh", "-f", "-c", 'print -r -- "$HOME"']

    def checked(self, arguments, **kwargs):
        if arguments[:3] == ["docker", "image", "inspect"]:
            return json.dumps([{"Id": IMAGE_ID, "Os": "linux", "Architecture": "amd64",
                                "Config": {"Labels": {"dev.zshell.zd.profile": "runtime"}}}])
        if arguments[:2] == ["docker", "info"]:
            return "x86_64"
        if "ls-files" in arguments:
            return "fixture\0"
        return "a" * 40 if "rev-parse" in arguments else ""

    def run_cli(self, extra=(), effect=None, started=True, checked=None):
        effect = effect or (lambda *a, **kw: subprocess.CompletedProcess(a[0], 0))
        def docker(arguments, **kwargs):
            # The container writes this marker once setup succeeds.
            if started and arguments[:2] == ["docker", "run"]:
                (self.output / zd.STARTED_MARKER).write_text("{}")
            return effect(arguments, **kwargs)
        with patch.object(zd, "checked", side_effect=checked or self.checked), \
                patch.object(zd.subprocess, "run", side_effect=docker) as run, patch.object(zd.time, "sleep"):
            status = zd.main(self.arguments(*extra))
            return status, run

    def report(self):
        return json.loads((self.output / "execution.json").read_text())

    def timeout_with_cleanup(self, listing):
        """Time out the run, then answer cleanup calls; listing returns docker ps output or None."""
        def effect(arguments, **kwargs):
            if arguments[1] == "run":
                raise subprocess.TimeoutExpired(arguments, 1)
            self.assertIn(arguments[1], {"stop", "rm", "ps"})
            self.assertTrue(any(part.startswith("zd-") or part.startswith("name=^zd-") for part in arguments))
            if arguments[1] == "ps":
                stdout = listing()
                return subprocess.CompletedProcess(arguments, 1 if stdout is None else 0, stdout=stdout or "")
            return subprocess.CompletedProcess(arguments, 0)
        return effect

    def test_immutable_image_reference(self):
        self.assertTrue(zd.IMAGE.fullmatch("ghcr.io/z-shell/zd@" + IMAGE_ID))
        self.assertFalse(zd.IMAGE.fullmatch("ghcr.io/z-shell/zd:latest"))

    def test_source_symlink_escape_is_rejected(self):
        (self.source / "escape").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "escapes"):
            zd.content_identity(self.source, ["escape"])

    def test_absolute_symlink_inside_checkout_is_rejected(self):
        # It resolves inside the host checkout but not once copied to /work/source.
        (self.source / "inside").symlink_to(self.source / "fixture")
        with self.assertRaisesRegex(ValueError, "absolute target"):
            zd.content_identity(self.source, ["inside"])

    def test_relative_symlink_inside_checkout_is_accepted(self):
        (self.source / "inside").symlink_to("fixture")
        self.assertEqual(zd.content_identity(self.source, ["inside"])["entries"], 1)

    def test_parent_symlink_cannot_expose_external_file(self):
        (self.root / "private").write_text("must not read")
        (self.source / "nested").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "escapes"):
            zd.content_identity(self.source, ["nested/private"])

    def test_emulated_benchmark_is_rejected(self):
        original = self.checked
        def architecture(arguments, **kwargs):
            result = original(arguments, **kwargs)
            if arguments[:3] == ["docker", "image", "inspect"]:
                data = json.loads(result)
                data[0]["Architecture"] = "arm64"
                return json.dumps(data)
            return result
        with patch.object(zd, "checked", side_effect=architecture), patch.object(zd.subprocess, "run") as docker:
            self.assertEqual(zd.main(self.arguments("--mode", "benchmark")), 125)
            docker.assert_not_called()

    def test_output_must_not_overwrite_previous_evidence(self):
        self.output.mkdir()
        (self.output / "raw.json").write_text("retain")
        status, docker = self.run_cli()
        self.assertEqual(status, 125)
        docker.assert_not_called()

    def test_benchmark_cannot_enable_network(self):
        status, docker = self.run_cli(["--mode", "benchmark", "--network", "bridge"])
        self.assertEqual(status, 125)
        docker.assert_not_called()

    def test_argument_boundaries_and_no_host_environment(self):
        status, docker = self.run_cli(["--env", "FIXTURE=value with spaces"])
        self.assertEqual(status, 0)
        arguments = docker.call_args.args[0]
        self.assertIn('print -r -- "$HOME"', arguments)
        self.assertIn("FIXTURE=value with spaces", arguments)
        self.assertIn("ALL", arguments)
        self.assertNotIn("--privileged", arguments)
        report = json.loads((self.output / "execution.json").read_text())
        self.assertEqual(report["environment_names"], ["FIXTURE"])
        self.assertNotIn("value with spaces", json.dumps(report))

    def test_failure_invalidates_execution_and_retains_log(self):
        status, _ = self.run_cli(effect=lambda *a, **kw: subprocess.CompletedProcess(a[0], 71))
        self.assertEqual(status, 71)
        self.assertEqual(json.loads((self.output / "execution.json").read_text())["status"], "failed")
        self.assertTrue((self.output / "execution.log").exists())

    def test_timeout_removes_only_named_owned_container(self):
        status, calls = self.run_cli(effect=self.timeout_with_cleanup(lambda: ""))
        self.assertEqual(status, 124)
        operations = [call.args[0][1] for call in calls.call_args_list]
        self.assertEqual(operations, ["run", "stop", "rm", "ps", "rm", "ps"])
        self.assertEqual(self.report()["timeout_cleanup"], "removed")

    def test_timeout_with_surviving_container_is_infrastructure_error(self):
        # A container created after the client was killed keeps reappearing in the listing.
        status, _ = self.run_cli(effect=self.timeout_with_cleanup(lambda: "abc123\n"))
        self.assertEqual(status, 125)
        self.assertEqual(self.report()["status"], "cleanup-failed")
        self.assertEqual(self.report()["timeout_cleanup"], "remove-failed")

    def test_timeout_with_unreachable_engine_is_infrastructure_error(self):
        status, _ = self.run_cli(effect=self.timeout_with_cleanup(lambda: None))
        self.assertEqual(status, 125)
        self.assertEqual(self.report()["status"], "cleanup-failed")
        self.assertEqual(self.report()["timeout_cleanup"], "unavailable")

    def test_setup_failure_is_not_a_workload_failure(self):
        status, _ = self.run_cli(effect=lambda *a, **kw: subprocess.CompletedProcess(a[0], 125), started=False)
        self.assertEqual(status, 125)
        self.assertEqual(self.report()["status"], "setup-failed")
        self.assertEqual(self.report()["container_exit_code"], 125)

    def test_workload_exit_125_after_setup_is_a_workload_failure(self):
        status, _ = self.run_cli(effect=lambda *a, **kw: subprocess.CompletedProcess(a[0], 125))
        self.assertEqual(status, 125)
        self.assertEqual(self.report()["status"], "failed")

    def test_unavailable_provenance_still_finishes_evidence(self):
        state = {"ran": False}
        def effect(arguments, **kwargs):
            state["ran"] = True
            return subprocess.CompletedProcess(arguments, 0)
        def checked(arguments, **kwargs):
            if state["ran"] and "rev-parse" in arguments:
                raise subprocess.CalledProcessError(128, arguments)
            return self.checked(arguments, **kwargs)
        status, _ = self.run_cli(effect=effect, checked=checked)
        self.assertEqual(status, 125)
        report = self.report()
        self.assertEqual(report["status"], "invalid-provenance-unavailable")
        self.assertIn("finished_at_unix", report)

    def test_concurrent_source_change_invalidates_identity(self):
        def mutate(arguments, **kwargs):
            (self.source / "fixture").write_text("changed")
            return subprocess.CompletedProcess(arguments, 0)
        status, _ = self.run_cli(effect=mutate)
        self.assertEqual(status, 125)
        self.assertEqual(json.loads((self.output / "execution.json").read_text())["status"], "invalid-source-changed")

    def test_environment_cannot_override_isolation(self):
        status, calls = self.run_cli(["--env", "HOME=/real-home"])
        self.assertEqual(status, 125)
        calls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
