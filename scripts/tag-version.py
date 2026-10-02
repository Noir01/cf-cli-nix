#!/usr/bin/env python3
"""Publish an immutable lightweight version tag on the tested commit."""
import argparse
import json
import re
import subprocess
from pathlib import Path


def tag_name(version):
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", version):
        raise ValueError(f"Invalid version: {version!r}")
    return f"v{version}"


def existing_tag_sha(refs, tag, sha):
    matches = [ref for ref in refs if ref["ref"] == f"refs/tags/{tag}"]
    if not matches:
        return False
    if len(matches) != 1 or matches[0]["object"]["type"] != "commit" or matches[0]["object"]["sha"] != sha:
        raise ValueError(f"{tag} already exists on a different target; refusing to move it")
    return True


def api(path, *args):
    return json.loads(subprocess.check_output(["gh", "api", path, *args], text=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.sha):
        raise ValueError("Expected an exact commit SHA")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if head != args.sha:
        raise ValueError("Checkout does not match the tested SHA")
    commit = api(f"repos/{args.repo}/commits/{args.sha}")
    if not commit["commit"]["verification"]["verified"]:
        raise ValueError("Refusing to tag an unverified commit")
    version = json.loads(Path("package-lock.json").read_text())["version"]
    tag = tag_name(version)
    path = f"repos/{args.repo}/git"
    refs = api(f"{path}/matching-refs/tags/{tag}")
    if existing_tag_sha(refs, tag, args.sha):
        print(f"{tag} already points to {args.sha}; no changes")
        return
    if args.dry_run:
        print(f"Would create {tag} -> {args.sha}")
        return
    api(f"{path}/refs", "--method", "POST", "-f", f"ref=refs/tags/{tag}", "-f", f"sha={args.sha}")
    ref = api(f"{path}/ref/tags/{tag}")
    if not existing_tag_sha([ref], tag, args.sha):
        raise ValueError("Tag read-back failed")
    print(f"Verified {tag} -> {args.sha}")


if __name__ == "__main__":
    main()
