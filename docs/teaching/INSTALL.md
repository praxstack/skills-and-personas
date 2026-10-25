# Teaching installation reference

Install both entries for the full current visual teaching engine:

```bash
npx skills add praxstack/skills-and-personas --skill teacher teach-pro-max
# Equivalent source mirror:
npx skills add praxstack/skills --skill teacher teach-pro-max
```

Teacher is the standalone implementation with 22 bundled modules. Teach Pro Max is the user entry and tutoring contract; it reads the sibling Teacher implementation when present. Ask the agent to use either installed entry for a complete visual explanation, with practice when requested.

Teacher alone is also usable:

```bash
npx skills add praxstack/skills-and-personas --skill teacher
```

An existing Teach Pro Max installation without its sibling Teacher uses its self-contained compatibility engine. It can answer without requiring another installation. Select both entries to use the full current Teacher implementation through that entry.

The root [`skills.sh.json`](../../skills.sh.json) groups these entries on the repository page. As described in the [skills.sh customization documentation](https://www.skills.sh/docs/customize), grouping affects display only. It does not change CLI selection or install another skill automatically.

## Edition and source identity

Current versions are Teacher 1.3.0 and Teach Pro Max 3.1.0. Substantive lessons use HTML by default, with five dark and five night reading palettes for text, controls and inline diagrams. Explicit live tutoring requests still use the conversation. The [reading-theme reference](../../skills/teacher/references/READING-THEMES.md) gives the local embedding command and accessibility checks. Theme selection follows course links through a URL parameter; it does not enable progress saving or create learner records.

[`versions-current.json`](versions-current.json) lists current component versions. Skill versions remain separate from upstream releases, runtime packages, renderers and acceptance receipts. The embedded compatibility implementation remains preserved; its historical receipts retain their original scope.

[`versions-1.2.0.json`](versions-1.2.0.json) records the earlier metadata-only edition, source paths and SHA-256 fingerprints. Repository originals, curated `new-skills` entries, Teacher's bundled copies and canonical local installations are separate records. Matching names do not imply matching bodies: for example, the legacy concept-cartographer differs from its curated counterpart, and Teacher's eli includes an existing local self-check. Preserve these variants when installing over an existing local skill.

The edition covers teacher, teach, prax-teach, prax-teach-v2, algo-sensei, eli, visualize, concept-cartographer, techtutor and lecture-alchemist, plus their named Teacher counterparts where present. The manifest distinguishes public repository entries from local-only editions. A provenance record for a local-only edition does not publish its content or add it to CLI installation choices. Optional modules outside this list keep their existing bytes. Upstream attribution and license notices remain applicable.

Runtime packages, renderers, browser and voice assets remain separate prerequisites. See the existing [usage guide](../teach-pro-max/USAGE-GUIDE.md) for capabilities and setup, and Teacher's [vendor manifest](../../skills/teacher/VENDOR.json) for bundled provenance and deliberate local edition notices.
