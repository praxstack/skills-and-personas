# Document Type Templates

When input matches a recognizable document type, use these structural skeletons.

---

## README.md

```markdown
# [Project Name]

[One-line description of what this project does.]

## 🚀 Features

- Feature 1
- Feature 2

## 🛠️ Installation

```bash
[install command]
```

## 💻 Usage

```bash
[usage example]
```

## ⚙️ Configuration

| Option | Default | Description |
|--------|---------|-------------|
| | | |

## 📚 Documentation

[Links or inline docs]

## 🧪 Testing

```bash
[test command]
```

## 🤝 Contributing

[Guidelines]

## 📄 License

[License type]
```

---

## CHANGELOG.md (Keep a Changelog style)

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features

### Changed
- Existing functionality changes

### Deprecated
- Soon-to-be-removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Vulnerability fixes

## [1.2.0] - 2026-01-15

### Added
- [Change description]
```

---

## Meeting Notes

```markdown
# Meeting Notes — [Topic] ([Date])

## 📅 Meta

| Field | Value |
|-------|-------|
| Date | |
| Time | |
| Location / Link | |
| Facilitator | |

## 👥 Attendees

- Name (Role)
- Name (Role)

## 🎯 Agenda

1. Topic 1
2. Topic 2

## 📝 Discussion

### Topic 1
[Summary]

### Topic 2
[Summary]

## 🤝 Decisions

- [Decision 1 with rationale]

## ✅ Action Items

| # | Owner | Task | Due |
|---|-------|------|-----|
| 1 | | | |

## 🏁 Next Steps

[Follow-up date / topic]
```

---

## API Documentation

```markdown
# [API Name]

[Brief description]

## 🔌 Base URL

```
https://api.example.com/v1
```

## 🔒 Authentication

[Method — Bearer token, API key, OAuth]

```
Authorization: Bearer <token>
```

## Endpoints

### `GET /resource`

[Description]

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| | | | |

**Response:**

```json
{
  "field": "value"
}
```

**Status codes:**

| Code | Meaning |
|------|---------|
| 200 | OK |
| 401 | Unauthorized |
| 404 | Not Found |
```

---

## Configuration Documentation

```markdown
# Configuration Reference

## ⚙️ Environment Variables

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | string | — | Yes | Postgres connection string |
| `PORT` | int | `3000` | No | Server port |

## 📂 Config File

```yaml
# config.yml
database:
  host: localhost
  port: 5432
server:
  port: 3000
```

## ⚠️ Notes

> Sensitive values (keys, tokens) should be set via environment variables, not in the config file.
```

---

## Runbook / Incident Response

```markdown
# Runbook — [Service / Scenario]

## 🚨 Symptoms

- [Observable signal 1]
- [Observable signal 2]

## 🔍 Diagnosis

1. Check [metric / log]
2. Verify [dashboard]

## 🛠️ Mitigation

### Option A: [Quick fix]
```bash
[commands]
```

### Option B: [Escalation]
[Procedure]

## 📞 Escalation Contacts

| Role | Contact |
|------|---------|
| | |

## 📚 Related

- [Related runbook]
- [Architecture doc]
```

---

## Transcript Cleanup

Input: raw speech-to-text transcript (filler words, timestamps, multiple speakers).

```markdown
# [Event Name] — Transcript

**Date:** [Date]
**Participants:** [Names]

## Summary

[2-3 sentence summary of what was covered]

## Key Points

- Point 1
- Point 2

## Transcript

**[Speaker 1]:** [Cleaned-up quote — filler removed, punctuation added, meaning preserved]

**[Speaker 2]:** [Quote]

[Continue...]

## Action Items

- [ ] Item 1
- [ ] Item 2
```

Rule: When cleaning transcripts, remove filler ("um", "uh", "like"), fix obvious misheard words, preserve the speaker's voice and all substantive content.

---

## Script / Log Output

Input: terminal output, CI logs, error traces.

```markdown
# [Context] — Output

## Command

```bash
[exact command]
```

## Output

```
[verbatim output — do NOT paraphrase]
```

## ⚠️ Errors / Warnings

[If any]

> [Quote relevant error line with context]

## Analysis

[What the output means, if the user asked for analysis]
```

Rule: Verbatim preservation of command output. Never edit timestamps, error codes, stack traces, or filenames.
