# Visual intuition teaching skill: research and initial review

Date: 2026-10-16. Status: research synthesis for design decisions, not a completed CEO review or implemented improvement.

## Finding
The present package contains useful visual and state machinery, but its mandatory attempt-first conversational policy conflicts with the user-approved direction. Improve the reusable skill policy and its supporting references; do not build a new application or make a single lesson the deliverable. This conclusion comes from the current SKILL.md, TEACHING-PROTOCOL.md, MODE-CONTRACT.md, VISUALIZATION-ROUTER.md and the conversation decisions recorded in DECISIONS.md.

## Evidence and design implications

### Mechanisms must be visible
A 2024 experiment on five short science explanations found that causal diagrams improved the quality of participants' written causal explanations, while multiple-choice performance did not distinguish the conditions. It studied short immediate explanations, not long-term retention or all subjects. Design inference: assess missing intermediate relationships and explanations of why a change matters; do not assess visual teaching solely by attractive output or factual recall. [Primary study](https://doi.org/10.22318/icls2024.106268)

A history-coaching study found more accurate, better-structured diagrammatic historical explanations with content-specific guidance and scaffolding. Its domain involved interpretive historical causation rather than experimentally established mechanical laws. Design inference: the general skill must adapt its explanatory form to a domain and preserve uncertainty or competing interpretations. It cannot force every subject into a deterministic machine metaphor. [Primary study](https://ora.ox.ac.uk/objects/uuid:24127083-463c-4756-8878-b62d8176aa87/files/m4dd26202197b129139f385d007c238cb)

### Animation is a tool, not the success criterion
Mayer et al. (2005) compared annotated static illustrations with narrated animations; static presentations performed better in some comparisons and similarly in others. The packages differed in pacing and delivery, so this does not isolate motion or establish universal static superiority. Design inference: select animation for change, timing or transformation that it actually reveals, and retain inspectable key states. [Primary paper](https://adrenaline.ucsd.edu/kirsh/fileupload/illustrations%20vs%20animations.pdf)

Mayer and Chandler (2001) found transfer benefits from learner-paced segments in lightning explanations. That supports meaningful pacing controls within a guided story, not unlimited discovery. The user's complete-delivery default is compatible with segmentation: all scenes can be available together while the learner controls playback. [Primary paper; abstract/indexed evidence, full fetch unavailable in this review](https://tecfa.unige.ch/tecfa/teaching/methodo/Mayer_Chandler01.pdf)

Tversky, Morrison and Betrancourt review why animation can be difficult to apprehend and why comparisons often confound information, motion and interaction. Use as a conceptual review, not another independent experiment. [Review](https://www.tc.columbia.edu/faculty/bt2158/faculty-profile/files/_Morrison_Betrancourt_AnimationCanitfacilitate.pdf)

### Depth comes from explanation, not visual clutter
Harp and Mayer (1998) found that interesting but irrelevant additions impaired recall and transfer in short science lessons. This does not prohibit attractive design; it supports excluding distractions unrelated to the explanation. [Primary paper](https://www.researchgate.net/profile/Richard-Mayer-4/publication/232595492_How_Seductive_Details_Do_Their_Damage_A_Theory_of_Cognitive_Interest_in_Science_Learning/links/57799b8408ae4645d611f204/How-Seductive-Details-Do-Their-Damage-A-Theory-of-Cognitive-Interest-in-Science-Learning.pdf)

Mautone and Mayer (2001) found benefits from signaling explanatory structure. Ozcelik et al. (2010) investigated how signaling guides attention. Design inference: consistent object identity, adjacent labels, sparse meaningful emphasis and explicit transitions should connect prose and visuals; attention is not itself evidence of durable understanding. [Mautone and Mayer](https://www.researchgate.net/publication/232494695_Signaling_as_a_Cognitive_Guide_in_Multimedia_Learning), [Ozcelik et al.](https://www.sciencedirect.com/science/article/pii/S0747563209001459)

Ainsworth's DeFT framework distinguishes how representations complement, constrain and help construct understanding, while emphasizing the extra work of interpreting and coordinating them. Design inference: every extra view must answer a specific question and explicitly map back to the other views. This is a research framework, not proof of one universal template. [Framework](https://www.sciencedirect.com/science/article/abs/pii/S0959475206000259)

### Teach beginners before demanding performance
Sweller and Cooper's algebra experiments support worked examples for acquisition, with transfer limits. Van Gog et al. found worked-example benefits in troubleshooting, but extra process explanations increased effort without improving transfer in that study. Design inference: show an accurate concrete worked example and explain decisive transitions; do not equate deeper teaching with exhaustive narration. [Sweller and Cooper](https://onderwijs.felienne.nl/vakdidactiek/materiaal/sweller_worked_examples.pdf), [Van Gog et al.](https://www.sciencedirect.com/science/article/pii/S095947520600017X)

Roediger and Karpicke (2006) found delayed recall benefits from retrieval practice, with different immediate-test results. The study does not establish that optional practice is better than mandatory practice. Optionality is this user's product decision. Preserve honest state: a viewed lesson is not demonstrated mastery; declined practice does not mean failure. [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/16507066/)

### Reuse mechanisms, avoid building an application
Data Theater separates simulation logic from visual presentation and reduces authoring boilerplate through constrained interaction. Its formative interviews and demonstrations do not establish superior learning. The relevant inference is to reuse available tools and existing runtime primitives rather than require a new general rendering framework. [Author paper](https://lau.ucsd.edu/pubs/Data-Theater-prototyping-explorable-explanations_LIVE-2020.pdf)

Pettigrew and Shearman describe focused mathematical visualizations with accurate outputs, scaffolding and comparative investigation. It is design/development evidence rather than a definitive efficacy trial. [Primary design report](https://doi.org/10.14742/apubs.2014.1276)

### Visual emphasis must retain access to meaning
W3C recommends short identification and detailed equivalents for complex images, including relationships and trends. Its pause/stop/hide guidance addresses moving or updating content under the criterion's stated conditions. Design inference: generated lessons need descriptive alternatives and meaningful playback controls; a screenshot or short alt label is insufficient for an explanatory mechanism. [Complex images](https://www.w3.org/WAI/tutorials/images/complex/), [Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide)

## Proposed reusable production rules
These are design proposals synthesized from research and user decisions, not empirically validated rules for every subject.

1. Establish the requested understanding and a concrete anchor; infer a starting level and ask only for material missing context.
2. Identify the relationships, transformations, distinctions or interpretations that make the idea work. Keep conjecture separate from established mechanism.
3. Plan connected explanatory scenes. Each has a question, an accurate representation, a change or relationship to notice, and an explanation of why it matters.
4. Select representations by those jobs. Motion must expose meaningful change; interaction must change a modeled variable and visibly explain the consequence.
5. Maintain consistent entities and notation; explicitly connect concrete examples, visual models and formal expressions where applicable.
6. Include sufficient inline prerequisite explanation, a useful contrast or boundary case, and a coherent closing mental model. Do not impose a fixed scene count or media quota.
7. Deliver the complete bounded lesson together; honor requests for concise or layered output and different visual forms.
8. Offer one optional understanding check. Follow the learner's next request without forcing practice.
9. Record preferences, coverage and actual performance separately within consented directory state. Resume without a mandatory retrieval barrier.
10. Verify factual semantics, actual rendered output, controls and fallbacks. Name what was checked without claiming human learning from artifact quality.

## Approaches for user selection

A. Revise the existing skill and relevant references, reusing state and visual tooling. Best alignment with current request. Requires explicit new specification version because existing attempt-first gates conflict. Effort medium; main risk is contradictory old references surviving.

B. Add a visual-explanation mode to the existing attempt-first skill. Smallest initial change; preserves existing default but makes the desired behavior secondary and risks duplicated rules. Effort small to medium; main risk is host agents choosing the wrong default.

C. Create an independent replacement teaching skill. Clean separation, but duplicates maintenance and risks losing mature consent/state safeguards. Effort large; main risk is divergence between two active teaching systems.

Recommendation: A. This changes the general teaching experience, not the product category or underlying tool stack. Completeness estimates are design coverage judgments, not measured effectiveness: A 9/10, B 6/10 for the requested default, C 9/10 with more migration work.

## Evaluation direction, not a frozen evaluator
Use the neural-network journey only as a visible development example. Add contrasting domains, such as a physical mechanism, a mathematical relationship, a historical interpretation and a language concept; include novice/expert and tool-limited conditions. Separate adherence to the requested policy, explanation/visual quality, runtime correctness and actual learner outcomes. Keep public examples distinct from hidden evaluation inputs. No new held-out evaluation or learner study has been run.

Before candidate edits, approve a new version of the governing design and freeze acceptance criteria, protected behavior, held-out evaluation arrangements, budgets and rollback. The current production package remains unchanged.

## Methodology and limits
Ten search queries across Exa/web tooling: six in a bounded research subtask and four in the main review. Fifteen distinct sources retained: eight older experimental studies, a recent causal-diagram experiment, a historical-coaching study, two design reports, two conceptual/review sources and W3C guidance (the two W3C pages count as one source organization). Full-paper reads covered animation/static comparison, worked examples and irrelevant details in the research subtask; the main review read the causal-diagram study and W3C complex-image guidance in depth. Some publisher pages were accessible only as abstracts or previews. Research is strongest for bounded science/math explanations, and much is foundational rather than recent. Cross-domain generalization, cross-model reliability, long-term benefit and accessibility for representative learners remain unverified. Source count is not an evidence-quality score.
