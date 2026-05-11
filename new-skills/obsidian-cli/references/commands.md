# Obsidian CLI — Commands Reference

Complete command reference for `obsidian` CLI v2 (Obsidian 1.12+). Requires Obsidian app running.

## Conventions

- **Parameter** takes a value: `name=Note content="Hello"`.
- **Flag** is a boolean switch: `open`, `overwrite`, `newtab`, `inline`.
- Multiline content: `\n` newline, `\t` tab.
- Spaces in values require quotes: `content="Hello world"`.
- `--copy` on any command copies output to clipboard.

## Vault targeting

- Default vault: cwd if it is a vault; otherwise the active vault.
- Explicit: put `vault=<name>` or `vault=<id>` as the first parameter before the command.

```shell
obsidian vault=PraxVault daily
obsidian vault="My Vault" search query="test"
```

## File targeting

Most commands accept `file` and `path`:

- `file=<name>` — wikilink-style resolution (name only, no path/extension).
- `path=<path>` — exact path from vault root, e.g. `Projects/idea.md`.
- If neither provided, defaults to active file.

## File operations

### `create` — create or overwrite a file

```shell
obsidian create name=<name> path=<path> content=<text> template=<name>
# Flags: overwrite, open, newtab
```

```shell
obsidian create name="SS-W01 - Blockchains" content="# SS-W01\n\nStudy notes"
obsidian create name="New Note" template=Travel
obsidian create path="Projects/idea.md" content="# Idea" open
obsidian create name=Note content="Fresh start" overwrite
```

### `read` — read file contents

```shell
obsidian read                          # active file
obsidian read file=Recipe
obsidian read path="folder/note.md"
```

### `append` — append content to end of file

```shell
obsidian append content=<text>
obsidian append file=<name> content=<text>
obsidian append path=<path> content=<text>
# Flag: inline (no newline before appended content)
```

### `prepend` — prepend content after frontmatter

```shell
obsidian prepend content=<text>
obsidian prepend file=<name> content=<text>
# Flag: inline
```

Prepend inserts AFTER frontmatter, not at the very top of the file.

### `move`, `rename`, `delete`, `open`

```shell
obsidian move file=<name> to=<path>
obsidian move path=<path> to=<new-path>

obsidian rename file=<name> name=<new-name>
obsidian rename path=<path> name=<new-name>

obsidian delete file=<name>               # to trash (default)
obsidian delete file=<name> permanent

obsidian open file=<name>
obsidian open path=<path> newtab
```

## File & folder info

```shell
obsidian file
obsidian file file=<name>

obsidian files                            # all files
obsidian files folder=<path>              # filter by folder
obsidian files ext=md
obsidian files total                      # count

obsidian folder path=<path>
obsidian folder path=<path> info=files
obsidian folder path=<path> info=size

obsidian folders
obsidian folders folder=<path>
obsidian folders total
```

## Tags

```shell
obsidian tags                              # all vault tags
obsidian tags active                       # active file's tags
obsidian tags file=<name>
obsidian tags counts                       # with occurrence counts
obsidian tags counts sort=count
obsidian tags total
obsidian tags format=json                  # json|tsv|csv

obsidian tag name=web3
obsidian tag name=web3 total
obsidian tag name=web3 verbose             # include file list
```

## Tasks

```shell
obsidian tasks                             # all tasks
obsidian tasks todo                        # incomplete only
obsidian tasks done                        # completed only
obsidian tasks file=<name>
obsidian tasks daily
obsidian tasks active
obsidian tasks verbose                     # group by file with line numbers
obsidian tasks total
obsidian tasks 'status=?'                  # custom status char
obsidian tasks format=json                 # json|tsv|csv|text

obsidian task file=Recipe line=8
obsidian task ref="Recipe.md:8"
obsidian task ref="Recipe.md:8" toggle
obsidian task file=Recipe line=8 done
obsidian task file=Recipe line=8 todo
obsidian task daily line=3 toggle
obsidian task file=Recipe line=8 status=-
```

## Daily notes

```shell
obsidian daily
obsidian daily paneType=tab
obsidian daily:path                        # expected path even if not yet created
obsidian daily:read

obsidian daily:append content="- [ ] Buy groceries"
obsidian daily:append content="## Evening\nReflection" open
# Flags: inline, open

obsidian daily:prepend content="# Morning Priorities"
# Flags: inline, open
```

## Templates

```shell
obsidian templates
obsidian templates total

obsidian template:read name=<template>
obsidian template:read name=<template> resolve
obsidian template:read name=<template> title="My Note" resolve

obsidian template:insert name=<template>
```

The `resolve` flag processes `{{date}}`, `{{time}}`, `{{title}}`.

Use `obsidian create path=<path> template=<name>` to create a new file from a template.

## Outline

```shell
obsidian outline
obsidian outline file=<name>
obsidian outline format=tree              # tree|md|json
obsidian outline total
```

## Plugins, themes, snippets

```shell
obsidian plugins
obsidian plugins filter=community versions
obsidian plugins filter=core
obsidian plugins format=json
obsidian plugin id=<plugin-id>
obsidian plugin:enable id=<id>
obsidian plugin:disable id=<id>
obsidian plugin:install id=<id> enable
obsidian plugin:uninstall id=<id>
obsidian plugin:reload id=my-plugin

obsidian themes
obsidian theme
obsidian theme:set name=<name>
obsidian theme:install name=<name> enable
obsidian theme:uninstall name=<name>

obsidian snippets
obsidian snippets:enabled
obsidian snippet:enable name=<name>
obsidian snippet:disable name=<name>
```

## Bookmarks

```shell
obsidian bookmarks
obsidian bookmarks total verbose
obsidian bookmark file=<path>
obsidian bookmark file=<path> subpath="#Heading"
obsidian bookmark search="TODO"
obsidian bookmark url="https://..."
```

## Vault info

```shell
obsidian vault
obsidian vault info=name                   # name|path|files|folders|size

obsidian vaults
obsidian vaults verbose
obsidian vaults total

# TUI only
vault:open PraxVault
```

## Wordcount

```shell
obsidian wordcount
obsidian wordcount file=<name>
obsidian wordcount words
obsidian wordcount characters
```

## Workspace

```shell
obsidian workspace
obsidian workspaces
obsidian workspace:save name=<name>
obsidian workspace:load name=<name>
obsidian workspace:delete name=<name>
obsidian tabs
obsidian tabs ids
obsidian recents
```

## History & diff

```shell
obsidian diff
obsidian diff file=<name>
obsidian diff file=<name> from=1
obsidian diff file=<name> from=2 to=1
obsidian diff filter=sync

obsidian history file=<name>
obsidian history:list
obsidian history:read file=<name> version=1
obsidian history:restore file=<name> version=2
obsidian history:open file=<name>
```

## Command palette

```shell
obsidian commands
obsidian commands filter=editor
obsidian command id=<command-id>
obsidian hotkeys
obsidian hotkey id=<command-id>
```

## Developer commands

```shell
obsidian devtools
obsidian dev:screenshot path=screenshot.png

obsidian eval code="app.vault.getFiles().length"
obsidian eval code="app.workspace.getActiveFile().path"

obsidian dev:console
obsidian dev:console limit=10 level=error
obsidian dev:console clear

obsidian dev:errors
obsidian dev:errors clear

obsidian dev:css selector=".workspace" prop=background
obsidian dev:dom selector=".nav-file-title" total
obsidian dev:dom selector=".cm-line" text all

obsidian dev:debug on
obsidian dev:debug off
obsidian dev:cdp method="Page.captureScreenshot" params='{"format":"png"}'
obsidian dev:mobile on
obsidian dev:mobile off
```

## Miscellaneous

```shell
obsidian help
obsidian help <command>
obsidian version
obsidian reload
obsidian restart
obsidian random
obsidian random:read
obsidian web url="https://..."
obsidian unique name=<text>
```

## TUI keyboard shortcuts

When running `obsidian` with no command:

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

## Obsidian Headless (separate tool)

Obsidian Headless is a standalone client — no desktop app required. It syncs vaults from the command line.

### Install

```shell
npm install -g obsidian-headless
```

Requires Node.js 22+ and an active Obsidian Sync subscription.

### Authentication

```shell
ob login
ob logout
export OBSIDIAN_AUTH_TOKEN="your-token"
```

### Sync commands

```shell
ob sync-list-remote
ob sync-list-local
ob sync-create-remote --name "Vault" --encryption e2ee --password <pw>
ob sync-setup --vault "Vault" --path ~/vaults/my-vault
ob sync
ob sync --continuous
ob sync-status
ob sync-config
ob sync-unlink
```

Do NOT use both desktop Sync and Headless Sync on the same device.
