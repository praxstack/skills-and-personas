---
name: obsidian-cli
description: 'Control Obsidian from the terminal using the CLI v2 (Obsidian 1.12+). Create, read, append, prepend, move, rename, delete files; manage frontmatter properties; list and toggle tasks; search the vault; analyze links; query Bases; manage plugins, themes, snippets, workspaces. Use when performing vault operations, automating note workflows, appending content to notes, managing frontmatter properties, searching the vault, running Base queries, or scripting Obsidian from bash. Requires Obsidian app running. Trigger phrases: "obsidian cli", "append to note", "create obsidian note", "search vault", "obsidian property", "obsidian task", "daily note", "obsidian backlinks", "orphans", "base:query".'
---

# Obsidian CLI

**Audience:** AI agents and terminal users automating Obsidian vault operations.
**Goal:** Drive Obsidian from the command line safely and reproducibly — file CRUD, frontmatter properties, tasks, search, link analysis, Bases, plugins, workspaces.

**MANDATORY:** Before any file operation (`create`, `append`, `prepend`, `move`, `rename`, `delete`, `template:insert`), read `references/commands.md` to confirm exact parameter/flag names.

**MANDATORY:** Before any frontmatter change (`property:set`, `property:remove`), read `references/properties.md` for type rules and value formats.

**MANDATORY:** Before any search, link analysis, or base query, read `references/queries.md`.

## Prerequisites

- Obsidian 1.12+ installed (`obsidian version`).
- CLI enabled in Settings -> General -> Command line interface.
- Obsidian app must be running — CLI connects to the live instance.
- On macOS the PATH should include the binary: `export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"` in `~/.zprofile`.

## Core concepts

### Two modes

1. **Single command:** `obsidian <command> [params] [flags]`.
2. **TUI:** `obsidian` with no command enters an interactive shell with autocomplete and history. See `references/commands.md` for TUI keybindings.

### Parameters vs flags

- **Parameter** takes a value: `name=Note content="Hello world"`.
- **Flag** is a boolean switch with no value: `open`, `overwrite`, `newtab`, `inline`.
- Multiline content uses `\n` and `\t`. Values with spaces require quotes.

### Vault targeting

- Default vault = current working directory if it is a vault; otherwise the active vault.
- Explicit: `vault=<name>` or `vault=<id>` as the FIRST parameter before the command.

```shell
obsidian vault=PraxVault daily
obsidian vault="My Vault" search query="test"
```

### File targeting

- `file=<name>` — wikilink-style (name only, no path/extension).
- `path=<path>` — exact path from vault root, e.g. `Projects/idea.md`.
- If neither provided, most commands default to the **active file**.

### Copy output

Add `--copy` on any command to copy its output to the clipboard.

```shell
obsidian read --copy
obsidian search query="TODO" --copy
```

## Decision tree: picking the right command

### "I want to write content into a note"

| Need | Command |
|------|---------|
| New note (fail if exists) | `obsidian create name=<n> content="..."` |
| New note, replace if exists | `obsidian create ... overwrite` |
| New note from template | `obsidian create path=... template=<name>` |
| Add to the END of an existing note | `obsidian append file=<n> content="..."` |
| Add AFTER the frontmatter but before body | `obsidian prepend file=<n> content="..."` |
| Insert template into the currently open file | `obsidian template:insert name=<n>` |

### "I want to change a note's metadata"

See `references/properties.md` for full type rules.

| Need | Command |
|------|---------|
| Set frontmatter value | `obsidian property:set name=<k> value=<v>` |
| Set with explicit type | `obsidian property:set name=<k> value=<v> type=<type>` |
| Read a value | `obsidian property:read name=<k> file=<n>` |
| Remove a property | `obsidian property:remove name=<k> file=<n>` |
| List frequency histogram | `obsidian properties counts sort=count` |

### "I want to find something in the vault"

See `references/queries.md` for the full search/link/base matrix.

| Need | Command |
|------|---------|
| Text search, return paths | `obsidian search query="..."` |
| Text search with line context | `obsidian search:context query="..."` |
| Incoming links to a note | `obsidian backlinks file=<n>` |
| Outgoing links from a note | `obsidian links file=<n>` |
| Broken links | `obsidian unresolved` |
| Isolated notes | `obsidian orphans` |
| Notes that link nowhere | `obsidian deadends` |
| Query a base file | `obsidian base:query file=<base>` |

### "I want to manage tasks"

| Need | Command |
|------|---------|
| List all vault tasks | `obsidian tasks` |
| Only open tasks | `obsidian tasks todo` |
| Tasks from active file | `obsidian tasks active` |
| Tasks from daily note | `obsidian tasks daily` |
| Toggle a task | `obsidian task file=<n> line=<N> toggle` |
| Mark done explicitly | `obsidian task file=<n> line=<N> done` |
| Custom status char | `obsidian task file=<n> line=<N> status=-` |

### "I want to work with the daily note"

| Need | Command |
|------|---------|
| Open daily note | `obsidian daily` |
| Path (even if not created yet) | `obsidian daily:path` |
| Read daily note | `obsidian daily:read` |
| Append a line | `obsidian daily:append content="..."` |
| Prepend a section | `obsidian daily:prepend content="..."` |

## Agent workflow patterns

### Pattern: append learning to a study note

```shell
obsidian append path="100xDevBootcamp/03_Web3/SelfStudy/classes/SS-W01 - Blockchains.md" \
  content="\n## New Insight\nContent here..."

obsidian property:set name=status value=in-progress \
  path="100xDevBootcamp/03_Web3/SelfStudy/classes/SS-W01 - Blockchains.md"
```

### Pattern: search before creating

```shell
# Check if a concept note already exists
obsidian search query="Program Derived Addresses" \
  path="100xDevBootcamp/03_Web3/SelfStudy"

# If no result, create it. If found, append to it.
```

### Pattern: create a concept note on demand

```shell
obsidian create \
  path="100xDevBootcamp/03_Web3/SelfStudy/concepts/PDAs.md" \
  content="---\ntitle: PDAs\ntags:\n  - web3\n  - concept\nstatus: active\n---\n\n# Program Derived Addresses (PDAs)\n\n## Intuition\n..."
```

### Pattern: daily study log

```shell
obsidian daily:append content="\n## Web3 Study Session\n- Studied: W01 - Blockchains\n- Key concepts: distributed ledger, transaction lifecycle\n- Next: W02 - Wallets"
```

### Pattern: vault health check

```shell
obsidian orphans
obsidian unresolved verbose
obsidian deadends
```

### Pattern: check study progress

```shell
obsidian files folder="100xDevBootcamp/03_Web3/SelfStudy" total
obsidian properties file="SS-W01 - Blockchains"
obsidian tasks path="100xDevBootcamp/03_Web3/SelfStudy"
```

## Safety guidelines for agents

- **Idempotency.** For appends, consider searching first to avoid duplicate sections.
- **Overwrite is destructive.** Never pass the `overwrite` flag on `create` without user confirmation.
- **Trash vs permanent.** `delete` trashes by default; `delete ... permanent` skips trash. Prefer trash unless the user explicitly asks otherwise.
- **Dry-run by reading first.** Before `property:set` or `prepend` on unfamiliar files, run `obsidian read` or `obsidian properties` to confirm current state.
- **Escape quotes in content.** Shell-escape `"` and `$` inside `content="..."`.
- **Active-file ambiguity.** If the user did not specify a target and the active file is unexpected, prefer `file=` or `path=` explicitly.

## Troubleshooting

### CLI not found

```shell
which obsidian
cat ~/.zprofile | grep Obsidian
export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"
```

### Commands not executing

- Ensure Obsidian app is running — the CLI connects to the running instance.
- Restart the terminal after initial CLI registration.
- Check version: `obsidian version` (requires 1.12+).

### File not found

- Use `file=` for wikilink-style resolution (name only).
- Use `path=` for exact vault-relative paths.
- Confirm existence: `obsidian search query="filename"`.

## Further references

- [Obsidian CLI docs](https://help.obsidian.md/cli)
- [Obsidian Headless](https://help.obsidian.md/headless)
- [Headless Sync](https://help.obsidian.md/sync/headless)

For the headless client (separate tool, standalone sync without the desktop app), see the "Obsidian Headless" section in `references/commands.md`.
