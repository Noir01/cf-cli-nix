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
