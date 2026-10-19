# Independent general-lesson content audit — initial snapshot

Read-only product audit by the C-adapter worker, who did not author these three general lessons. This is a bounded content review, not full release acceptance. Original source snapshots and SHA-256 values are retained under this directory. Root began correcting wording during this audit; these findings refer to the retained originals, not an assumed final rerender.

## Numeric findings

`python3 audit-numbers.py` runs the actual snapshotted JavaScript models, then compares them with independently constructed exact arithmetic:

- **Base rates:** all **53,550** allowed parameter states (50 priors × 51 hit rates × 21 false-flag rates). All integer contingency counts match. Posterior is independently calculated through Bayes odds, `1 / (1 + prior_odds_against × false_rate / hit_rate)`, using `Fraction`; maximum absolute difference after conversion to binary64 is **0**. Flagged counts are positive throughout this supported domain.
- **Diffusion:** all **14,091** allowed states (61 initial splits × 11 crossing chances × 21 tick counts). An exact iterative one-particle Markov update, `p_next = p(1-k) + (1-p)k`, is compared with the JS closed form. Maximum absolute difference across left/right counts, directional traffic, net traffic and next-left is **7.105427357601002e-15**. Exact conservation and bounds hold. This checks the stated two-compartment expectation model, not empirical diffusion or an individual particle simulation.
- **Dots:** the real source figure function was invoked at every diffusion state in wide and narrow modes: **28,182** draws, each containing exactly **60** circles. The complementary rounding repair conserves dots, including ties.
- **Grammar model:** all eight allowed voice/example/agent combinations were enumerated. The two active sentences, four passive variants and omitted-agent information agree with the limited examples. This does not prove a general grammar theorem.

Counterexamples and raw summary: `numeric-results.json`. Model checks supplied by the author were not used as proof.

## P1 findings: actual caption/diagram mismatch

**V1 — diffusion film, transition into “Dynamic balance.”**

- Original source: `snapshots/diffusion.lesson.js`, film chapter “Dynamic balance” (original line 42), says: “With thirty on each side, expected traffic is six in each direction. Net flow is zero”. The selected target is `{initialLeft:30,cross:0.2,ticks:0}`.
- Actual `lessons/diffusion/lesson.mp4`, **42.75 s**, displays that caption while the diagram still shows **31.3 left, 28.7 right, traffic 6.3/5.7, net 0.53**. The chapter title already says “Dynamic balance.”
- Frame proof: `diffusion-transition-42.75.png`. Timing lists narration start at 42.602333 s.
- The numerical model is not the defect. The scene has not reached the state the caption is explaining. Complete the transition before this exact-state narration/caption, or explicitly narrate the transition first. Do not adjust the numeric oracle or suppress the frame check.

**V2 — base-rate partial film, transition into “An edge case.”**

- Original source: `snapshots/base-rates.lesson.js`, film chapter “An edge case” (original line 42), says: “With no false flags, every flagged item is defective in this model.” Target `{base:10,hit:90,falseRate:0}` has 900 true flags, 0 false flags, precision 1.
- Actual `lessons/base-rates/lesson.partial.mp4`, **48.7 s**, displays that caption while the diagram still shows **450 false flags, 1,350 total flags and 66.7%**. Narration start is 48.542125 s.
- Frame proof: `base-transition-48.7.png`. This is the available partial render, not a claim about a later final MP4. Its filename/status must stay explicit.
- Same timing repair as V1. The statement is mathematically true under its stated condition; the simultaneously illustrated state does not meet that condition.

## P2 findings: missing boundary qualifications

**W1 — strict base-rate growth has a saturation exception.**

- `snapshots/base-rates.lesson.js:35`, step `limits`: “Keep detector rates fixed and raise the defect rate: the flagged group contains a larger defective share.” The step allows `falseRate` to reach 0.
- At hit 90 and falseRate 0, base 1 gives 90/90 = 1 and base 50 gives 4500/4500 = 1: no strictly larger share. With positive false-flag rate and supported positive hit rates, strict growth holds.
- Suggested qualification: a larger share **when false flags are possible**; at zero false flags it is already 100%. The step's initial falseRate 5 and later edge-case explanation mitigate severity, but the wording remains visible during the permitted saturated control state.

**W2 — a closed barrier does not relax the imbalance.**

- `snapshots/diffusion.lesson.js:35`, step `relax`, title “The imbalance shrinks” and note “The gradient fades as opposing traffic balances.” This step exposes the crossing-chance control, which includes 0.
- Counterexample `{initialLeft:48,cross:0,ticks:20}` gives 48 left, 12 right, net 0; the imbalance is unchanged for every tick. Positive crossing chance is needed for relaxation of a nonzero imbalance. Equal initial populations also have no imbalance to shrink.
- The diagram correctly says “No crossings through the barrier” at zero crossing chance, and another step explains the closed barrier. Qualify the relaxation title/note for an open barrier rather than contradicting that correct diagram.

## Grammar and primary sources

I reviewed all source explanation, practice options/corrections, model outputs and film text for the two stated past-simple transitive examples. The passive subject/agent distinction, optional by-phrase, information lost on omission and context-sensitive choice are supported by the primary teaching references. I found no additional concrete P1 in those limited grammar examples. In particular, the distractors are visibly practice alternatives, not asserted rules; the source explicitly limits scope and separates topic from stress/new-information focus.

Primary references opened live:

- [British Council: Passives](https://learnenglish.britishcouncil.org/free-resources/grammar/b1-b2/passives): passive choice and `be + past participle`, with optional agent. It lists past-simple `was/were + past participle`; the lesson's singular subjects correctly take `was`.
- [British Council: Active and passive voice](https://learnenglish.britishcouncil.org/free-resources/grammar/english-grammar-reference/active-passive-voice): active/passive transitive examples and by-phrases. Its additional constructions underscore why the lesson's explicit example limits matter.
- [OpenStax Statistics: Terminology](https://openstax.org/books/introductory-statistics-2e/pages/3-1-terminology): conditional probability restricts the denominator to the conditioning event, with positive denominator.
- [OpenStax Statistics: Tree and Venn Diagrams](https://openstax.org/books/introductory-statistics-2e/pages/3-5-tree-and-venn-diagrams): branch/joint-event context.
- [OpenStax Biology: Passive Transport](https://openstax.org/books/biology/pages/5-2-passive-transport): random molecular motion and continuing motion at dynamic equilibrium.
- [OpenStax Chemistry: Effusion and Diffusion](https://openstax.org/books/chemistry-atoms-first/pages/8-4-effusion-and-diffusion-of-gases): opposing transfers at equal concentration and diffusion from random motion. The source supports the mechanism, not the lesson's invented 60-particle calibration.
- Cambridge passive page returned **403** in this audit. Its contents were not independently corroborated here; the two accessible British Council primary pages suffice for the limited examples.

## Rendered scope and remaining uncertainty

Opened the three actual explorers at **1440 and 390 px**, light scheme. The default diagrams had no SVG text outside their viewBoxes and no document horizontal overflow. Diffusion displayed 60 dots in both. Read `render-results.json` and the six screenshots for exact artifact hashes/states. This is not an exhaustive visual-state/contrast/accessibility audit.

Inspected the actual voice still PNG/SVG, its standalone card export, and actual diffusion/base-rate contact sheets. Default base-rate diagram values 100/9900, 90/495, 585 and approximately 15.4% agree with the independent calculation. Default diffusion values 48/12, 9.6/2.4 and 7.2 agree. Base boxes explicitly disclaim area scaling; the final bar is proportional to the flagged counts. Voice cards retain their example/title, explanation and model limits.

The math/science six-format final bundles were not available at the initial inventory; final standalone exports require a separate current-artifact check. Audio quality, pronunciation/prosody, complete caption timing, full playback, keyboard operation, dark mode and every video frame were not independently reviewed. Speech-percentage or author-reported pass claims are not substituted for those checks. This audit does **not** certify that every statement or every medium is correct.

No product, test, evaluator or hidden case was edited. No commit or push was made.


## Final math/science recheck — originals retained

The later final MP4 files were independently re-extracted at the original bad positions and at the new exact scene `voiceAt + 0.2 s`. Hashes, timing and extracted-frame hashes are in `final-temporal-results.json`; corrected source snapshots have distinct `.corrected.lesson.js` names.

- **V1 sampled regression resolved:** final diffusion at **45.364625 s** shows 30.0/30.0, opposing 6.0/6.0 traffic and net 0.00 while the caption describes thirty each, six each and zero net. At old **42.75 s**, it now shows the earlier relaxation state 31.4/28.6 and net 0.56 with its matching open-barrier explanation.
- **V2 sampled regression resolved:** final base rates at **50.6705 s** shows 900 true flags, 0 false flags, 900 total flags and 100.0% while the zero-false-flags caption is visible. At old **48.7 s**, it now shows the earlier 900/450/1350 and 66.7% state with the positive-false-rate explanation.
- **W1 wording corrected:** current base-rate step `limits` explicitly conditions strict increase on a positive false-flag rate and says the share is already 100% when false flags are zero. The retained exact saturation counterexample is respected.
- **W2 wording corrected:** current diffusion step `relax` names an open barrier/positive crossing chance and explicitly says zero chance preserves the imbalance. The retained zero-crossing counterexample is respected.

These conclusions cover the named counterexamples and four actual extracted frames. They do not establish complete temporal correctness of every frame, audio intelligibility or prosody. The grammar final rerender was not yet ready during this recheck.


## Final grammar temporal samples

Opened actual final MP4 frames for all five scenes at `voiceAt + 0.2 s`: **1.300, 9.85225, 21.890875, 32.990125 and 45.65675 s**. The first two display Maya/bicycle with active and passive emphasis respectively; the third displays team/gate with the passive pattern. The final two display passive sentences without the by-phrase and explicitly explain that the sentence does not identify the doer. Their captions agree with the diagram and selected state at these sampled positions. No additional concrete P1 was found in these five samples.

`final-grammar-temporal-results.json` preserves timing, frame hashes and the final root/bundle video hash, which matches: `ec3905cd8e07545327af5f8678961698993179f857966fff61c03f1921714944`. These are sampled temporal checks, not every-frame or full-playback evidence. Audio intelligibility, pronunciation and human prosody remain unverified by this reviewer.


## Candidate2 public explorer check

The three current source files are byte-identical to the previously audited final sources. Actual widened explorers were checked at 1440/390 in light/dark, with first-range edits and all four chapter initial states: 48 geometry cases, zero measured document/SVG text overflow, diffusion always 60 dots. Arithmetic and boundary qualifications remain consistent in the reviewed outputs. Scope and visual judgments are in `candidate2-public/REVIEW.md`; the prior numeric and temporal evidence is retained without replacement. No new full-playback or subjective audio judgment is asserted.
