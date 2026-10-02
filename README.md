# cf-cli-nix

Nix flake for [Cloudflare's `cf` CLI](https://github.com/cloudflare/cf). Packages the published npm release with Node.js 22 and a pinned npm dependency cache. The CLI is currently a beta; commands may change.

## Run

From this checkout:

```sh
nix run . -- --version
nix run .#cf -- cli search dns
nix run .#cloudflare -- --version
```

For the published package, use `nix run github:Noir01/cf-cli-nix -- --version`.

## Install

In a flake-based NixOS or Home Manager configuration:

```nix
inputs.cf-cli-nix.url = "github:Noir01/cf-cli-nix";

# In your package list, where `system` is the target system:
inputs.cf-cli-nix.packages.${system}.default
```

Or add the overlay and use `pkgs.cf-cli`:

```nix
nixpkgs.overlays = [ inputs.cf-cli-nix.overlays.default ];
# environment.systemPackages = [ pkgs.cf-cli ]; # NixOS
# home.packages = [ pkgs.cf-cli ];               # Home Manager
```

Both `cf` and `cloudflare` are installed as commands.

## Updating the package

Requires Python 3, npm (Node.js 22+), and Nix with flakes enabled. The updater follows npm's `latest` dist-tag, including prereleases published to that tag.

```sh
python3 scripts/update.py --check
python3 scripts/update.py
# Or select an exact upstream version:
python3 scripts/update.py --version 1.0.0-beta.12
nix build .#cf-cli
python3 scripts/smoke-test.py result
```

Check mode returns 0 when current, 1 when an update is available, and 2 on errors. It does not edit files. The updater verifies npm's tarball integrity, resolves runtime dependencies with install scripts disabled, and computes the dependency hash using the prefetcher from our pinned nixpkgs. It updates `package.nix` and `package-lock.json` only after fetching and hashing succeeds. Package validation is a separate required step.

The hourly update workflow follows npm `latest`, creates a GitHub-signed bot PR, and explicitly builds and smoke-tests that exact candidate on all supported platforms. This does not rely on `GITHUB_TOKEN`-created PRs triggering normal PR workflows. Matching open candidates are revalidated on subsequent runs.

Automation is paused until the maintainer explicitly enables repository variable `AUTO_UPDATE_ENABLED=true` and repository auto-merge. When enabled, only bot-owned version/hash/lockfile updates from an unchanged main revision may merge after all validation jobs succeed. Test PRs are drafts and never merge. GitHub supplies the bot commit signature; no personal or dedicated signing key is stored in Actions.

GitHub's active **Validated main updates** ruleset requires all three platform checks from GitHub Actions and requires branches to be up to date before merging, with no bypass actors. The candidate workflow publishes these check runs directly on its exact SHA. This server-side requirement closes the race between our initial base check and the eventual merge. The updater refuses to request a merge if the strict required-check rule is absent or weakened. `.github/main-ruleset.json` records the intended repository configuration; committing that file does not itself install the rule. Admin-only bypass settings must remain empty (GitHub hides that field from ordinary Actions tokens).

To exercise the pipeline without merging, manually run the **Update cf** workflow with `test_version` set to a different published version. Leave it blank for a normal latest-version check. Failed candidates remain open for inspection; a later release can generate a new candidate.

## Version tags

After all three platform builds and smoke tests pass on `main`, CI publishes a fixed tag such as `v1.0.0-beta.12` on the exact tested commit. Existing tags are never moved: reruns on the same commit are no-ops; attempts to reuse a version on another commit fail rather than overwrite history. These are lightweight Git refs pointing to signed commits, not separately signed annotated tags or GitHub Release pages. No moving `latest` or major-version tags are published.

Once a tag exists, select it explicitly:

```sh
nix run github:Noir01/cf-cli-nix/v1.0.0-beta.12 -- --version
# Flake input:
# inputs.cf-cli-nix.url = "github:Noir01/cf-cli-nix/v1.0.0-beta.12";
```

Bot merges explicitly dispatch the main build workflow because `GITHUB_TOKEN` merges do not trigger normal push workflows. Tag publication waits for that merged commit's builds, rather than tagging the pre-merge PR candidate. Binary caching is not enabled yet.

## Build and test

```sh
nix build .#cf-cli
./result/bin/cf --version
./result/bin/cloudflare --version
./result/bin/cf cli search dns
```

`package.nix` pins the npm release tarball and `npmDepsHash` pins all dependencies from `package-lock.json`. The published tarball refers to unavailable local development dependencies; the Nix package removes those development-only entries before installation. It does not rebuild the upstream CLI bundle. `--ignore-scripts` prevents install-time npm scripts; features depending on those scripts need separate testing.

Supported and CI-tested systems: x86_64-linux, aarch64-linux, and aarch64-darwin (Apple Silicon). CI tests builds, both app entry points, help output, and local command search with an isolated home and no Cloudflare credentials. It does not yet verify authenticated operations or Workers local development and its native dependencies.

The pinned nixpkgs-unstable revision has dropped x86_64-darwin support, so Intel macOS is not supported by this flake.
