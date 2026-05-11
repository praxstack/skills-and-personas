# Markdown Anti-Patterns

Common mistakes and their correct alternatives.

---

## Inventing facts

**Input:** "we discussed the API redesign"
**Wrong:** "The team discussed the API redesign, covering authentication, rate limiting, versioning, and backward compatibility."
**Right:** "The team discussed the API redesign."

Never extrapolate from input. If the user didn't say it, don't say it.

---

## Paraphrasing technical literals

**Input:** `npm install --save-dev @types/node`
**Wrong:** `npm install --save-dev types for node`
**Right:** `npm install --save-dev @types/node` (exact, in code block)

File paths, commands, version numbers, API signatures, URLs, identifiers — all preserved exactly.

---

## Skipping heading levels

**Wrong:**
```markdown
# Project
### Installation
```

**Right:**
```markdown
# Project
## Installation
```

If you need deeper nesting, use every level in between.

---

## Decorative emojis in body text

**Wrong:**
```markdown
- 🌟 First item 🎉
- ⚡ Second item 🔥
- 💫 Third item ✨
```

**Right:**
```markdown
- First item
- Second item
- Third item
```

Emojis at most once per heading, and only when they carry semantic meaning.

---

## Tables without closing pipes

**Wrong:**
```markdown
| Column A | Column B
| -------- | --------
| Value 1  | Value 2
```

**Right:**
```markdown
| Column A | Column B |
| -------- | -------- |
| Value 1  | Value 2  |
```

Every row must close with `|`. Many renderers fail without it.

---

## Code blocks without language tags

**Wrong:**
````markdown
```
def hello():
    print("hi")
```
````

**Right:**
````markdown
```python
def hello():
    print("hi")
```
````

Language tag enables syntax highlighting. If language is unknown, leave the tag empty rather than guessing.

---

## Conversational preambles

**Wrong:**
```
Here's the formatted version of your content:

# My Document
...
```

**Right:**
```
# My Document
...
```

Output the Markdown directly. No "here's the formatted version" or "I've organized this for you" openers.

---

## Wrapping entire output in a code fence

**Wrong (output literally contains these characters):**
````
```markdown
# My Document

## Section

Content here.
```
````

**Right (output IS the Markdown):**
```markdown
# My Document

## Section

Content here.
```

Only wrap in an outer fence if the user specifically asked for a copy-paste-able code block.

---

## Excessive blockquotes

**Wrong:**
```markdown
> This is paragraph one.

> This is paragraph two.

> This is paragraph three.
```

**Right:** Blockquotes mark notes, warnings, definitions, or distinct summaries. Regular prose is prose.

```markdown
This is paragraph one.

This is paragraph two.

> Note: paragraph three contains critical information.
```

---

## Inconsistent list markers

**Wrong:**
```markdown
* Item A
- Item B
+ Item C
```

**Right:**
```markdown
- Item A
- Item B
- Item C
```

Pick one (`-` recommended) and stay consistent within a document.

---

## Missing blank lines around block elements

**Wrong:**
```markdown
Some text.
## Heading
More text.
```

**Right:**
```markdown
Some text.

## Heading

More text.
```

Blank lines before and after headings, lists, code blocks, and blockquotes. Many renderers require them.

---

## Generic titles when context exists

**Wrong:** `# Document` when input clearly is meeting notes from a specific meeting
**Right:** `# Meeting Notes — API Redesign (2026-01-15)`

Generate neutral titles only when truly no context exists.

---

## Mixing heading levels in lists

**Wrong:**
```markdown
## Items
### Item 1
### Item 2
### Item 3
```

**Right:** If items are peers with equal weight, use a list, not headings.
```markdown
## Items

- Item 1
- Item 2
- Item 3
```

Headings are for document structure, not enumeration.
