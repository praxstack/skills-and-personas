---
name: obsidian-cli
description: Control Obsidian from the terminal using CLI v2 (1.12+). Create, read, append, search files; manage properties, tags, tasks; query bases; use templates; analyze links. Use when performing vault operations, automating note workflows, appending content to notes, managing frontmatter properties, or searching the vault from the command line. Requires Obsidian app to be running.
---

# Obsidian CLI Skill

Control Obsidian from the terminal. Create files, append content, manage properties, search the vault, toggle tasks, query bases, and more — all from the command line.

## Prerequisites

- **Obsidian 1.12+ installer** (check: `obsidian version`)
- **CLI enabled** in Settings > General > Command line interface
- **Obsidian app must be running** — CLI connects to the running instance
- On macOS, PATH is set via `~/.zprofile`: `export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"`

## Core Concepts

### Two Modes

1. **Single command**: `obsidian <command> [params] [flags]`
2. **TUI (Terminal UI)**: Run `obsidian` alone to enter interactive mode with autocomplete and history

### Parameters vs Flags

- **Parameter**: takes a value — `name=Note content="Hello world"`
- **Flag**: boolean switch, no value — `open`, `overwrite`, `newtab`
- Multiline content: use `\n` for newline, `\t` for tab
- Spaces in values: wrap in quotes — `content="Hello world"`

### Vault Targeting

- Default: current working directory if it's a vault, otherwise the active vault
- Explicit: `vault=<name>` or `vault=<id>` as FIRST parameter before the command

```shell
obsidian vault=PraxVault daily
obsidian vault="My Vault" search query="test"
```

### File Targeting

Many commands accept `file` and `path`:
- `file=<name>` — wikilink-style resolution (name only, no path/extension needed)
- `path=<path>` — exact path from vault root, e.g. `100xDevBootcamp/03_Web3/SelfStudy/classes/SS-W01.md`
- If neither provided, defaults to **active file**

### Copy Output

Add `--copy` to any command to copy output to clipboard:

```shell
obsidian read --copy
obsidian search query="TODO" --copy
```

---

## File Operations

### `create` — Create or overwrite a file

```shell
obsidian create name=<name> path=<path> content=<text> template=<name>
# Flags: overwrite, open, newtab
```

Examples:

```shell
# Create with content
obsidian create name="SS-W01 - Blockchains" content="# SS-W01\n\nStudy notes"

# Create from template
obsidian create name="New Note" template=Travel

# Create at specific path and open it
obsidian create path="Projects/idea.md" content="# Idea" open

# Overwrite existing
obsidian create name=Note content="Fresh start" overwrite
```

### `read` — Read file contents

```shell
obsidian read                          # active file
obsidian read file=Recipe              # by name
obsidian read path="folder/note.md"    # by path
```

### `append` — Append content to end of file

```shell
obsidian append content=<text>         # active file
obsidian append file=<name> content=<text>
obsidian append path=<path> content=<text>
# Flag: inline (no newline before appended content)
```

Examples:

```shell
# Append to specific file
obsidian append file="SS-W01 - Blockchains" content="\n## New Section\nContent here"

# Inline append (no preceding newline)
obsidian append file=Note content=" more text" inline
```

### `prepend` — Prepend content after frontmatter

```shell
obsidian prepend content=<text>
obsidian prepend file=<name> content=<text>
# Flag: inline
```

> [!important] Prepend inserts AFTER frontmatter, not at the very top of the file.

### `move` — Move or rename a file

```shell
obsidian move file=<name> to=<path>       # move to folder
obsidian move path=<path> to=<new-path>   # move with new path
```

Automatically updates internal links if enabled in vault settings.

### `rename` — Rename a file

```shell
obsidian rename file=<name> name=<new-name>
obsidian rename path=<path> name=<new-name>
```

Extension preserved automatically if omitted.

### `delete` — Delete a file

```shell
obsidian delete file=<name>       # to trash (default)
obsidian delete file=<name> permanent  # skip trash
```

### `open` — Open a file

```shell
obsidian open file=<name>
obsidian open path=<path> newtab
```

---

## File & Folder Info

### `file` — Show file metadata

```shell
obsidian file                    # active file
obsidian file file=<name>
```

Returns: path, name, extension, size, created, modified timestamps.

### `files` — List vault files

```shell
obsidian files                   # all files
obsidian files folder=<path>     # filter by folder
obsidian files ext=md            # filter by extension
obsidian files total             # just the count
```

### `folder` — Show folder info

```shell
obsidian folder path=<path>
obsidian folder path=<path> info=files    # file count only
obsidian folder path=<path> info=size     # size only
```

### `folders` — List vault folders

```shell
obsidian folders                       # all folders
obsidian folders folder=<path>         # filter by parent
obsidian folders total                 # just the count
```

---

## Properties (Frontmatter)

### `properties` — List properties

```shell
obsidian properties                           # all vault properties
obsidian properties active                    # active file's properties
obsidian properties file=<name>               # specific file
obsidian properties name=status               # specific property count
obsidian properties counts sort=count         # sorted by frequency
obsidian properties format=yaml               # yaml|json|tsv
```

### `property:set` — Set a property

```shell
obsidian property:set name=<prop> value=<val>
obsidian property:set name=<prop> value=<val> file=<name>
obsidian property:set name=<prop> value=<val> type=<type>
# Types: text, list, number, checkbox, date, datetime
```

Examples:

```shell
# Set status on active file
obsidian property:set name=status value=in-progress

# Set status on specific file
obsidian property:set name=status value=complete file="SS-W01 - Blockchains"

# Set a date property
obsidian property:set name=date value=2026-03-02 type=date

# Set a list property
obsidian property:set name=tags value="[100xdev, web3]" type=list
```

### `property:read` — Read a property value

```shell
obsidian property:read name=status
obsidian property:read name=status file=<name>
```

### `property:remove` — Remove a property

```shell
obsidian property:remove name=<prop>
obsidian property:remove name=<prop> file=<name>
```

---

## Search

### `search` — Search vault text (returns file paths)

```shell
obsidian search query=<text>
obsidian search query=<text> path=<folder>    # limit to folder
obsidian search query=<text> limit=10         # max results
obsidian search query=<text> case             # case sensitive
obsidian search query=<text> total            # count only
obsidian search query=<text> format=json      # text|json
```

### `search:context` — Search with line context

Returns grep-style `path:line: text` output.

```shell
obsidian search:context query=<text>
obsidian search:context query=<text> path=<folder>
obsidian search:context query="TODO" format=json
```

### `search:open` — Open search view in Obsidian

```shell
obsidian search:open query="meeting notes"
```

---

## Tags

### `tags` — List tags

```shell
obsidian tags                         # all vault tags
obsidian tags active                  # active file's tags
obsidian tags file=<name>             # specific file
obsidian tags counts                  # with occurrence counts
obsidian tags counts sort=count       # sorted by frequency
obsidian tags total                   # just the count
obsidian tags format=json             # json|tsv|csv
```

### `tag` — Tag info

```shell
obsidian tag name=web3                # occurrence count
obsidian tag name=web3 total          # just the number
obsidian tag name=web3 verbose        # include file list
```

---

## Tasks

### `tasks` — List tasks

```shell
obsidian tasks                        # all tasks
obsidian tasks todo                   # incomplete only
obsidian tasks done                   # completed only
obsidian tasks file=<name>            # from specific file
obsidian tasks daily                  # from daily note
obsidian tasks active                 # from active file
obsidian tasks verbose                # group by file with line numbers
obsidian tasks total                  # just the count
obsidian tasks 'status=?'            # filter by custom status char
obsidian tasks format=json            # json|tsv|csv|text
```

### `task` — Show or update a task

```shell
# Show task info
obsidian task file=Recipe line=8
obsidian task ref="Recipe.md:8"

# Toggle completion
obsidian task ref="Recipe.md:8" toggle

# Mark done/todo
obsidian task file=Recipe line=8 done
obsidian task file=Recipe line=8 todo
obsidian task daily line=3 toggle

# Set custom status
obsidian task file=Recipe line=8 status=-
```

---

## Daily Notes

### `daily` — Open daily note

```shell
obsidian daily
obsidian daily paneType=tab
```

### `daily:path` — Get daily note path

Returns the expected path even if the file hasn't been created yet.

```shell
obsidian daily:path
```

### `daily:read` — Read daily note

```shell
obsidian daily:read
```

### `daily:append` — Append to daily note

```shell
obsidian daily:append content="- [ ] Buy groceries"
obsidian daily:append content="## Evening\nReflection" open
# Flags: inline, open
```

### `daily:prepend` — Prepend to daily note

```shell
obsidian daily:prepend content="# Morning Priorities"
# Flags: inline, open
```

---

## Templates

### `templates` — List available templates

```shell
obsidian templates
obsidian templates total
```

### `template:read` — Read template content

```shell
obsidian template:read name=<template>
obsidian template:read name=<template> resolve         # resolve variables
obsidian template:read name=<template> title="My Note" resolve
```

The `resolve` flag processes `{{date}}`, `{{time}}`, `{{title}}` variables.

### `template:insert` — Insert template into active file

```shell
obsidian template:insert name=<template>
```

> [!tip] Creating files from templates
> Use `obsidian create path=<path> template=<name>` to create a new file with a template applied.

---

## Links Analysis

### `backlinks` — Incoming links to a file

```shell
obsidian backlinks                     # active file
obsidian backlinks file=<name>
obsidian backlinks file=<name> counts  # include link counts
obsidian backlinks total               # just the count
obsidian backlinks format=json         # json|tsv|csv
```

### `links` — Outgoing links from a file

```shell
obsidian links                         # active file
obsidian links file=<name>
obsidian links total
```

### `unresolved` — Broken/unresolved links

```shell
obsidian unresolved                    # list all
obsidian unresolved total              # count
obsidian unresolved counts verbose     # with source files
```

### `orphans` — Files with no incoming links

```shell
obsidian orphans
obsidian orphans total
```

### `deadends` — Files with no outgoing links

```shell
obsidian deadends
obsidian deadends total
```

---

## Bases

### `bases` — List .base files

```shell
obsidian bases
```

### `base:views` — List views in a base

```shell
obsidian base:views                    # active base
```

### `base:create` — Create a new item in a base

```shell
obsidian base:create file=<base> name=<name> content=<text>
obsidian base:create file=<base> view=<view> name=<name>
# Flags: open, newtab
```

### `base:query` — Query a base

```shell
obsidian base:query file=<base>
obsidian base:query file=<base> view=<view>
obsidian base:query file=<base> format=json    # json|csv|tsv|md|paths
```

---

## Outline

### `outline` — Show headings

```shell
obsidian outline                       # active file
obsidian outline file=<name>
obsidian outline format=tree           # tree|md|json
obsidian outline total                 # heading count
```

---

## Plugins

### `plugins` — List installed plugins

```shell
obsidian plugins
obsidian plugins filter=community versions
obsidian plugins filter=core
obsidian plugins format=json
```

### `plugin` — Plugin info

```shell
obsidian plugin id=<plugin-id>
```

### `plugin:enable` / `plugin:disable`

```shell
obsidian plugin:enable id=<id>
obsidian plugin:disable id=<id>
```

### `plugin:install` / `plugin:uninstall`

```shell
obsidian plugin:install id=<id> enable
obsidian plugin:uninstall id=<id>
```

### `plugin:reload` — Reload plugin (for developers)

```shell
obsidian plugin:reload id=my-plugin
```

---

## Themes & Snippets

### Themes

```shell
obsidian themes                        # list installed
obsidian theme                         # show active
obsidian theme:set name=<name>         # set active
obsidian theme:install name=<name> enable
obsidian theme:uninstall name=<name>
```

### CSS Snippets

```shell
obsidian snippets                      # list all
obsidian snippets:enabled              # list enabled
obsidian snippet:enable name=<name>
obsidian snippet:disable name=<name>
```

---

## Bookmarks

```shell
obsidian bookmarks                     # list bookmarks
obsidian bookmarks total verbose
obsidian bookmark file=<path>          # bookmark a file
obsidian bookmark file=<path> subpath="#Heading"
obsidian bookmark search="TODO"        # bookmark a search
obsidian bookmark url="https://..."    # bookmark a URL
```

---

## Vault Info

### `vault` — Show vault info

```shell
obsidian vault
obsidian vault info=name               # name|path|files|folders|size
```

### `vaults` — List known vaults

```shell
obsidian vaults
obsidian vaults verbose                # include paths
obsidian vaults total
```

### `vault:open` — Switch vault (TUI only)

```shell
vault:open PraxVault
```

---

## Wordcount

```shell
obsidian wordcount                     # active file
obsidian wordcount file=<name>
obsidian wordcount words               # word count only
obsidian wordcount characters          # char count only
```

---

## Workspace

```shell
obsidian workspace                     # show tree
obsidian workspaces                    # list saved
obsidian workspace:save name=<name>
obsidian workspace:load name=<name>
obsidian workspace:delete name=<name>
obsidian tabs                          # list open tabs
obsidian tabs ids
obsidian recents                       # recently opened files
```

---

## File History & Diff

### `diff` — Compare file versions

```shell
obsidian diff                          # list versions of active file
obsidian diff file=<name>              # list versions
obsidian diff file=<name> from=1       # compare latest to current
obsidian diff file=<name> from=2 to=1  # compare two versions
obsidian diff filter=sync              # only sync versions
```

### `history` — Local file recovery

```shell
obsidian history file=<name>           # list versions
obsidian history:list                  # all files with history
obsidian history:read file=<name> version=1
obsidian history:restore file=<name> version=2
obsidian history:open file=<name>      # open recovery UI
```

---

## Command Palette

Execute any registered Obsidian command:

```shell
obsidian commands                      # list all command IDs
obsidian commands filter=editor        # filter by prefix
obsidian command id=<command-id>       # execute a command
obsidian hotkeys                       # list all hotkeys
obsidian hotkey id=<command-id>        # get hotkey for command
```

---

## Developer Commands

### `devtools` — Toggle dev tools

```shell
obsidian devtools
```

### `dev:screenshot` — Take screenshot

```shell
obsidian dev:screenshot path=screenshot.png
```

### `eval` — Execute JavaScript

```shell
obsidian eval code="app.vault.getFiles().length"
obsidian eval code="app.workspace.getActiveFile().path"
```

### `dev:console` — Show console messages

```shell
obsidian dev:console
obsidian dev:console limit=10 level=error
obsidian dev:console clear
```

### `dev:errors` — Show JavaScript errors

```shell
obsidian dev:errors
obsidian dev:errors clear
```

### `dev:css` — Inspect CSS

```shell
obsidian dev:css selector=".workspace" prop=background
```

### `dev:dom` — Query DOM

```shell
obsidian dev:dom selector=".nav-file-title" total
obsidian dev:dom selector=".cm-line" text all
```

### `dev:debug` — Chrome DevTools Protocol

```shell
obsidian dev:debug on     # attach
obsidian dev:debug off    # detach
```

### `dev:cdp` — Run CDP command

```shell
obsidian dev:cdp method="Page.captureScreenshot" params='{"format":"png"}'
```

### `dev:mobile` — Toggle mobile emulation

```shell
obsidian dev:mobile on
obsidian dev:mobile off
```

---

## Miscellaneous

```shell
obsidian help                          # all commands
obsidian help <command>                # specific command help
obsidian version                       # show version
obsidian reload                        # reload app window
obsidian restart                       # restart app
obsidian random                        # open random note
obsidian random:read                   # read random note
obsidian web url="https://..."         # open URL in web viewer
obsidian unique name=<text>            # create unique note
```

---

## TUI Keyboard Shortcuts

When in TUI mode (`obsidian` with no command):

### Navigation

| Action | Shortcut |
|--------|----------|
| Cursor left | `Left` / `Ctrl+B` |
| Cursor right (accepts suggestion at end) | `Right` / `Ctrl+F` |
| Start of line | `Ctrl+A` |
| End of line | `Ctrl+E` |
| Back one word | `Alt+B` |
| Forward one word | `Alt+F` |

### Editing

| Action | Shortcut |
|--------|----------|
| Delete to start | `Ctrl+U` |
| Delete to end | `Ctrl+K` |
| Delete previous word | `Ctrl+W` / `Alt+Backspace` |

### Autocomplete

| Action | Shortcut |
|--------|----------|
| Enter suggestions / accept selected | `Tab` |
| Exit suggestions | `Shift+Tab` |
| Accept first suggestion (at end of line) | `Right` |

### History

| Action | Shortcut |
|--------|----------|
| Previous entry / navigate up | `Up` / `Ctrl+P` |
| Next entry / navigate down | `Down` / `Ctrl+N` |
| Reverse search | `Ctrl+R` |

### Other

| Action | Shortcut |
|--------|----------|
| Execute / accept | `Enter` |
| Undo / exit suggestions / clear | `Escape` |
| Clear screen | `Ctrl+L` |
| Exit TUI | `Ctrl+C` / `Ctrl+D` |

---

## Obsidian Headless (Separate Tool)

Obsidian Headless is a STANDALONE client — no desktop app required. It syncs vaults from the command line.

### Install

```shell
npm install -g obsidian-headless
```

Requires Node.js 22+ and an active Obsidian Sync subscription.

### Authentication

```shell
ob login                               # interactive login
ob logout                              # log out
export OBSIDIAN_AUTH_TOKEN="your-token" # for CI/scripts
```

### Headless Sync Commands

```shell
ob sync-list-remote                    # list remote vaults
ob sync-list-local                     # list local vaults
ob sync-create-remote --name "Vault" --encryption e2ee --password <pw>
ob sync-setup --vault "Vault" --path ~/vaults/my-vault
ob sync                                # one-time sync
ob sync --continuous                   # watch for changes
ob sync-status                         # check sync status
ob sync-config                         # view/change sync settings
ob sync-unlink                         # disconnect vault
```

> [!warning] Do NOT use both desktop Sync and Headless Sync on the same device. Use one sync method per device.

---

## Agent Workflow Patterns

Common patterns for AI agents working with Obsidian vaults:

### Pattern: Append Learning to Study Note

```shell
# Append a section to a specific study note
obsidian append path="100xDevBootcamp/03_Web3/SelfStudy/classes/SS-W01 - Blockchains.md" content="\n## New Insight\nContent here..."

# Update status property after studying
obsidian property:set name=status value=in-progress path="100xDevBootcamp/03_Web3/SelfStudy/classes/SS-W01 - Blockchains.md"
```

### Pattern: Create Concept Note on Demand

```shell
# Create a new concept note
obsidian create path="100xDevBootcamp/03_Web3/SelfStudy/concepts/PDAs.md" content="---\ntitle: PDAs\ntags:\n  - web3\n  - concept\nstatus: active\n---\n\n# Program Derived Addresses (PDAs)\n\n## Intuition\n..."
```

### Pattern: Search Before Creating

```shell
# Check if a concept note already exists
obsidian search query="Program Derived Addresses" path="100xDevBootcamp/03_Web3/SelfStudy"

# If no result, create it; if found, append to it
```

### Pattern: Check Study Progress

```shell
# List all files in SelfStudy
obsidian files folder="100xDevBootcamp/03_Web3/SelfStudy"

# Check properties of a study note
obsidian properties file="SS-W01 - Blockchains"

# Get tasks from study notes
obsidian tasks path="100xDevBootcamp/03_Web3/SelfStudy"
```

### Pattern: Daily Study Log

```shell
# Append study session to daily note
obsidian daily:append content="\n## Web3 Study Session\n- Studied: W01 - Blockchains\n- Key concepts: Distributed ledger, transaction lifecycle\n- Next: W02 - Wallets"
```

### Pattern: Vault Health Check

```shell
# Find orphaned notes
obsidian orphans

# Find broken links
obsidian unresolved verbose

# Find dead-end notes
obsidian deadends
```

---

## Troubleshooting

### CLI not found

```shell
# Check if binary exists
which obsidian

# macOS: verify PATH in ~/.zprofile
cat ~/.zprofile | grep Obsidian

# Manual PATH addition (macOS)
export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"
```

### Commands not executing

- Ensure Obsidian app is running (CLI connects to the running instance)
- Restart terminal after initial CLI registration
- Check version: `obsidian version` (requires 1.12+)

### File not found

- Use `file=` for wikilink-style resolution (just the name)
- Use `path=` for exact vault-relative paths
- Check if file exists: `obsidian search query="filename"`

## References

- [Obsidian CLI Docs](https://help.obsidian.md/cli)
- [Obsidian Headless](https://help.obsidian.md/headless)
- [Headless Sync](https://help.obsidian.md/sync/headless)
