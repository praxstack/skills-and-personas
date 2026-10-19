#!/usr/bin/env bash
# Install the teacher skill for one or more agent hosts.
#
#   ./install.sh                         # every host whose config folder exists on this machine
#   ./install.sh --targets claude,codex,pi
#   ./install.sh --with-subskills        # also expose the bundled skills (explorable, manim-video, ...) by name
#   ./install.sh --copy                  # copy instead of symlink (for hosts that don't follow links)
#   ./install.sh --dir ./.claude/skills  # a project-level folder instead of the home ones
#   ./install.sh --dry-run | --uninstall
#
# Or with the skills CLI: npx skills add praxstack/skills-and-personas --skill teacher
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="teacher"
MODE="link"
TARGETS=""
DIR=""
SUBSKILLS=0
DRY=0
UNINSTALL=0
FORCE=0

host_dir() {
  case "$1" in
    claude) echo "$HOME/.claude/skills" ;;
    codex) echo "$HOME/.codex/skills" ;;
    agents) echo "$HOME/.agents/skills" ;;
    pi) echo "$HOME/.pi/agent/skills" ;;
    opencode) echo "$HOME/.config/opencode/skills" ;;
    gemini) echo "$HOME/.gemini/skills" ;;
    hermes) echo "$HOME/.hermes/skills" ;;
    cursor) echo "$HOME/.cursor/skills" ;;
    cline) echo "$HOME/.cline/skills" ;;
    kilocode) echo "$HOME/.kilocode/skills" ;;
    copilot) echo "$HOME/.copilot/skills" ;;
    *) return 1 ;;
  esac
}
ALL="claude codex agents pi opencode gemini hermes cursor cline kilocode copilot"

while [ $# -gt 0 ]; do
  case "$1" in
    --targets|--dir)
      case "${2-}" in ""|-*) echo "$1 needs a value" >&2; exit 2 ;; esac
      if [ "$1" = --dir ]; then DIR="$2"; else TARGETS="${2//,/ }"; fi; shift 2 ;;
    --copy) MODE="copy"; shift ;;
    --with-subskills) SUBSKILLS=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

run() { if [ "$DRY" = 1 ]; then echo "would: $*"; else "$@"; fi; }

ours() { # ours <source dir> <dest>: a link that resolves to this source, or a copy this script made
  if [ -L "$2" ]; then
    # A dangling link can't be traced back to us, so it counts as foreign (--force replaces it).
    [ -e "$2" ] && [ "$(cd "$2" && pwd -P)" = "$(cd "$1" && pwd -P)" ]
  else
    [ -f "$2/.installed-by-teacher" ]
  fi
}

place() { # place <source dir> <dest dir> <name>
  local src="$1" dest="$2/$3"
  if [ "$UNINSTALL" = 1 ]; then
    if ours "$src" "$dest"; then run rm -rf "$dest"; echo "removed $dest"
    elif [ -e "$dest" ] || [ -L "$dest" ]; then echo "skip    $dest (isn't ours)"; fi
    return
  fi
  if [ -d "$dest" ] && ! [ -L "$dest" ] && [ "$(cd "$dest" && pwd -P)" = "$(cd "$src" && pwd -P)" ]; then
    echo "ok      $dest (this is the source itself)"; return
  fi
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$MODE" != "copy" ] && [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then echo "ok      $dest"; return; fi
    if [ "$FORCE" != 1 ] && ! ours "$src" "$dest"; then
      echo "skip    $dest (exists and isn't ours; --force replaces it)"; return
    fi
    run rm -rf "$dest"
  fi
  run mkdir -p "$2"
  if [ "$MODE" = "copy" ]; then
    run cp -R "$src" "$dest"
    [ "$DRY" = 1 ] || touch "$dest/.installed-by-teacher"
  else
    run ln -s "$src" "$dest"
  fi
  [ "$DRY" = 1 ] || echo "installed $dest"
}

install_into() {
  local base="$1"
  place "$SRC" "$base" "$NAME"
  if [ "$SUBSKILLS" = 1 ]; then
    for sub in "$SRC"/skills/*/; do
      sub="${sub%/}"
      # Public compatibility aliases are installed explicitly from their
      # top-level entry. Never shadow them with a bundled copy.
      [ "$(basename "$sub")" = "teach-pro-max" ] && continue
      [ -f "$sub/SKILL.md" ] && place "$sub" "$base" "$(basename "$sub")"
    done
  fi
}

if [ -n "$DIR" ]; then
  install_into "$DIR"
  exit 0
fi

if [ -z "$TARGETS" ]; then
  for t in $ALL; do
    d="$(host_dir "$t")"
    # Only hosts that are set up here: their config folder (the parent of skills/) exists.
    [ -d "$(dirname "$d")" ] && TARGETS="$TARGETS $t"
  done
  [ -n "$TARGETS" ] || TARGETS="agents"
fi

for t in $TARGETS; do
  d="$(host_dir "$t")" || { echo "unknown target: $t (known: $ALL)" >&2; exit 2; }
  install_into "$d"
done

if [ "$UNINSTALL" != 1 ] && [ "$DRY" != 1 ]; then
  echo
  echo "Check what this machine can render: python3 \"$SRC/scripts/find_tool.py\" --inventory --net"
fi
