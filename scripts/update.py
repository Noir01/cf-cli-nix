#!/usr/bin/env python3
"""Refresh the published cf npm package and its Nix dependency cache."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def run(argv, cwd=ROOT):
    result = subprocess.run(argv, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE)
    return result.stdout.strip()


def metadata(version):
    url = "https://registry.npmjs.org/cf/" + urllib.parse.quote(version, safe="")
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit 0 if current, 1 if an update exists, 2 on errors")
    parser.add_argument("--version", help="Use a specific npm version instead of the latest dist-tag")
    args = parser.parse_args()
    package_file = ROOT / "package.nix"
    original = package_file.read_text()
    match = re.search(r'  version = "([^"]+)";', original)
    if match is None:
        raise ValueError("Missing package version")
    current = match.group(1)
    info = metadata(args.version or "latest")
    version = info["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError(f"Unexpected version: {version!r}")
    print(f"Packaged: {current}; upstream target: {version}", flush=True)
    if args.check:
        return int(current != version)
    if current == version:
        print("Already current; no changes.")
        return 0
    # Keep temporary artifacts under TMPDIR when it is configured.
    with tempfile.TemporaryDirectory(prefix="cf-update-", dir=os.environ.get("TMPDIR")) as scratch:
        work = Path(scratch)
        url = info["dist"]["tarball"]
        if not url.startswith("https://registry.npmjs.org/cf/-/"):
            raise ValueError(f"Unexpected tarball URL: {url}")
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        algorithm, expected = info["dist"]["integrity"].split("-", 1)
        if algorithm != "sha512" or base64.b64encode(hashlib.sha512(data).digest()).decode() != expected:
            raise ValueError("npm tarball integrity verification failed")
        archive = work / "cf.tgz"
        archive.write_bytes(data)
        with tarfile.open(archive) as tar:
            # Only metadata is needed to resolve runtime dependencies. Do not
            # extract or execute upstream files or development scripts here.
            manifest = tar.extractfile("package/package.json")
            if manifest is None:
                raise ValueError("Tarball has no package.json")
            source = json.load(manifest)
        if source["version"] != version or source["name"] != "cf":
            raise ValueError("Tarball metadata does not match npm metadata")
        source.pop("devDependencies", None)
        source.pop("scripts", None)
        (work / "package.json").write_text(json.dumps(source, indent=2) + "\n")
        run(["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=work)
        # Resolve the prefetcher from the flake's pinned nixpkgs, not the host's
        # channel. This keeps dependency hash generation consistent with builds.
        expr = 'let f = builtins.getFlake (toString ./.); p = import f.inputs.nixpkgs { system = builtins.currentSystem; }; in p.prefetch-npm-deps'
        prefetch = run(["nix", "build", "--impure", "--no-link", "--print-out-paths", "--expr", expr])
        deps_hash = run([str(Path(prefetch) / "bin/prefetch-npm-deps"), str(work / "package-lock.json")])
        if not re.fullmatch(r"sha256-[A-Za-z0-9+/]{43}=", deps_hash):
            raise ValueError(f"Unexpected dependency hash: {deps_hash!r}")
        tar_hash = "sha256-" + base64.b64encode(hashlib.sha256(data).digest()).decode()
        updated = original.replace(f'  version = "{current}";', f'  version = "{version}";', 1)
        updated, count = re.subn(r'    hash = "[^"]+";', f'    hash = "{tar_hash}";', updated)
        if count != 1:
            raise ValueError("Expected exactly one tarball hash")
        updated, count = re.subn(r'  npmDepsHash = "[^"]+";', f'  npmDepsHash = "{deps_hash}";', updated)
        if count != 1:
            raise ValueError("Expected exactly one npm dependency hash")
        # Leave the repository untouched until fetching and hashing succeeds.
        (ROOT / "package-lock.json").write_bytes((work / "package-lock.json").read_bytes())
        package_file.write_text(updated)
        print(f"Updated to {version}. Run nix build and scripts/smoke-test.py before publishing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Update failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(2)
