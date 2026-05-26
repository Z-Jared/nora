#!/usr/bin/env bash
set -e

REPO="git+https://github.com/Z-Jared/nora.git"

echo "Installing Nora..."

# Check python3
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found. Please install Python 3.9+ first." >&2
  exit 1
fi

# Check Python version >= 3.9
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
  echo "Error: Python >= 3.9 required, found $PY_VERSION" >&2
  exit 1
fi

echo "Python $PY_VERSION found."

# Install
python3 -m pip install --user "$REPO"

# Check if nora is executable
if command -v nora &>/dev/null; then
  echo ""
  echo "Installation complete!"
  echo ""
  echo "  nora         Start the CLI"
  echo "  nora-serve   Start the HTTP server with Web UI"
  echo ""
else
  SCRIPTS_DIR=$(python3 -c "import site, os; print(os.path.join(site.getusersitepackages(), '..', '..', '..', 'bin'))" 2>/dev/null || echo "")
  echo ""
  echo "Installation complete, but 'nora' is not in your PATH."
  echo ""
  echo "Add the user scripts directory to your PATH:"
  echo ""
  if [ -n "$SCRIPTS_DIR" ]; then
    echo "  export PATH=\"$SCRIPTS_DIR:\$PATH\""
  else
    echo "  # macOS:"
    echo "  export PATH=\"\$HOME/Library/Python/3.x/bin:\$PATH\""
    echo ""
    echo "  # Linux:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
  echo ""
  echo "Add the line to your shell profile (~/.zshrc or ~/.bashrc) and reload:"
  echo "  source ~/.zshrc"
  echo ""
  echo "Then run: nora"
fi
