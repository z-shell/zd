#!/usr/bin/env python3
"""Build an exact official Zsh release, with an explicitly selected patch profile."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

RELEASES = {
    "5.8.1": "b6973520bace600b4779200269b1e5d79e5f505ac4952058c11ad5bbf0dd9919",
    "5.9": "9b8d1ecedd5b5e81fbf1918e876752a7dd948e05c1a0dba10ab863842d45acd5",
    "5.9.2": "36fa734374b44783582cec09bcd67822e2f992c779ec1624ab5596df078d2f81",
}
PATCH_COMMIT = "a3547fd4c165bd6c0c9c9d2643bd61b593f7bbaf"
PATCH_SHA = "bcac19bbbb4506ae35eee6e7873c4308aba9b86e4e6d152101e3a4c4d5265255"
PATCH_OWNER = "00d5d47783fb80c739edf89e39ae47274b9f503e"
# 5.8.1 and 5.9 look only for PCRE1, which Debian trixie does not ship.
PCRE2_RELEASES = {"5.9.2"}


def download(urls, target, digest):
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
        except OSError:
            continue
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("download digest mismatch: " + url)
        target.write_bytes(data)
        return url
    raise ValueError("release download unavailable")


def main():
    version = os.environ["ZSH_VERSION"]
    patch = os.environ["ZSH_PATCH_SET"]
    if version not in RELEASES or patch not in {"none", "trap-bounds-a3547fd4"}:
        raise ValueError("unsupported runtime profile")
    if patch != "none" and version != "5.9.2":
        raise ValueError("trap-bounds profile is only defined for Zsh 5.9.2")
    build = Path("/tmp/zsh-build")
    build.mkdir()
    artifact = build / "zsh.tar.xz"
    url = download([f"https://www.zsh.org/pub/zsh-{version}.tar.xz",
                    f"https://www.zsh.org/pub/old/zsh-{version}.tar.xz"], artifact, RELEASES[version])
    subprocess.run(["tar", "-xJf", str(artifact), "-C", str(build)], check=True)
    source = build / f"zsh-{version}"
    patches = []
    if patch != "none":
        patch_file = build / "runtime.patch"
        patch_url = f"https://raw.githubusercontent.com/z-shell/.github/{PATCH_OWNER}/actions/setup-zsh/{patch}.patch"
        download([patch_url], patch_file, PATCH_SHA)
        for dry_run in [True, False]:
            with patch_file.open() as data:
                command = ["patch", "--batch", "--forward", "--fuzz=0", "-p1"]
                if dry_run:
                    command.append("--dry-run")
                subprocess.run(command, cwd=source, stdin=data, check=True)
        patches.append({"profile": patch, "upstream_commit": PATCH_COMMIT, "sha256": PATCH_SHA,
                        "delivery_revision": PATCH_OWNER})
    cflags = "-O2"
    if version in {"5.8.1", "5.9"}:
        # Older releases use C89 definitions rejected by newer default modes.
        cflags += " -std=gnu89"
    environment = dict(os.environ, CFLAGS=cflags)
    configure = ["./configure", "--prefix=/opt/zsh", "--enable-multibyte", "--with-tcsetpgrp"]
    if version in PCRE2_RELEASES:
        configure.append("--enable-pcre")
    subprocess.run(configure, cwd=source, env=environment, check=True)
    subprocess.run(["make", "-j2"], cwd=source, check=True)
    if patch != "none":
        for suite in ["A05", "B11"]:
            subprocess.run(["make", f"TESTNUM={suite}", "check"], cwd=source, check=True)
    subprocess.run(["make", "install.bin", "install.modules", "install.fns"], cwd=source, check=True)
    observed = subprocess.check_output(["/opt/zsh/bin/zsh", "-f", "-c", 'print -r -- "$ZSH_VERSION"'], text=True).strip()
    if observed != version:
        raise ValueError("built runtime does not match requested version")
    pcre_loads = subprocess.run(["/opt/zsh/bin/zsh", "-f", "-c", "zmodload zsh/pcre"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if pcre_loads != (version in PCRE2_RELEASES):
        raise ValueError("zsh/pcre availability does not match the runtime profile")
    metadata = {"schema_version": 1, "zsh_version": version, "patch_set": patch, "patches": patches,
                "release_url": url, "release_sha256": RELEASES[version], "cflags": cflags,
                "configure": configure, "pcre": "pcre2" if pcre_loads else "unavailable",
                "compiler": subprocess.check_output(["cc", "--version"], text=True).splitlines()[0]}
    Path("/opt/zd").mkdir(exist_ok=True)
    Path("/opt/zd/runtime.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
