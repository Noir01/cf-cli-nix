{ lib, buildNpmPackage, fetchurl, jq, nodejs_22 }:

buildNpmPackage rec {
  pname = "cf-cli";
  version = "1.0.0-beta.5";

  src = fetchurl {
    url = "https://registry.npmjs.org/cf/-/cf-${version}.tgz";
    hash = "sha256-1x3pK0SXZ7YssUD8HA02IwWRTu7bGkS4WoYACcKXMBw=";
  };

  sourceRoot = "package";
  nodejs = nodejs_22;
  npmDepsHash = "sha256-dAT4zWMLQvn2Uj3b27u5kfcM7Gar6Z5mq3zPjfYXF/c=";
  npmFlags = [ "--ignore-scripts" ];
  dontNpmBuild = true;

  # The published tarball's devDependencies reference files outside the tarball.
  # Remove only these build-time entries; retain all runtime dependencies.
  postPatch = ''
    ${jq}/bin/jq 'del(.devDependencies, .scripts)' package.json > package.json.tmp
    mv package.json.tmp package.json
    cp ${./package-lock.json} package-lock.json
  '';

  meta = {
    description = "Cloudflare cf CLI";
    homepage = "https://github.com/cloudflare/cf";
    license = with lib.licenses; [ mit asl20 ];
    mainProgram = "cf";
  };
}
