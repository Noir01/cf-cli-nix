{ lib, buildNpmPackage, fetchurl, jq, nodejs_22 }:

buildNpmPackage rec {
  pname = "cf-cli";
  version = "1.0.0-beta.22";

  src = fetchurl {
    url = "https://registry.npmjs.org/cf/-/cf-${version}.tgz";
    hash = "sha256-aOdTbzpNh2KAlu9pQ/3U6TSXizQ5rZRFmnQ3MgY9Rrk=";
  };

  sourceRoot = "package";
  nodejs = nodejs_22;
  npmDepsHash = "sha256-2+SRKde+/HICmPwNvOzIufNxbcvSm+6557W3y7hBKwY=";
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
