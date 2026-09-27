#!/usr/bin/env python3
"""Observable image qualification, including invalidation and timeout cleanup."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    common = [sys.executable, str(root / "bin/zd"), "run", "--image", args.image,
              "--profile", args.profile, "--source", str(root)]
    probe = '''import json, os, pathlib, subprocess
assert os.environ['HOME'] == '/work/home'
assert os.environ['ZDOTDIR'] == '/work/home'
assert not pathlib.Path('.git').exists()
assert pathlib.Path('AGENTS.md').is_file()
assert 'QUALIFICATION_HOST_SECRET' not in os.environ
pathlib.Path('zd-source-write-probe').write_text('only in container copy')
runtime = json.loads(pathlib.Path('/opt/zd/runtime.json').read_text())
assert subprocess.check_output(['zsh', '-f', '-c', 'print -r -- "$ZSH_VERSION"'], text=True).strip() == runtime['zsh_version']
pathlib.Path('/output/probe.json').write_text(json.dumps({'isolated': True, 'runtime': runtime}))
'''
    statuses = []
    for name, command, timeout, expected in [
        ("success", ["python3", "-c", probe], 60, 0),
        ("functional-failure", ["python3", "-c", "raise SystemExit(23)"], 60, 23),
        ("timeout", ["python3", "-c", "import time; time.sleep(60)"], 2, 124),
    ]:
        output = args.output / name
        result = subprocess.run(common + ["--output", str(output), "--timeout", str(timeout), "--", *command],
                                env=dict(__import__("os").environ, QUALIFICATION_HOST_SECRET="must-not-inherit"))
        if result.returncode != expected:
            raise AssertionError(f"{name}: expected {expected}, observed {result.returncode}")
        status = json.loads((output / "execution.json").read_text())
        assert status["exit_code"] == expected
        statuses.append({"case": name, "exit_code": expected, "status": status["status"]})
    assert not (root / "zd-source-write-probe").exists()
    # The runner's temporary named containers must be gone after normal exit and timeout.
    remaining = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True).splitlines()
    # Check these runs only, without asserting anything about another caller's containers.
    for name in ["success", "functional-failure", "timeout"]:
        log = (args.output / name / "execution.json").read_text()
        report = json.loads(log)
        assert report["status"] != "running"
        assert report["container_name"] not in remaining
    (args.output / "qualification.json").write_text(json.dumps({"cases": statuses}, indent=2) + "\n")
    print("Controlled image qualification passed")


if __name__ == "__main__":
    main()
