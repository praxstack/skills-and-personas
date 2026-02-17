#!/bin/bash
# ============================================================
# OpenCode Tech Educator Setup for Obsidian Vault
# ============================================================
# Usage: ./setup.sh /path/to/your/obsidian-vault
#
# This script copies all necessary OpenCode config files
# into your Obsidian vault folder so that when you run
# `opencode` from that directory, the Gabriel Petersson
# mentor persona auto-activates.
# ============================================================

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KNOWLEDGE_PACK_DIR="$(cd "$SCRIPT_DIR/../knowledge-packs/atlas/v2" && pwd)"

# --- Validate arguments ---
if [ $# -eq 0 ]; then
  echo "❌ Usage: $0 /path/to/your/obsidian-vault"
  echo ""
  echo "   Example: $0 ~/Documents/MyVault"
  echo "   Example: $0 \"/Users/prax/Library/Mobile Documents/iCloud~md~obsidian/Documents/MyVault\""
  exit 1
fi

VAULT_DIR="$1"

if [ ! -d "$VAULT_DIR" ]; then
  echo "❌ Directory not found: $VAULT_DIR"
  echo "   Please provide a valid path to your Obsidian vault."
  exit 1
fi

echo "🧠 Setting up OpenCode Tech Educator in: $VAULT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- Step 1: Copy AGENTS.md ---
echo "📄 Copying AGENTS.md (custom instructions)..."
cp "$SCRIPT_DIR/AGENTS.md" "$VAULT_DIR/AGENTS.md"

# --- Step 2: Create .opencode/agents/ and copy agent ---
echo "🤖 Setting up agent: gabriel-petersson..."
mkdir -p "$VAULT_DIR/.opencode/agents"
cp "$SCRIPT_DIR/.opencode/agents/gabriel-petersson.md" "$VAULT_DIR/.opencode/agents/gabriel-petersson.md"

# --- Step 3: Copy opencode.json ---
echo "⚙️  Copying opencode.json (config)..."
cp "$SCRIPT_DIR/opencode.json" "$VAULT_DIR/opencode.json"

# --- Step 4: Copy Knowledge Pack modules ---
echo "📚 Copying Atlas v2 Knowledge Pack..."
mkdir -p "$VAULT_DIR/.opencode/knowledge-pack"

for module in \
  "03_DSA_Patterns_Map.md" \
  "04_Design_Principles_Cheatsheet.md" \
  "05_Learning_Tracker_Template.md"; do
  if [ -f "$KNOWLEDGE_PACK_DIR/$module" ]; then
    cp "$KNOWLEDGE_PACK_DIR/$module" "$VAULT_DIR/.opencode/knowledge-pack/$module"
    echo "   ✓ $module"
  else
    echo "   ⚠ $module not found (skipping)"
  fi
done

# --- Step 5: Verify ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete! Files created:"
echo ""
echo "   $VAULT_DIR/"
echo "   ├── AGENTS.md                          ← Custom instructions"
echo "   ├── opencode.json                      ← Agent + config"
echo "   └── .opencode/"
echo "       ├── agents/"
echo "       │   └── gabriel-petersson.md        ← Full mentor persona"
echo "       └── knowledge-pack/"
echo "           ├── 03_DSA_Patterns_Map.md      ← DSA patterns reference"
echo "           ├── 04_Design_Principles.md     ← SOLID/GoF cheatsheet"
echo "           └── 05_Learning_Tracker.md      ← Progress tracker"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 How to use:"
echo "   1. cd \"$VAULT_DIR\""
echo "   2. opencode"
echo "   3. Press Tab to switch to the 'gabriel-petersson' agent"
echo "   4. Start learning! Try:"
echo "      → 'Explain how HashMap handles collisions'"
echo "      → 'REVIEW: <paste your code>'"
echo "      → 'DEEP DIVE: Binary Search Tree deletion'"
echo "      → 'ESCALATE: What if we have 1M entries?'"
echo ""
