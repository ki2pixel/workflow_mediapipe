{ pkgs, ... }: {
  channel = "stable-23.11";

  packages = [
    pkgs.git
    pkgs.python310
    pkgs.python310Packages.pip
    pkgs.python310Packages.virtualenv
    pkgs.python310Packages.pytest
    pkgs.nodejs_20
    pkgs.ffmpeg
    pkgs.sqlite
    pkgs.watchman
    pkgs.which
  ];

  idx = {
    extensions = [
      "ms-python.python"
      "ms-python.vscode-pylance"
      "ms-toolsai.jupyter"
      "esbenp.prettier-vscode"
      "dbaeumer.vscode-eslint"
    ];

    workspace = {
      onCreate = {
        install-python-deps = "python3 -m pip install --upgrade pip && python3 -m pip install -r requirements-dev.txt";
        install-node-deps = "npm install";
        default.openFiles = [
          "README.md"
          "docs/Documentation_De_Fichier_Dev.Nix.md"
        ];
      };

      onStart = {
        sync-repo = "git pull origin main --no-rebase || true";
        check-env = "python3 --version && pip --version && pytest --version && node --version && npm --version";
      };
    };

    previews = {
      enable = true;
    };
  };
}