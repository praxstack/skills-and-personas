# Public publication: Prax Teach v3.0.0

The accepted general teacher is on the public default branch of `praxstack/skills-and-personas`. The preserved governing stage, product stages and acceptance/evidence commits were promoted separately onto the current main branch. The existing main-branch work was preserved. No accepted skill bytes, frozen criteria or private evaluator prompts changed.

## Public installation and downloads

```sh
npx skills add praxstack/skills-and-personas --skill teacher teach-pro-max
```

`--skill teacher` alone installs the standalone general teacher. The compatible `teach-pro-max` entry requires its sibling, so the README and usage guide now show the paired command for that invocation.

Two actual anonymous GitHub installation tests passed with Skills CLI 1.7.2: the two-entry installation matched all 2,342 accepted files, and the standalone installation matched all 1,538 teacher files. GitHub token variables, gh fallback and Git credential files were disabled for these scoped tests. No user-wide installation was overwritten.

Stable release: https://github.com/praxstack/skills-and-personas/releases/tag/prax-teach-v3.0.0 . The source ZIP includes every skill source/support file, hidden support files, license notices, a setup guide and sample lesson sources. The separate lesson ZIP contains actual current outputs and review evidence. Runtime environments and model weights are separate prerequisites. The unfinished C development fixtures are not part of the accepted release.

Both ZIPs were downloaded over ordinary unauthenticated HTTPS. Byte counts, SHA256 hashes and full ZIP CRC checks passed. The extracted setup guide and lesson portal were checked at 1440 and 390 px with no missing local links or horizontal overflow. A downloaded interactive video loaded and played at 1280x720. Original development assets and their hashes remain unchanged.

## skills.sh

The normal public page https://skills.sh/praxstack/skills-and-personas/teacher is live and renders its installation command and Teacher content. An initial check found a soft 404 despite HTTP200; it is retained as an observed pre-ingestion state. The genuine standalone install's normal telemetry request returned HTTP200, without a fabricated event or a modified CLI.

The official repository-page grouping file `skills.sh.json` is on main. Official instructions say these metadata updates are processed from normal install telemetry and cached.

At the final search check, the CLI search index still returned the older `teach-pro-max` record, and that compatibility detail page retained an older cached instruction excerpt. These are external catalog-cache observations, not a failed source install. The exact current GitHub files were verified in both install tests. Do not claim the search index or old snapshot was refreshed until observed; do not inflate install counts to force a refresh.

The accepted teacher's direct listing, public stable downloads and public default-branch installation are verified. The fresh private bank stays private, and the source candidate's earlier factual/visual acceptance limits remain unchanged.
