# Obsidian CLI — Properties (Frontmatter) Reference

Manage frontmatter properties on notes via the `obsidian properties` and `obsidian property:*` commands.

## List properties

```shell
obsidian properties                           # all vault properties
obsidian properties active                    # active file's properties
obsidian properties file=<name>               # specific file
obsidian properties name=status               # count for a specific property
obsidian properties counts sort=count         # sorted by frequency
obsidian properties format=yaml               # yaml|json|tsv
```

## Set a property

```shell
obsidian property:set name=<prop> value=<val>
obsidian property:set name=<prop> value=<val> file=<name>
obsidian property:set name=<prop> value=<val> type=<type>
```

Supported types: `text`, `list`, `number`, `checkbox`, `date`, `datetime`.

### Examples

```shell
# Active file
obsidian property:set name=status value=in-progress

# Specific file
obsidian property:set name=status value=complete file="SS-W01 - Blockchains"

# Date property
obsidian property:set name=date value=2026-03-02 type=date

# List property
obsidian property:set name=tags value="[100xdev, web3]" type=list

# Number
obsidian property:set name=priority value=1 type=number

# Checkbox
obsidian property:set name=done value=true type=checkbox
```

## Read a property value

```shell
obsidian property:read name=status
obsidian property:read name=status file=<name>
```

## Remove a property

```shell
obsidian property:remove name=<prop>
obsidian property:remove name=<prop> file=<name>
```

## Common property patterns

### Study-note status workflow

```shell
# Mark as started
obsidian property:set name=status value=in-progress path="SelfStudy/classes/SS-W01.md"

# Mark as complete after review
obsidian property:set name=status value=complete path="SelfStudy/classes/SS-W01.md"

# Read current status
obsidian property:read name=status file="SS-W01"
```

### Bulk tagging via property:set

For tag-like properties stored as frontmatter `tags`, use `type=list`:

```shell
obsidian property:set name=tags value="[concept, web3, solidity]" type=list file="PDAs"
```

### Dataview-style metadata

Populate frontmatter keys that Dataview/Bases queries rely on:

```shell
obsidian property:set name=type value=concept type=text file="PDAs"
obsidian property:set name=difficulty value=3 type=number file="PDAs"
obsidian property:set name=reviewed value=2026-03-02 type=date file="PDAs"
```

## Output formats

Use `format=` for programmatic consumption:

- `format=yaml` — YAML (default).
- `format=json` — machine-parseable JSON.
- `format=tsv` — tab-separated values for scripts.

```shell
obsidian properties counts format=json --copy
```
