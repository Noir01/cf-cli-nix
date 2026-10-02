# cf-cli-nix

Nix flake for [Cloudflare's `cf` CLI](https://github.com/cloudflare/cf), with hourly upstream checks, automatic tested updates, and [Cachix binaries](https://app.cachix.org/cache/cf-cli). Includes Node.js 22; no separate npm installation needed.

Supports **Linux x86_64 / ARM64** and **Apple Silicon macOS**. The upstream CLI is in beta.

## Quick start

Requires Nix with `nix-command` and `flakes` enabled.

```sh
# Try without installing
nix run github:Noir01/cf-cli-nix -- --help

# Install to your profile
nix profile install github:Noir01/cf-cli-nix
cf --version

# Update your installation
nix profile upgrade cf-cli-nix
```

Both `cf` and `cloudflare` are installed.

## Binary cache (optional)

Enable the cache before installing to download prebuilt packages:

```sh
nix run nixpkgs#cachix -- use cf-cli
```

Or add to your NixOS configuration:

```nix
nix.settings = {
  extra-substituters = [ "https://cf-cli.cachix.org" ];
  extra-trusted-public-keys = [
    "cf-cli.cachix.org-1:CD9hXEjchmA92ng/Q14oPwS6WxTwWGzp2P+EGgJjlmU="
  ];
};
```

Using the cache trusts this project's signing key. Skip it to build locally.

## NixOS / Home Manager

Add the flake input:

```nix
inputs.cf-cli-nix.url = "github:Noir01/cf-cli-nix";
```

Pass `inputs` to your modules via NixOS `specialArgs` or Home Manager `extraSpecialArgs`, then use:

```nix
{ inputs, pkgs, ... }:
{
  # NixOS
  environment.systemPackages = [ inputs.cf-cli-nix.packages.${pkgs.system}.default ];

  # Home Manager: use this instead
  # home.packages = [ inputs.cf-cli-nix.packages.${pkgs.system}.default ];
}
```

An overlay is also available: `inputs.cf-cli-nix.overlays.default` provides `pkgs.cf-cli`.

## Updates and pinning

Hourly checks follow npm's `latest` tag, including beta releases. Version updates merge automatically only after builds and smoke tests pass on all three platforms. Main builds are cached and new versions receive fixed Git tags. Failed candidates stay unmerged; GitHub scheduling and validation can delay updates.

To select a specific release:

```sh
nix run github:Noir01/cf-cli-nix/v1.0.0-beta.12 -- --version
```

The default URL follows `main`; a flake input stays pinned until you update your `flake.lock`. Installed profiles likewise need an explicit upgrade.

## Development

```sh
nix build .#cf-cli
python3 scripts/smoke-test.py result
python3 -m unittest discover -s tests -v
```

CI covers credential-free CLI smoke tests, not authenticated Cloudflare operations or Workers local development. See [maintenance notes](docs/maintaining.md) for packaging and automation details.
