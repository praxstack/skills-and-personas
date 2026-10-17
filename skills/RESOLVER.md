# Skill Resolver

Human-readable dispatch map over `skills/<slug>/SKILL.md`. Frontmatter `triggers:` are authoritative; this file is for scanning and disambiguation. Regenerate with `.agent/operator-prompt-library/scripts/add_triggers.py`.

| Skill | Trigger phrases |
|---|---|
| [academic-verify](academic-verify/SKILL.md) | `verify this academic claim`, `check this study`, `academic verify`, `validate citation`, `is this study real`, `Retraction Watch` |
| [archive-crawler](archive-crawler/SKILL.md) | `crawl my archive`, `find gold in my archive`, `archive crawler`, `scan my dropbox for`, `mine my old files for` |
| [article-enrichment](article-enrichment/SKILL.md) | `enrich this article`, `enrich the article`, `enriching the article`, `enrich brain pages`, `batch enrich`, `enrich pass`, `make brain pages useful` |
| [ask-user](ask-user/SKILL.md) | `present options`, `ask before proceeding`, `choice gate`, `user decision` |
| [backend-pe](backend-pe/SKILL.md) | `backend PE`, `distinguished engineer review`, `high-performance backend design`, `production readiness review` |
| [backend-principle-eng-cpp-pro-max](backend-principle-eng-cpp-pro-max/SKILL.md) | `C++ backend design`, `cpp performance service`, `low latency C++ systems` |
| [backend-principle-eng-java-pro-max](backend-principle-eng-java-pro-max/SKILL.md) | `Java backend design`, `Java microservice architecture`, `JVM service reliability` |
| [backend-principle-eng-javascript-pro-max](backend-principle-eng-javascript-pro-max/SKILL.md) | `JavaScript backend design`, `Node service architecture` |
| [backend-principle-eng-nodejs-pro-max](backend-principle-eng-nodejs-pro-max/SKILL.md) | `Node.js backend design`, `NodeJS service performance`, `express service review` |
| [backend-principle-eng-python-ml-pro-max](backend-principle-eng-python-ml-pro-max/SKILL.md) | `Python ML pipeline design`, `MLOps architecture`, `model serving review` |
| [backend-principle-eng-python-pro-max](backend-principle-eng-python-pro-max/SKILL.md) | `Python backend design`, `FastAPI service architecture`, `python service reliability` |
| [backend-principle-eng-typescript-pro-max](backend-principle-eng-typescript-pro-max/SKILL.md) | `TypeScript backend design`, `TS service architecture`, `type-safe API review` |
| [blog-ingest](blog-ingest/SKILL.md) | `ingest this publication`, `ingest this whole blog`, `ingest this feed`, `ingest this newsletter archive`, `save this whole substack`, `backfill this blog`, `walk this RSS feed`, `ingest every post from` |
| [blueprint-creator](blueprint-creator/SKILL.md) | `create a blueprint`, `expand this spec into a blueprint`, `implementation bible`, `BLUEPRINT.md` |
| [book-mirror](book-mirror/SKILL.md) | `personalized version of this book`, `mirror this book`, `two-column book analysis`, `apply this book to my life`, `how does this book apply to me` |
| [brain-ingest-gate](brain-ingest-gate/SKILL.md) | `move this to brain`, `migrate to brain`, `copy these files into the brain`, `is this already in the brain`, `check for duplicates before writing`, `dedup before saving`, `raw copy to brain` |
| [brain-link-discipline](brain-link-discipline/SKILL.md) | `give me the link`, `where is the page`, `why does this link 404`, `brain link discipline`, `rewrite subagent paths`, `report the pages you created`, `send me a clickable link`, `link the page in the same message` |
| [brain-ops](brain-ops/SKILL.md) | `any brain read/write/lookup/citation` |
| [brain-pdf](brain-pdf/SKILL.md) | `make pdf from brain`, `brain pdf`, `convert brain page to pdf`, `publish this page as pdf`, `export brain page` |
| [brain-taxonomist](brain-taxonomist/SKILL.md) | `where does this brain page go`, `file this in the brain`, `brain taxonomist`, `taxonomy check`, `refile brain page`, `create brain page`, `which directory does this go`, `which directory does this page go` |
| [briefing](briefing/SKILL.md) | `daily briefing`, `morning briefing`, `what's happening today`, `brain pulse`, `pre-briefing pull` |
| [bulk-ingestion](bulk-ingestion/SKILL.md) | `bulk ingest`, `bulk import`, `ingest all`, `ingestion pipeline`, `mass ingestion`, `bulk backfill`, `make a manifest`, `processing manifest`, `track a large ingest` |
| [capture](capture/SKILL.md) | `capture this`, `save this thought`, `remember this`, `ingest this into my brain`, `drop this in the inbox`, `save to brain` |
| [chronicle](chronicle/SKILL.md) | `journal entry`, `process my thoughts`, `daily reflection`, `write up my day` |
| [citation-fixer](citation-fixer/SKILL.md) | `fix citations`, `fix broken citations`, `citation audit`, `check citations`, `citation fixer` |
| [citation-graph-ingest](citation-graph-ingest/SKILL.md) | `citation graph`, `citation graph ingest`, `typed citation graph`, `build a reference graph`, `graph over a corpus`, `overrules / distinguishes graph`, `reason over a domain corpus`, `trace the argument through these documents` |
| [coding-agent-leadership-principles](coding-agent-leadership-principles/SKILL.md) | `leadership principles`, `operating floor`, `extreme ownership rules` |
| [cold-start](cold-start/SKILL.md) | `cold start`, `fill my brain`, `bootstrap brain`, `bootstrap my data`, `import my data`, `day one`, `get started`, `what should I import first`, `populate brain`, `now what?` |
| [company-brainify](company-brainify/SKILL.md) | `company brain`, `team brain`, `brainify`, `sanitize the brain`, `share my brain with the team`, `strip sensitive data from the brain`, `scrub employee data`, `audit the shared brain`, `make the brain safe to share` |
| [concept-cartographer](concept-cartographer/SKILL.md) | `create diagrams from notes`, `visualize concepts`, `make a flowchart`, `diagram this`, `concept map` |
| [concept-synthesis](concept-synthesis/SKILL.md) | `concept synthesis`, `synthesize my concepts`, `find patterns across my notes`, `build my intellectual map`, `trace idea evolution`, `canon vs riff`, `cull my concepts`, `which concepts to keep`, `concept quality rubric` |
| [constellation-team](constellation-team/SKILL.md) | `star team`, `cross-functional workflow`, `full lifecycle planning`, `multi-role planning` |
| [context-audit](context-audit/SKILL.md) | `context audit`, `context diet`, `system prompt audit`, `prompt compression`, `reduce context size`, `audit my context stack`, `context is too big`, `token hygiene` |
| [conversation-archive](conversation-archive/SKILL.md) | `chatgpt export`, `claude export`, `perplexity export`, `conversation history`, `import my conversations`, `search my conversations`, `when did I first discuss`, `archive my session transcripts`, `backfill missing conversations` |
| [correction-pipeline](correction-pipeline/SKILL.md) | `that's wrong`, `that's not true`, `I never said that`, `where did you get that`, `you got that wrong`, `correct that fact`, `root-cause this error` |
| [cron-scheduler](cron-scheduler/SKILL.md) | `schedule a job`, `cron`, `quiet hours`, `what jobs are running` |
| [cross-agent-handoff](cross-agent-handoff/SKILL.md) | `hand off to another agent`, `prepare a handoff`, `resume work in another session`, `cross-session handoff` |
| [cross-modal-review](cross-modal-review/SKILL.md) | `second opinion`, `cross-modal review`, `double check this`, `get another perspective`, `challenge this code`, `adversarial review` |
| [daily-task-manager](daily-task-manager/SKILL.md) | `add task`, `complete task`, `what are my tasks`, `task list`, `defer task` |
| [daily-task-prep](daily-task-prep/SKILL.md) | `morning prep`, `prepare for today`, `what's on my plate`, `day prep` |
| [data-loss-gate](data-loss-gate/SKILL.md) | `bulk delete`, `wipe the`, `rm -rf`, `purge the`, `truncate`, `free up space`, `bulk forget`, `remove the source`, `drop the table` |
| [data-research](data-research/SKILL.md) | `research`, `track`, `extract from email`, `investor updates`, `donations`, `build a tracker`, `data dig` |
| [draft-in-voice](draft-in-voice/SKILL.md) | `draft in voice`, `write this as`, `make this sound like`, `ghostwrite`, `draft a tweet as`, `write a post as`, `in their voice`, `in my voice`, `build a voice profile` |
| [eiirp](eiirp/SKILL.md) | `everything in its right place`, `eiirp`, `store this research`, `put this in the brain`, `file this properly`, `where does this research go`, `make this permanent`, `archive this research`, `archive this research thread`, `brain this`, `file all of this`, `organize all of this`, `organize all of this work`, `make this re-doable`, `DRY this up`, `check everything is in the right place`, `analyze this document`, `deep analysis`, `review this report` |
| [enrich](enrich/SKILL.md) | `enrich`, `create person page`, `update company page`, `who is this person`, `look up this company` |
| [fact-check](fact-check/SKILL.md) | `fact check`, `fact-check`, `verify the facts`, `check the claims`, `is this accurate`, `source check`, `verify this output claim by claim`, `is this output hallucinating`, `re-derive every claim` |
| [frontend-pe](frontend-pe/SKILL.md) | `Ultrafrontend`, `High-End UX`, `Awwwards style`, `world-class UI design` |
| [functional-area-resolver](functional-area-resolver/SKILL.md) | `compress agents.md`, `compress my resolver`, `resolver too big`, `resolver.md too big`, `agents.md too large`, `shrink routing table`, `slim down agents.md`, `functional area resolver`, `functional area dispatcher`, `context-health agents`, `context-health resolver`, `reduce context budget` |
| [gbrain-advisor](gbrain-advisor/SKILL.md) | `what should I do to get more out of gbrain`, `is my brain set up right`, `gbrain advisor`, `advise me on my brain`, `weekly brain checkup` |
| [idea-capturer](idea-capturer/SKILL.md) | `capture an idea`, `develop a raw idea`, `organize my ideas` |
| [idea-ingest](idea-ingest/SKILL.md) | `shares a link or URL`, `read this`, `save this`, `think about this`, `put this in brain` |
| [idea-lineage](idea-lineage/SKILL.md) | `idea lineage`, `trace the lineage of this idea`, `how my thinking about`, `how has my thinking about`, `current version of this idea`, `what is my current version of`, `show reversals in my thinking about`, `where did this idea come from` |
| [ingest](ingest/SKILL.md) | `ingest this`, `save this to brain`, `process this meeting` |
| [lecture-alchemist](lecture-alchemist/SKILL.md) | `process this transcript`, `convert lecture to notes`, `lecture notes`, `study material from lecture` |
| [maintain](maintain/SKILL.md) | `brain health`, `check backlinks`, `maintenance`, `orphan pages`, `stale pages`, `extract links`, `build link graph`, `populate timeline`, `populate links`, `backfill graph`, `extract timeline entries`, `retriage the backlog`, `re-score the triage`, `run dream`, `process today's session`, `process yesterday's transcripts`, `synthesize my conversations`, `what patterns did you see`, `did the dream cycle run`, `consolidate yesterday's conversations` |
| [measure-before-you-fix](measure-before-you-fix/SKILL.md) | `keeps timing out`, `ETIMEDOUT`, `why is this data stale`, `freshness alert`, `wedged`, `job is slow`, `sync is stuck`, `raise the timeout` |
| [media-ingest](media-ingest/SKILL.md) | `watch this video`, `process this YouTube link`, `ingest this PDF`, `save this podcast`, `process this book`, `PDF book`, `summarize this book`, `ingest it into my brain`, `what's in this screenshot`, `check out this repo` |
| [meeting-ingestion](meeting-ingestion/SKILL.md) | `meeting transcript`, `process this meeting`, `meeting notes`, `meeting recorder`, `ingest this recording`, `capture meetings`, `audit this meeting`, `check the sequence`, `did I get the order right`, `meeting transcript received` |
| [minion-orchestrator](minion-orchestrator/SKILL.md) | `gbrain jobs submit`, `submit a gbrain job`, `submit a shell job`, `shell job`, `run shell command in background`, `deterministic background task`, `spawn agent`, `background task`, `run in background`, `check on agent`, `agent progress`, `what's running`, `steer agent`, `change direction`, `tell the agent`, `pause agent`, `stop agent`, `resume agent`, `parallel tasks`, `fan out`, `do these in parallel`, `long operation`, `durable execution`, `arm a deadman`, `the job went silent`, `operation died in the background`, `make this pipeline resumable` |
| [obsidian-cli](obsidian-cli/SKILL.md) | `obsidian vault operations`, `obsidian command line`, `search my obsidian vault` |
| [perplexity-research](perplexity-research/SKILL.md) | `perplexity research`, `perplexity-research`, `what's new about`, `current state of`, `web research`, `what changed about`, `surface new developments` |
| [publish](publish/SKILL.md) | `share this page`, `publish page`, `create shareable link` |
| [query](query/SKILL.md) | `what do we know about`, `tell me about`, `who is`, `what happened`, `search for`, `look up`, `background on`, `notes on`, `who knows who`, `relationship between`, `connections`, `graph query` |
| [repo-architecture](repo-architecture/SKILL.md) | `where does this go`, `filing rules`, `create new page`, `which directory` |
| [reports](reports/SKILL.md) | `save report`, `load latest report`, `what's the latest briefing`, `show me the pulse`, `report quality`, `link quality check`, `validate report links` |
| [research-compendium](research-compendium/SKILL.md) | `compendium`, `research everything about`, `read them all and summarize`, `definitive guide`, `comprehensive guide to`, `deep research and write up`, `archive the sources then summarize`, `deepen the compendium` |
| [resolve-before-asking](resolve-before-asking/SKILL.md) | `resolve before asking`, `before asking the user`, `unidentified contact`, `unknown relationship`, `should I ask who`, `don't know who this is`, `to be filled by content analysis`, `placeholder on this page` |
| [signal-detector](signal-detector/SKILL.md) | `every inbound message (always-on)` |
| [skill-autobench](skill-autobench/SKILL.md) | `skill autobench`, `autobench`, `write the eval from usage history`, `synthesize an eval for this skill`, `mine how this skill is actually used`, `build a benchmark from my corrections`, `verify the eval panel`, `did all providers return` |
| [skill-creator](skill-creator/SKILL.md) | `create a skill`, `new skill`, `improve this skill` |
| [skillify](skillify/SKILL.md) | `skillify this`, `skillify`, `is this a skill?`, `make this proper`, `add tests and evals for this`, `check skill completeness`, `run skillify on a skill`, `did this skill regress` |
| [skillpack-check](skillpack-check/SKILL.md) | `skillpack check`, `is gbrain healthy`, `gbrain health`, `check the brain`, `is the brain working` |
| [skillpack-harvest](skillpack-harvest/SKILL.md) | `harvest this skill`, `harvest my skill`, `publish this skill to gbrain`, `lift this skill`, `share this skill`, `promote this skill`, `promote my skill`, `skill upstream`, `into the gbrain core`, `gbrain bundle` |
| [soul-audit](soul-audit/SKILL.md) | `soul audit`, `customize agent`, `who am I`, `set up identity`, `change my agent's personality` |
| [spec-creator](spec-creator/SKILL.md) | `write a spec`, `create SPEC.md`, `implementation contract`, `spec out this feature` |
| [strategic-reading](strategic-reading/SKILL.md) | `strategic reading`, `read this through the lens of`, `apply this to my problem`, `what can I learn from this about`, `extract a playbook from` |
| [superimprove](superimprove/SKILL.md) | `improve this codebase`, `harden the codebase`, `fix all confirmed defects`, `overhaul this repo` |
| [svg-logo-designer](svg-logo-designer/SKILL.md) | `design an SVG logo`, `brand mark`, `wordmark design`, `vector logo` |
| [teach-pro-max](teach-pro-max/SKILL.md) | `teach me`, `build intuition`, `quiz me`, `Socratic guidance`, `resume my course` |
| [teacher](teacher/SKILL.md) | `teach me visually`, `explain this visually`, `make a lesson`, `make an explainer video`, `I still don't get it`, `interactive lesson` |
| [techtutor](techtutor/SKILL.md) | `explain X`, `how does X work`, `tutor me on`, `mock interview`, `intuition for` |
| [testing](testing/SKILL.md) | `validate skills`, `test skills`, `skill health check`, `run conformance tests`, `run the tests`, `how are the tests`, `what's broken`, `daily test run` |
| [transcribe-refiner](transcribe-refiner/SKILL.md) | `clean this transcript`, `refine captions`, `fix this transcript`, `clean up meeting notes` |
| [transcript-pipeline](transcript-pipeline/SKILL.md) | `run transcript pipeline`, `generate class tutorial`, `validate transcript coverage`, `enrich class resources` |
| [two-tier-extraction](two-tier-extraction/SKILL.md) | `two-tier extraction`, `triage then deep read`, `smart model routing`, `cheap triage expensive analysis`, `model escalation pattern`, `route models by content value`, `which model tier for bulk extraction` |
| [ultra-reasoning-operator](ultra-reasoning-operator/SKILL.md) | `ultra reasoning`, `think harder`, `verify everything`, `war room`, `no hallucinations` |
| [voice-note-ingest](voice-note-ingest/SKILL.md) | `voice note`, `ingest this voice memo`, `transcribe and file`, `voice note ingest`, `save this audio note`, `audio message` |
| [webhook-transforms](webhook-transforms/SKILL.md) | `set up webhook`, `process webhook event`, `transform this event` |
