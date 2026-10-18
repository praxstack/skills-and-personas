# Verify: the gates

Other gates (values, visual, media) add their own sections here.

## Claims gate (WP7)

Code: `ptk/verify/claims.py`, `ptk/verify/mutation_claims.py`. Rubric: `ptk/verify/rubric.md` (version 2).
Host steps: `references/HOST-ADAPTERS.md`.

### 1. Mapping (`claims.mapping`, automatic)

Every text a learner can see is collected from the artifacts: SVG `<text>` and `<desc>`, the video
compositions, captions, chapters, transcript, the IVE page and its state track, and each projector's
`teaching_texts(build_dir)` (explorer, Q&A, cards). Each one must map:

| Source | Rule |
|---|---|
| claim, alt | every sentence equals a whole sentence of a claim (no fragments, no added words) |
| narration, caption, transcript | equals a storyboard narration line; maps to that line's claims |
| question, option, trace, title, scene title, misconception | equals the model's text exactly |
| fact | equals the captured value, or the `alt_output` chrome string filled with those values |
| chrome | matches its `chrome.json` string; each `{slot}` takes only values this lesson can hold (topic, program paths, compiler, fact values, integers) |
| chrome with claims (template) | matches its `chrome.json` string, cites real claims, and every filled instance goes to the reviewer |

Anything else fails with `ClaimsUnmapped`. `tests/test_lint_claims.py` fails if a template or
projector hard-codes a sentence that isn't in `chrome.json`.

### 2. Jobs (`ptk build`)

`build/claims-jobs/` gets one lesson job, up to 12 mutation jobs and one control per mutation.
A control is an unchanged copy of the lesson job. Nothing in a job says which it is; the roles live
in `$PTK_STATE/claims-private/`, outside the lesson tree.

A job carries only teaching texts: claims, narration and captions, alt text, questions and options,
trace labels, titles, card and Q&A sentences, filled templates. Code, chrome strings and number labels
are counted and hashed in `inputs.not_sent`, not sent. The switch slice's job went from about
13,100 tokens to about 5,400 to 6,800 (characters / 4), plus about 1,900 for the rubric.

**Manifest:** sha256 of the whole lesson model, of the job body the reviewer sees, of every artifact
text (sent or not), of the claim sources and program sources, plus the rubric version and the
rubric's sha256, plus a per-job slot. The review must echo `manifest_sha256`. `ptk claims check`
recomputes every manifest from the current inputs, so any edit (lesson, artifact text, source,
rubric) makes the old review stale.

### 3. Mutations (E22)

Authored in `lessons/<id>/mutations.json`, each with `id`, `kind`, `target` (a claim id, or
`narration:<sc.i>`, `trace:<id>`, `question:<sc>`), then `find`/`replace`, or `sources`,
`justification`, `claim_kind` overrides, and `why_false`. Kinds: `false-mechanism`, `overbroad`,
`dropped-caveat`, `wrong-citation`, `false-framing`, `ub-dishonest`, `false-narration` (claim family)
and `value-swap` (value family). ptk adds automatic value swaps: a captured value in a claim that
cites it, replaced by a different value, in the claim and every text mapped to it.

A mutation whose anchor text is gone (the lesson was edited) is skipped and listed, never counted.
A mutation must not restate `misconceptions[]` (word overlap under 0.5).

Caught means: the review rejects overall **and** rejects the planted claim or a text the mutation
changed. Rejecting some other claim isn't a catch.

### 4. Check (`ptk claims check`)

| Review | Result |
|---|---|
| empty, prose, refusal, wrong schema, missing or duplicate ids, `overall` not following the verdicts | first time: moved to `claims-review/invalid/`, job gets a `retry` block with a schema reminder, status stays `claims-pending`; second time: `ClaimsReviewInvalid` |
| rubric version or manifest differs from the job, or the job differs from the current inputs | stale, gate fails |
| missing | `not-run`, build `incomplete` |

Gates:
- `claims.review`: the lesson job is accepted with no rejected claim or text.
- `claims.sensitivity`: value mutations caught 100%, claim mutations caught 90% or more, controls
  accepted 95% or more. Schema rejections are counted on their own and never as catches.

Every verdict is an LLM-reviewed finding, not a proof.

### 5. Rubric v2 in short

The strict rule (true as worded, not roughly), then five lenses applied to text: maths (values equal
facts), explanation (mechanism, mechanism-not-metrics, no overgeneralising, caveats kept, analogy
limits, UB and implementation-defined honesty, sources, misconceptions), looks (titles, alt text),
interaction (questions don't leak answers, options and trace labels true), media and portability
(captions match, no colour-only or medium-only wording). The `%f` "same bits" case is deliberately
not in the rubric: it is the held-out regression.
