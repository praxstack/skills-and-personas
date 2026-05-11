# Obsidian CLI — Search, Links, and Bases Reference

Reference for text search, link-graph analysis, and Base queries.

## Text search

### `search` — text search, returns file paths

```shell
obsidian search query=<text>
obsidian search query=<text> path=<folder>    # limit to folder
obsidian search query=<text> limit=10
obsidian search query=<text> case             # case-sensitive
obsidian search query=<text> total            # count only
obsidian search query=<text> format=json      # text|json
```

### `search:context` — grep-style `path:line: text`

```shell
obsidian search:context query=<text>
obsidian search:context query=<text> path=<folder>
obsidian search:context query="TODO" format=json
```

### `search:open` — open search view inside Obsidian

```shell
obsidian search:open query="meeting notes"
```

## Link graph analysis

### `backlinks` — incoming links

```shell
obsidian backlinks
obsidian backlinks file=<name>
obsidian backlinks file=<name> counts          # include link counts
obsidian backlinks total
obsidian backlinks format=json                 # json|tsv|csv
```

### `links` — outgoing links

```shell
obsidian links
obsidian links file=<name>
obsidian links total
```

### `unresolved` — broken / unresolved links

```shell
obsidian unresolved
obsidian unresolved total
obsidian unresolved counts verbose             # with source files
```

### `orphans` — files with no incoming links

```shell
obsidian orphans
obsidian orphans total
```

### `deadends` — files with no outgoing links

```shell
obsidian deadends
obsidian deadends total
```

## Bases (`.base` files)

### List

```shell
obsidian bases
obsidian base:views                            # views in active base
```

### Create base item

```shell
obsidian base:create file=<base> name=<name> content=<text>
obsidian base:create file=<base> view=<view> name=<name>
# Flags: open, newtab
```

### Query base

```shell
obsidian base:query file=<base>
obsidian base:query file=<base> view=<view>
obsidian base:query file=<base> format=json    # json|csv|tsv|md|paths
```

## Common query patterns

### Health check queries

```shell
obsidian orphans                               # notes with no incoming links
obsidian unresolved verbose                    # broken links and their sources
obsidian deadends                              # notes that link nowhere
```

### Coverage queries

```shell
# Count notes in a folder
obsidian files folder="100xDevBootcamp/03_Web3/SelfStudy" total

# Find all TODO-tagged notes with context
obsidian search:context query="TODO" path="100xDevBootcamp"

# List all tasks across a folder
obsidian tasks path="100xDevBootcamp/03_Web3/SelfStudy"
```

### Metadata-driven queries via Bases

Bases (`.base` YAML files) define filters and views. Query them with `base:query`:

```shell
obsidian base:query file=Concepts view="By Difficulty" format=json
obsidian base:query file=Projects format=paths    # paths only, script-friendly
```

### Link-graph pruning

```shell
# Find orphan concept notes
obsidian orphans | grep concepts/

# Build reverse-index for a hub note
obsidian backlinks file="Neural Networks" counts format=json --copy
```

### JSON pipelines

Many commands support `format=json` so scripts can consume output. Combine with `--copy` or redirect:

```shell
obsidian search query="loss function" format=json > hits.json
obsidian tasks todo format=json > open_tasks.json
obsidian properties counts format=json > prop_histogram.json
```
