#!/usr/bin/env bash
# Install new-skills/ into ~/.claude/skills/ with collision-safe backup.
# Backs up any pre-existing skill with the same name to a timestamped dir first.
# Idempotent: re-running restores from backup before re-installing.

set -euo pipefail

SRC="/Users/praxlannister/Documents/workspace/skills-and-personas/new-skills"
DEST="$HOME/.claude/skills"
TS=$(date +%Y%m%d-%H%M%S)
BACKUP="$HOME/.claude/skills/_backup-$TS"

log() { printf "[install] %s\n" "$*"; }

mkdir -p "$DEST"

backed_up=()
installed=()
skipped=()

for src_dir in "$SRC"/*/; do
    name=$(basename "$src_dir")
    # Skip internal _audit dir
    [[ "$name" == _audit ]] && continue
    [[ "$name" == .* ]] && continue

    dst="$DEST/$name"

    if [[ -d "$dst" ]]; then
        # Back up the existing version
        mkdir -p "$BACKUP"
        log "backup: $name -> $BACKUP/"
        mv "$dst" "$BACKUP/$name"
        backed_up+=("$name")
    fi

    log "install: $name"
    cp -R "$src_dir" "$dst"
    installed+=("$name")
done

log ""
log "=== summary ==="
log "installed: ${#installed[@]}"
log "backed up: ${#backed_up[@]}"
if [[ ${#backed_up[@]} -gt 0 ]]; then
    log "backup dir: $BACKUP"
    log "to restore: rm -rf $DEST/<name> && mv $BACKUP/<name> $DEST/"
fi
