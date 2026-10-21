#!/usr/bin/env bash
# DevMentor install script - add devmentor command to PATH
# Usage: bash install.sh
set -euo pipefail

INSTALL_DIR="${1:-$HOME/.devmentor}"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
JAR_SOURCE="$PROJECT_ROOT/target/devmentor-0.0.1-SNAPSHOT.jar"

# --- 1. Build JAR ---
if [[ ! -f "$JAR_SOURCE" ]]; then
    echo "JAR not found, building..."
    if [[ -n "${JAVA_HOME:-}" ]] && [[ -x "$JAVA_HOME/bin/java" ]]; then
        export JAVA_HOME
    fi
    (cd "$PROJECT_ROOT" && mvn package -DskipTests -q)
    if [[ ! -f "$JAR_SOURCE" ]]; then
        echo "Build failed"
        exit 1
    fi
    echo "Build complete"
fi

# --- 2. Install files ---
LIB_DIR="$INSTALL_DIR/lib"
BIN_DIR="$INSTALL_DIR/bin"
mkdir -p "$LIB_DIR" "$BIN_DIR"

cp "$JAR_SOURCE" "$LIB_DIR/devmentor.jar"
echo "JAR installed to $LIB_DIR"

cp "$PROJECT_ROOT/bin/devmentor" "$BIN_DIR/devmentor"
chmod +x "$BIN_DIR/devmentor"
echo "Launcher installed to $BIN_DIR"

# --- 3. Add to PATH ---
SHELL_RC=""
if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$(basename "$SHELL")" == "zsh" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -n "${BASH_VERSION:-}" ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [[ -n "$SHELL_RC" ]] && ! grep -q "$BIN_DIR" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# DevMentor" >> "$SHELL_RC"
    echo "export PATH="$PATH:$BIN_DIR"" >> "$SHELL_RC"
    echo "Added $BIN_DIR to $SHELL_RC"
else
    echo "$BIN_DIR already in PATH or shell rc"
fi

# --- 4. Done ---
echo ""
echo "Install complete!"
echo "  Type devmentor in terminal to start."
echo "  Set API key: export OPENROUTER_API_KEY=sk-or-..."
