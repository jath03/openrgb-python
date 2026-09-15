{
  description = "OpenRGB-Python devshell";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }@self:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs {
      inherit system;
    };
  in {
    devShells.${system}.default = with pkgs; mkShell {
      packages = [
        python3
        ruff
      ];
    };
  };
}
