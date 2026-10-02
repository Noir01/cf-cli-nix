#!/usr/bin/env python3
"""Create a signed, bot-owned cf update PR; never merge it here."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
FILES = ("package.nix", "package-lock.json")


def gh(endpoint, payload=None):
    args = ["gh", "api", endpoint]
    if payload is not None:
        args += ["--method", "POST", "--input", "-"]
    result = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                            check=True, text=True, capture_output=True)
    data = json.loads(result.stdout)
    if isinstance(data, dict) and data.get("errors"):
        raise RuntimeError(data["errors"])
    return data


def output(**values):
    for name, value in values.items():
        print(f"{name}={value}")
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a") as file:
            for name, value in values.items():
                file.write(f"{name}={value}\n")


def additions(root):
    return [{"path": name, "contents": base64.b64encode((root / name).read_bytes()).decode()}
            for name in FILES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-version", help="Exercise a real signed PR without permitting merge")
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    base = gh(f"repos/{repo}/commits/main")["sha"]
    if (not args.test_version and
            subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip() != base):
        raise RuntimeError("Checkout is not the current main revision")
    if not args.test_version:
        existing = gh(f"repos/{repo}/pulls?state=open&base=main&per_page=100")
        existing = [p for p in existing if p["head"]["ref"].startswith("automation/cf-")
                    and p["user"]["login"] == "github-actions[bot]"]
        if existing:
            raise RuntimeError("An update PR is already open; resolve it before generating another")
    command = [sys.executable, str(ROOT / "scripts/update.py")]
    if args.test_version:
        command += ["--version", args.test_version]
    subprocess.run(command, check=True, cwd=ROOT)
    changed = subprocess.check_output(["git", "diff", "--name-only"], text=True, cwd=ROOT).splitlines()
    if not changed:
        output(changed="false")
        return
    if set(changed) != set(FILES):
        raise RuntimeError(f"Unexpected changed files: {changed}")
    version = json.loads((ROOT / "package-lock.json").read_text())["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
        raise RuntimeError("Invalid version")
    prefix = "automation/test-cf-" if args.test_version else "automation/cf-"
    branch = prefix + version + "-" + os.environ["GITHUB_RUN_ID"]
    gh(f"repos/{repo}/git/refs", {"ref": "refs/heads/" + branch, "sha": base})
    query = """mutation($input: CreateCommitOnBranchInput!) {
      createCommitOnBranch(input: $input) { commit { oid } }
    }"""
    result = gh("graphql", {"query": query, "variables": {"input": {
        "branch": {"repositoryNameWithOwner": repo, "branchName": branch},
        "expectedHeadOid": base,
        "message": {"headline": f"chore: update cf to {version}"},
        "fileChanges": {"additions": additions(ROOT)},
    }}})
    sha = result["data"]["createCommitOnBranch"]["commit"]["oid"]
    commit = gh(f"repos/{repo}/commits/{sha}")
    if not commit["commit"]["verification"]["verified"]:
        raise RuntimeError("GitHub did not verify the bot commit; refusing to create PR")
    if commit["author"]["login"] != "github-actions[bot]":
        raise RuntimeError("Expected github-actions[bot] commit identity")
    pr = gh(f"repos/{repo}/pulls", {
        "title": ("TEST ONLY: " if args.test_version else "") + f"chore: update cf to {version}",
        "head": branch, "base": "main", "draft": bool(args.test_version),
        "body": "Automated npm version/hash/lockfile update. Signed by GitHub. "
                "Candidate builds run explicitly in the update workflow on all supported systems."
                + ("\n\nTEST ONLY: do not merge this PR." if args.test_version else ""),
    })
    output(changed="true", sha=sha, base=base, pr=str(pr["number"]), branch=branch)
    print(pr["html_url"])


if __name__ == "__main__":
    main()
