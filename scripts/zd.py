#!/usr/bin/env python3
"""Local and CI execution contract for the controlled zd images (Python 3.10+)."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid


IMAGE = re.compile(r"(?:[a-zA-Z0-9][a-zA-Z0-9._/:\-]*@)?sha256:[0-9a-f]{64}\Z")
STARTED_MARKER = "execution-started.json"
RESERVED_ENV = {"HOME", "ZDOTDIR", "PATH", "LANG", "LC_ALL", "TMPDIR", "ZD_SOURCE_REVISION", "ZD_INPUT_DIR", "ZD_RUNNER_IMAGE", "ZD_OUTPUT_DIR"}


def checked(arguments, **kwargs):
    return subprocess.check_output(arguments, text=True, **kwargs).strip()


def container_absent(name):
    """True when gone, False when present, None when the engine cannot answer."""
    result = subprocess.run(["docker", "ps", "--all", "--quiet", "--filter", f"name=^{name}$"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=30)
    if result.returncode != 0:
        return None
    return not (result.stdout or "").strip()


def remove_owned_container(name, attempts=5, delay=1.0):
    """Stop, then force-remove until absence is confirmed twice.

    Killing the Docker client can leave a container created but not started,
    which --rm never removes, or a create request still in flight.
    """
    try:
        subprocess.run(["docker", "stop", "--time", "2", name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        confirmed = 0
        for _ in range(attempts):
            subprocess.run(["docker", "rm", "--force", name],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            absent = container_absent(name)
            if absent is None:
                return "unavailable"
            confirmed = confirmed + 1 if absent else 0
            if confirmed == 2:
                return "removed"
            time.sleep(delay)
        return "remove-failed"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def source_files(source):
    """Git owns the inventory; recurse initialized submodules, omit ignored caches."""
    names = subprocess.check_output(["git", "-C", str(source), "ls-files", "--cached", "--others", "--exclude-standard", "-z"], text=True)
    result = []
    for name in sorted(set(names.split("\0")) - {""}):
        path = source / name
        if path.is_dir() and not path.is_symlink():
            top = Path(checked(["git", "-C", str(path), "rev-parse", "--show-toplevel"])).resolve()
            if top != path.resolve():
                raise ValueError(f"initialize submodule before execution: {name}")
            result.extend(name + "/" + child for child in source_files(path))
        elif path.exists() or path.is_symlink():
            result.append(name)
    return result


def content_identity(source, files):
    digest = hashlib.sha256()
    count = 0
    for relative in sorted(files):
        path = source / relative
        if not path.resolve().is_relative_to(source):
            raise ValueError(f"source symlink escapes checkout: {relative}")
        # An absolute target inside the host checkout points elsewhere once copied.
        if path.is_symlink() and os.path.isabs(os.readlink(path)):
            raise ValueError(f"source symlink has an absolute target: {relative}")
        if path.is_symlink():
            content = os.readlink(path).encode()
            kind = b"link"
        elif path.is_file():
            content = path.read_bytes()
            kind = b"file"
        else:
            raise ValueError(f"unsupported source entry: {relative}")
        digest.update(relative.encode() + b"\0" + kind + b"\0")
        digest.update(str(path.lstat().st_mode & 0o777).encode() + b"\0")
        digest.update(hashlib.sha256(content).digest())
        count += 1
    return {"tree_sha256": digest.hexdigest(), "entries": count}


def identity(source):
    """Hash copied inputs, including dirty and nonignored untracked files."""
    revision = checked(["git", "-C", str(source), "rev-parse", "HEAD"])
    return {"revision": revision, "dirty": bool(checked(["git", "-C", str(source), "status", "--porcelain"])),
            **content_identity(source, source_files(source))}


def image_identity(image, profile):
    if not IMAGE.fullmatch(image):
        raise ValueError("image must be an immutable repository@sha256:digest or local sha256:image-id")
    info = json.loads(checked(["docker", "image", "inspect", image]))[0]
    labels = info.get("Config", {}).get("Labels") or {}
    if labels.get("dev.zshell.zd.profile") != profile:
        raise ValueError("image does not declare the requested controlled zd profile")
    return {"requested": image, "id": info["Id"], "architecture": info["Architecture"],
            "os": info["Os"], "profile": profile}


def make_command(args, image):
    command = ["docker", "run", "--rm", "--init", "--name", args.container_name, "--network", args.network,
               "--user", f"{os.getuid()}:{os.getgid()}", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--tmpfs", "/work:rw,exec,mode=1777",
               "--mount", f"type=bind,src={args.source},dst=/checkout,readonly",
               "--mount", f"type=bind,src={args.output},dst=/output",
               "--env", "LANG=C.UTF-8", "--env", "LC_ALL=C.UTF-8"]
    if args.cpuset:
        if not re.fullmatch(r"[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*", args.cpuset):
            raise ValueError("invalid CPU affinity list")
        command += ["--cpuset-cpus", args.cpuset]
    for setting in args.env:
        key, separator, _ = setting.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in RESERVED_ENV:
            raise ValueError("invalid or reserved environment assignment")
        command += ["--env", setting]
    for name, fixture in args.inputs.items():
        command += ["--mount", f"type=bind,src={fixture},dst=/inputs/{name},readonly"]
    command += ["--entrypoint", "/usr/bin/python3", image["id"], "/opt/zd/zd.py", "execute",
                "--source-revision", args.source_identity["revision"], "--runner-image", image["id"], "--", *args.command]
    return command


def execute(args):
    """Container entrypoint: never interpolate the repository command into a shell."""
    workspace = Path("/work/source")
    workspace.mkdir()
    inputs = json.loads(Path("/output/input-files.json").read_text())
    for name in inputs["files"]:
        source = Path("/checkout") / name
        destination = workspace / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, destination)
    if content_identity(workspace, inputs["files"]) != inputs["content"]:
        raise ValueError("source changed during workspace copy")
    for name, fixture in inputs.get("fixtures", {}).items():
        target = Path("/work/inputs") / name
        target.mkdir(parents=True)
        for filename in fixture["files"]:
            source = Path("/inputs") / name / filename
            destination = target / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                destination.symlink_to(os.readlink(source))
            else:
                shutil.copy2(source, destination)
        if content_identity(target, fixture["files"]) != fixture["content"]:
            raise ValueError("fixture changed during workspace copy: " + name)
    home = Path("/work/home")
    home.mkdir()
    temporary = Path("/work/tmp")
    temporary.mkdir()
    environment = {key: value for key, value in os.environ.items() if key not in RESERVED_ENV}
    environment.update(HOME=str(home), ZDOTDIR=str(home), TMPDIR=str(temporary),
                       PATH="/opt/zsh/bin:/usr/local/bin:/usr/bin:/bin", LANG="C.UTF-8", LC_ALL="C.UTF-8",
                       ZD_OUTPUT_DIR="/output", ZD_SOURCE_REVISION=args.source_revision,
                       ZD_INPUT_DIR="/work/inputs", ZD_RUNNER_IMAGE=args.runner_image)
    runtime = json.loads(Path("/opt/zd/runtime.json").read_text())
    runtime["zsh_version_observed"] = checked(["/opt/zsh/bin/zsh", "--version"], env=environment)
    runtime["kernel"] = os.uname().release
    runtime["cpu_affinity"] = sorted(os.sched_getaffinity(0))
    runtime["cpu"] = next((line.partition(":")[2].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                           if line.startswith("model name")), "unavailable")
    Path("/output/runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
    shutil.copyfile("/opt/zd/packages.tsv", "/output/packages.tsv")
    # The host reads this to tell a setup failure from the workload's own exit status.
    Path("/output", STARTED_MARKER).write_text(json.dumps({"started_at_unix": time.time()}) + "\n")
    return subprocess.run(args.command, cwd=workspace, env=environment).returncode


def run(args):
    args.source = Path(args.source).resolve(strict=True)
    args.output = Path(args.output).resolve()
    if not args.source.is_dir() or args.output.is_relative_to(args.source) or args.source.is_relative_to(args.output):
        raise ValueError("output and source must be separate non-overlapping directories")
    if any("," in str(path) or "\n" in str(path) for path in [args.source, args.output]):
        raise ValueError("mount paths cannot contain commas or line breaks")
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("output directory must be empty")
    args.command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not args.command:
        raise ValueError("a repository command is required after --")
    if args.mode == "benchmark" and args.network != "none":
        raise ValueError("benchmark mode requires networking disabled")
    args.source_identity = identity(args.source)
    args.inputs = {}
    fixtures = {}
    for setting in args.input:
        name, separator, value = setting.partition("=")
        if not separator or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name) or name in args.inputs:
            raise ValueError("fixture input requires a unique name=checkout assignment")
        fixture = Path(value).resolve(strict=True)
        if "," in str(fixture) or "\n" in str(fixture) or fixture.is_relative_to(args.output) or args.output.is_relative_to(fixture):
            raise ValueError("invalid or overlapping fixture mount")
        top = Path(checked(["git", "-C", str(fixture), "rev-parse", "--show-toplevel"])).resolve()
        if top != fixture:
            raise ValueError("fixture must be a separate Git checkout")
        args.inputs[name] = fixture
        fixtures[name] = {"files": source_files(fixture), "identity": identity(fixture)}
        fixtures[name]["content"] = {key: fixtures[name]["identity"][key] for key in ["tree_sha256", "entries"]}
    image = image_identity(args.image, args.profile)
    if image["os"] != "linux":
        raise ValueError("controlled zd requires a Linux image")
    engine_arch = checked(["docker", "info", "--format", "{{.Architecture}}"])
    native_arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(engine_arch, engine_arch)
    if args.mode == "benchmark" and image["architecture"] != native_arch:
        raise ValueError("benchmark image must match the Docker host architecture; no emulation")
    args.container_name = "zd-" + uuid.uuid4().hex
    command = make_command(args, image)
    if args.dry_run:
        # Do not print caller environment values.
        print(json.dumps({"image": image, "source": args.source_identity, "mode": args.mode,
                          "network": args.network, "cpuset": args.cpuset, "command": args.command}, indent=2))
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "image": image, "source": args.source_identity,
              "mode": args.mode, "network": args.network, "cpuset": args.cpuset,
              "command": args.command, "environment_names": [s.partition("=")[0] for s in args.env],
              "fixtures": {name: spec["identity"] for name, spec in fixtures.items()},
              "container_name": args.container_name, "started_at_unix": time.time(), "status": "running"}
    (args.output / "input-files.json").write_text(json.dumps({"files": source_files(args.source),
        "content": {key: args.source_identity[key] for key in ["tree_sha256", "entries"]}, "fixtures": fixtures}) + "\n")
    path = args.output / "execution.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    try:
        with (args.output / "execution.log").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        code = result.returncode
        if not (args.output / STARTED_MARKER).is_file():
            # Workspace setup or the engine failed before the workload started.
            report["status"] = "setup-failed"
            report["container_exit_code"] = code
            code = 125
        else:
            report["status"] = "passed" if code == 0 else "failed"
    except subprocess.TimeoutExpired:
        # Killing the Docker client alone leaves its workload running.
        report["timeout_cleanup"] = remove_owned_container(args.container_name)
        if report["timeout_cleanup"] == "removed":
            code = 124
            report["status"] = "timeout"
        else:
            code = 125
            report["status"] = "cleanup-failed"
    except OSError as error:
        code = 125
        report["status"] = "unavailable"
        report["error"] = str(error)
    except KeyboardInterrupt:
        report["interrupt_cleanup"] = remove_owned_container(args.container_name)
        code = 130
        report["status"] = "interrupted"
    report.update(exit_code=code, finished_at_unix=time.time())
    # Detect concurrent source writes rather than presenting mismatched provenance.
    try:
        changed = identity(args.source) != args.source_identity or any(
            identity(args.inputs[name]) != spec["identity"] for name, spec in fixtures.items())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        report["status"] = "invalid-provenance-unavailable"
        report["error"] = str(error)
        code = report["exit_code"] = 125
    else:
        if changed:
            report["status"] = "invalid-source-changed"
            code = report["exit_code"] = 125
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"zd: {report['status']}; evidence: {args.output}")
    return code


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    local = sub.add_parser("run", help="execute a repository command in a pinned controlled image")
    local.add_argument("--image", required=True)
    local.add_argument("--profile", choices=["runtime", "module-build"], required=True)
    local.add_argument("--source", required=True)
    local.add_argument("--output", required=True)
    local.add_argument("--mode", choices=["test", "benchmark"], default="test")
    local.add_argument("--network", choices=["none", "bridge"], default="none")
    local.add_argument("--cpuset", default="")
    local.add_argument("--env", action="append", default=[])
    local.add_argument("--input", action="append", default=[], help="name=path to a prepared fixture Git checkout")
    local.add_argument("--timeout", type=int, default=900)
    local.add_argument("--dry-run", action="store_true")
    local.add_argument("command", nargs=argparse.REMAINDER)
    internal = sub.add_parser("execute", help=argparse.SUPPRESS)
    internal.add_argument("--source-revision", required=True)
    internal.add_argument("--runner-image", required=True)
    internal.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(arguments)
    try:
        if args.operation == "execute":
            args.command = args.command[1:] if args.command[:1] == ["--"] else args.command
            return execute(args)
        if args.timeout < 1:
            raise ValueError("timeout must be positive")
        return run(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"zd: {error}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    sys.exit(main())
