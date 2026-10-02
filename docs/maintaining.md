# Maintenance

## Packaging

`package.nix` pins the published npm tarball and Node.js 22. `package-lock.json` and `npmDepsHash` pin runtime dependencies. The upstream tarball references unavailable development-only dependencies; packaging removes those entries and uses the upstream CLI bundle without rebuilding it. npm install scripts are disabled; features depending on those scripts require separate testing.

Supported native CI systems: `x86_64-linux`, `aarch64-linux`, and `aarch64-darwin`. The pinned nixpkgs does not support `x86_64-darwin`. Smoke tests use an isolated home without Cloudflare credentials and exercise version, help, command search, and both app entry points. Authenticated operations and Workers local development are not verified.

## Manual updates

Requires Python 3, npm with Node.js 22+, and Nix with flakes enabled.

```sh
python3 scripts/update.py --check
python3 scripts/update.py
# Or select a published version:
python3 scripts/update.py --version 1.0.0-beta.12
nix build .#cf-cli
python3 scripts/smoke-test.py result
```

Check mode exits 0 when current, 1 when an update is available, and 2 on errors; it does not edit files. The updater verifies npm tarball integrity, resolves runtime dependencies with install scripts disabled, and computes hashes with the prefetcher from pinned nixpkgs. It updates `package.nix` and `package-lock.json` only after fetching and hashing succeeds. Build validation is separate.

## Automatic updates

`.github/workflows/update.yml` checks npm `latest` hourly. `AUTO_UPDATE_ENABLED=true` and repository auto-merge are enabled. Routine merge authorization covers only bot-owned version/hash/lockfile updates; code and workflow changes still require maintainer approval.

Candidates are created through GitHub's signing API, then explicitly built and smoke-tested on all three platforms. Workflow-token-created PRs do not normally trigger PR CI, so validation publishes required checks directly on the candidate SHA. Matching open candidates are revalidated on subsequent runs. Failed candidates remain open for inspection.

The active **Validated main updates** ruleset requires all three platform checks from GitHub Actions and up-to-date branches, with no bypass actors. `.github/main-ruleset.json` records the configuration but does not install it. The merge script refuses missing or weakened protection, unexpected files/code changes, stale bases, unverified commits, and versions no longer on npm `latest`. GitHub hides bypass settings from ordinary Actions tokens; verify them with administrator access.

The merge must complete immediately and its signed merge commit must be confirmed before dispatching main CI. This explicit dispatch is necessary because `GITHUB_TOKEN` merges do not trigger ordinary push workflows. No personal signing key is stored in Actions.

For a non-merging test, manually dispatch **Update cf** with `test_version` set to a different published version. Test PRs are drafts and never merge.

## Cache publication

The public `cf-cli` cache uses Cachix-managed signing. GitHub Actions holds a cache-scoped write token in `CACHIX_AUTH_TOKEN`; never put it in source or logs.

PR builds use the cache read-only. Each trusted main platform job uploads its exact output only after smoke tests pass, with the write token scoped to that step. It checks the output's public `.narinfo` afterward. A missing upload or token fails the job. Standard dependencies may come from `cache.nixos.org` rather than Cachix.

## Version tags

After all main platform jobs, including cache uploads, pass, CI creates a lightweight `v<upstream-version>` tag on the exact tested commit. The commit must be GitHub-verified. These refs are not separately signed annotated tags or GitHub Release pages. No moving `latest` or major-version tags are published.

Existing version tags never move. CI uses `--keep-existing` to preserve original release targets on same-version maintenance commits. Strict script mode rejects a different existing target. Newly created tags always require exact-target read-back verification.
