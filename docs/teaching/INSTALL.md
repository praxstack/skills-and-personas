# Teaching installation reference

Install both entries for the full current visual teaching engine:

```bash
npx skills add praxstack/skills-and-personas --skill teacher teach-pro-max
```

Teacher is the standalone implementation with 22 bundled modules. Teach Pro Max is the user entry and tutoring contract; it reads the sibling Teacher implementation when present. Ask the agent to use either installed entry for a complete visual explanation, with practice when requested.

Teacher alone is also usable:

```bash
npx skills add praxstack/skills-and-personas --skill teacher
```

An existing Teach Pro Max installation without its sibling Teacher uses its self-contained compatibility engine. It can answer without requiring another installation. Select both entries to use the full current Teacher implementation through that entry.

The root [`skills.sh.json`](../../skills.sh.json) groups these entries on the repository page. As described in the [skills.sh customization documentation](https://www.skills.sh/docs/customize), grouping affects display only. It does not change CLI selection or install another skill automatically.

## Edition and source identity

The teaching entries show `Version: 1.2.0 (locally maintained edition).` below their title, or after frontmatter when the original entry has no title. Their original frontmatter and teaching instructions are preserved. This notice is separate from upstream skill releases, repository tags, runtime/tool package versions and acceptance receipts. Teach Pro Max, including its embedded compatibility implementation and manifests, keeps its existing bytes and release numbering.

[`versions-1.2.0.json`](versions-1.2.0.json) records source paths and SHA-256 fingerprints. Repository originals, curated `new-skills` entries, Teacher's bundled copies and canonical local installations are separate records. Matching names do not imply matching bodies: for example, the legacy concept-cartographer differs from its curated counterpart, and Teacher's eli includes an existing local self-check. Preserve these variants when installing over an existing local skill.

The edition covers teacher, teach, prax-teach, prax-teach-v2, algo-sensei, eli, visualize, concept-cartographer, techtutor and lecture-alchemist, plus their named Teacher counterparts where present. The manifest distinguishes public repository entries from local-only editions. A provenance record for a local-only edition does not publish its content or add it to CLI installation choices. Optional modules outside this list keep their existing bytes. Upstream attribution and license notices remain applicable.

Runtime packages, renderers, browser and voice assets remain separate prerequisites. See the existing [usage guide](../teach-pro-max/USAGE-GUIDE.md) for capabilities and setup, and Teacher's [vendor manifest](../../skills/teacher/VENDOR.json) for bundled provenance and deliberate local edition notices.
