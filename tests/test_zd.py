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

    def run_cli(self, extra=(), effect=None):
        with patch.object(zd, "checked", side_effect=self.checked), patch.object(zd.subprocess, "run") as run:
            run.side_effect = effect or (lambda *a, **kw: subprocess.CompletedProcess(a[0], 0))
            status = zd.main(self.arguments(*extra))
            return status, run

    def test_immutable_image_reference(self):
        self.assertTrue(zd.IMAGE.fullmatch("ghcr.io/z-shell/zd@" + IMAGE_ID))
        self.assertFalse(zd.IMAGE.fullmatch("ghcr.io/z-shell/zd:latest"))

    def test_source_symlink_escape_is_rejected(self):
        (self.source / "escape").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "escapes"):
            zd.content_identity(self.source, ["escape"])

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

    def test_timeout_stops_only_named_owned_container(self):
        def timeout(arguments, **kwargs):
            if arguments[1] == "run":
                raise subprocess.TimeoutExpired(arguments, 1)
            self.assertEqual(arguments[:4], ["docker", "stop", "--time", "2"])
            self.assertTrue(arguments[4].startswith("zd-"))
            return subprocess.CompletedProcess(arguments, 0)
        status, calls = self.run_cli(effect=timeout)
        self.assertEqual(status, 124)
        self.assertEqual(calls.call_count, 2)

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
