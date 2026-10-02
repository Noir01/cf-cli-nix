{
  description = "Nix flake for Cloudflare's cf CLI";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      # These platforms passed native build and smoke tests in GitHub Actions.
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
      overlay = final: prev: {
        cf-cli = final.callPackage ./package.nix { };
      };
    in
    {
      overlays.default = overlay;
      packages = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; overlays = [ overlay ]; };
        in { default = pkgs.cf-cli; cf-cli = pkgs.cf-cli; });
      apps = forAllSystems (system:
        let cf = self.packages.${system}.cf-cli;
        in {
          default = { type = "app"; program = "${cf}/bin/cf"; };
          cf = { type = "app"; program = "${cf}/bin/cf"; };
          cloudflare = { type = "app"; program = "${cf}/bin/cloudflare"; };
        });
    };
}
