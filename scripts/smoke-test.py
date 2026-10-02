#!/usr/bin/env python3
"""Credential-free smoke tests for an installed cf package."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

package = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix="cf-smoke-", dir=os.environ.get("TMPDIR")) as home:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLOUDFLARE_")}
    env.update(HOME=home, XDG_CONFIG_HOME=home, CI="true")
    def run(binary, *args):
        result = subprocess.run([str(package / "bin" / binary), *args],
                                cwd=home, env=env, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(f"{binary} {args}: {result.returncode}\n{result.stdout}\n{result.stderr}")
        return result.stdout
    for binary in ("cf", "cloudflare"):
        version = run(binary, "--version")
        assert "1.0.0-beta.5" in version, version
        print(f"PASS {binary} --version")
    help_text = run("cf", "--help")
    assert "Cloudflare" in help_text and "Commands" in help_text, help_text
    print("PASS cf --help")
    results = json.loads(run("cf", "cli", "search", "dns"))
    assert isinstance(results, list) and results, results
    assert all(isinstance(r.get("command"), str) for r in results), results
    print(f"PASS cf cli search dns ({len(results)} results)")
