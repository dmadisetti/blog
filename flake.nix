{
  description = "Dylan's interactive blog development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python toolchain
            python311
            uv

            # Node.js toolchain
            nodejs_20

            # Useful utilities
            git
          ];

          shellHook = ''
            echo "🚀 Blog development environment loaded!"
            echo ""
            echo "Available tools:"
            echo "  - Python $(python --version 2>&1 | cut -d' ' -f2)"
            echo "  - Node.js $(node --version)"
            echo "  - uv $(uv --version)"
            echo ""
            echo "Quick start:"
            echo "  - uv sync          # Install Python dependencies"
            echo "  - npm install      # Install Node.js dependencies"
            echo "  - npm run dev      # Watch and build React component"
            echo "  - uv run mkdocs serve  # Serve the blog locally"
            echo ""
          '';
        };
      }
    );
}
