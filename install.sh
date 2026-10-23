#!/usr/bin/env bash
# DevMentor install script (macOS / Linux)
# Usage: bash install.sh
set -euo pipefail

INSTALL_DIR="${1:-$HOME/.devmentor}"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$PROJECT_ROOT/backend"
FRONTEND="$PROJECT_ROOT/frontend"

# --- 1. Check toolchain ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "Cannot find python3. Install 3.11+ first: https://www.python.org/downloads/" >&2
    exit 1
fi
if ! command -v node >/dev/null 2>&1; then
    echo "Cannot find node. Install 18+ first: https://nodejs.org/" >&2
    exit 1
fi

# --- 2. Install deps and build frontend ---
echo "Installing backend dependencies..."
python3 -m pip install -q -e "$BACKEND"

echo "Building frontend..."
npm install --silent --prefix "$FRONTEND"
npm run build --silent --prefix "$FRONTEND"

# --- 3. Write launcher ---
BIN_DIR="$INSTALL_DIR/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/devmentor" <<EOF
#!/usr/bin/env bash
# DevMentor - terminal programming mentor
PROJECT_ROOT="${DEVMENTOR_PROJECT_ROOT:-$PROJECT_ROOT}"
exec node "$PROJECT_ROOT/frontend/dist/cli.js" "$@"
EOF
chmod +x "$BIN_DIR/devmentor"
echo "Launcher written to $BIN_DIR/devmentor"

# --- 4. Add to PATH ---
SHELL_RC="$HOME/.bashrc"
if [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
fi
if ! grep -q "devmentor/bin" "$SHELL_RC" 2>/dev/null; then
    {
        echo ""
        echo "# DevMentor"
        echo 'export PATH="$HOME/.devmentor/bin:$PATH"'
    } >> "$SHELL_RC"
    echo "Added $BIN_DIR to $SHELL_RC"
else
    echo "$BIN_DIR already in PATH"
fi

echo ""
echo "Install complete!"
echo "  Type devmentor in terminal to start."
echo "  Then /login to pick a model provider."
