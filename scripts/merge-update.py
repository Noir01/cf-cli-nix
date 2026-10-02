#!/usr/bin/env python3
"""Merge only an exact, validated bot version-update candidate."""
import base64
import json
import os
import re
import subprocess
import urllib.request


def api(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", endpoint], text=True))


def normalize_package(text):
    patterns = (r'  version = "[^"]+";', r'    hash = "[^"]+";', r'  npmDepsHash = "[^"]+";')
    for pattern in patterns:
        text, count = re.subn(pattern, "PIN", text)
        if count != 1:
            raise RuntimeError("Unexpected package.nix layout")
    return text


def require_server_merge_guard(repo):
    """Refuse auto-merge unless GitHub atomically enforces the validated base."""
    rulesets = api(f"repos/{repo}/rulesets")
    for summary in rulesets:
        if summary["name"] != "Validated main updates":
            continue
        rule = api(f"repos/{repo}/rulesets/{summary['id']}")
        refs = rule.get("conditions", {}).get("ref_name", {})
        if (rule.get("enforcement") != "active" or rule.get("target") != "branch"
                # GitHub omits bypass_actors for non-admin tokens. The empty
                # bypass list is configured and verified by the maintainer;
                # reject any bypasses when GitHub exposes them to this token.
                or rule.get("bypass_actors", []) != []
                or refs.get("include") != ["refs/heads/main"] or refs.get("exclude") != []):
            continue
        for check in rule.get("rules", []):
            if check["type"] != "required_status_checks":
                continue
            params = check["parameters"]
            checks = {(c["context"], c.get("integration_id")) for c in params["required_status_checks"]}
            required = {(s, 15368) for s in ("x86_64-linux", "aarch64-linux", "aarch64-darwin")}
            if params.get("strict_required_status_checks_policy") is True and required <= checks:
                return
    raise RuntimeError("Missing strict, non-bypassable GitHub merge checks on main")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    number = os.environ["UPDATE_PR"]
    sha = os.environ["UPDATE_SHA"]
    base = os.environ["UPDATE_BASE"]
    pr = api(f"repos/{repo}/pulls/{number}")
    if (pr["state"] != "open" or pr["draft"] or pr["user"]["login"] != "github-actions[bot]"
            or not pr["head"]["ref"].startswith("automation/cf-")
            or pr["head"]["sha"] != sha or pr["head"]["repo"]["full_name"] != repo
            or pr["base"]["ref"] != "main"):
        raise RuntimeError("PR does not match the validated bot update")
    if api(f"repos/{repo}/commits/main")["sha"] != base:
        raise RuntimeError("Main changed during validation; refusing stale candidate")
    require_server_merge_guard(repo)
    commit = api(f"repos/{repo}/commits/{sha}")
    if (not commit["commit"]["verification"]["verified"]
            or commit["author"]["login"] != "github-actions[bot]"
            or [p["sha"] for p in commit["parents"]] != [base]):
        raise RuntimeError("Unexpected candidate signature, identity, or parent")
    files = api(f"repos/{repo}/pulls/{number}/files")
    if {f["filename"] for f in files} != {"package.nix", "package-lock.json"}:
        raise RuntimeError("Update modifies unexpected files")
    def content(name, ref):
        return base64.b64decode(api(f"repos/{repo}/contents/{name}?ref={ref}")["content"]).decode()
    if normalize_package(content("package.nix", base)) != normalize_package(content("package.nix", sha)):
        raise RuntimeError("Update changes package code, not just version/hash pins")
    version = json.loads(content("package-lock.json", sha))["version"]
    with urllib.request.urlopen("https://registry.npmjs.org/cf/latest", timeout=60) as response:
        latest = json.load(response)["version"]
    if version != latest:
        raise RuntimeError("Candidate is no longer npm latest")
    subprocess.run(["gh", "pr", "merge", number, "--repo", repo, "--auto", "--squash",
                    "--match-head-commit", sha], check=True)
    result = api(f"repos/{repo}/pulls/{number}")
    if result["merged"]:
        merged = api(f"repos/{repo}/commits/{result['merge_commit_sha']}")
        if not merged["commit"]["verification"]["verified"]:
            raise RuntimeError("Merged commit signature is unverified")
        print(f"Merged signed commit {result['merge_commit_sha']}")
    else:
        print("Auto-merge requested; merge is still pending")


if __name__ == "__main__":
    main()
