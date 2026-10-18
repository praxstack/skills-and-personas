# Lesson model: the authoring contract

You, the host agent, turn a learner's request into one `lesson.json` (schema `prax-teach/lesson@1`, file `schemas/lesson.schema.json`) plus the C programs it shows. ptk does the rest: it captures real values, projects the media and runs the gates. You write prose and structure. You never type a displayed value.

## The loop

1. `ptk new <slug> --dir lessons` writes `lessons/<slug>/lesson.json` and `programs/main.c`. Every prose field holds a `TODO:` placeholder.
2. Write the programs, then fill the model in this order: programs, facts, claims, misconceptions, trace, storyboard, figure. Later sections cite earlier ones by id.
3. Run `ptk validate lessons/<slug>`. Exit 0 means valid. Exit 3 prints `{"valid": false, "errors": [{"pointer", "message"}]}`. Each pointer is an RFC 6901 path into `lesson.json`, such as `/storyboard/2/narration/0/claims/1`.
4. Fix exactly what each pointer names, then validate again. **Repair each error at most twice.** If the same pointer fails a third time, stop and tell the learner which field you couldn't satisfy and why. Don't delete content to make an error go away.
5. Run `ptk capture` or `ptk build`. Capture fills `facts[].value`, `facts[].source`, `programs[].diagnostics`, `programs[].source_sha256` and `platform`. Never write those fields yourself.

Exit codes: 0 done, 1 a gate failed, 2 host problem (for example, no `sandbox-exec`), 3 model error, 4 claims review pending, 5 incomplete, 6 degraded.

## Sections

**programs[]**: C17 sources under `programs/`.
- Each program compiles with `clang -std=c17 -Wall -Wextra -Wformat=2 -fsanitize=undefined,address` inside the capture sandbox, then runs twice. The two runs must print the same bytes, or capture fails with `NondeterministicOutput`. Avoid addresses, time, pids and random numbers.
- The sandbox denies network, `fork`, writes outside the temp dir, and reading files outside the program's own dir and the toolchain. That includes `#include` and `#embed` of other files.
- A compiler warning, ASan or UBSan finding fails capture with `SanitizerFinding`.
- A program may not switch off its own guard. Capture and `ptk validate` refuse, by name, any `#pragma` other than `STDC` and `pack`, `_Pragma`, GNU line markers (`# 1 "x.h" 3`), `#line`, `#embed`, `no_sanitize`-style attributes, sanitizer hooks (`__asan_*`, `__ubsan_*`, `__sanitizer_*`), `asm` and `dlsym`. Capture checks clang's own `-E` output too, so pasting one together in a macro fails the same way (exit 3, the construct named at `/programs/i/path`). Only a program that never runs may use one, and only when a claim lists the program in `programs` and the construct in `overrides`.
- Program files are read with no symlink followed. A symlinked `programs/` or program file is refused. Compiler errors show diagnostics about the program's own file only.
- To teach undefined behaviour on purpose, set `ub: true` and `run: false`, and add an `undefined-behaviour` claim that lists the program in `programs`. That program compiles and its warnings are recorded, but it never runs, so no fact can read its output. A clean sanitizer run means "no finding", never "no UB".
- gcc-16 compiles every program for diagnostics only. Its warnings are recorded and never block.

**facts[]**: one per displayed value.
- `select` says where capture reads the value. Use `{"stream": "stdout", "line": N}` for one line, `{"stream": "stdout", "line": N, "field": K}` for the K-th whitespace-separated token of that line (kind `derived`), `{"stream": "stdout"}` for the whole output, or `{"stream": "platform", "key": "sizeof.int"}`. Platform keys are `sizeof.<char|short|int|long|long long|float|double|void*>`, `char_signed`, `endianness`, `libc`, `os`, `arch` and `compilers.<clang|gcc-16>`. Any other key is a model error at `/facts/i/select/key`.
- `expect` is required, and it must be independent of the run. Use `{"fn": name, "args": [...]}` to name a pure function in `ptk/expect.py`: `bits`, `hex`, `printf_d`, `printf_u`, `printf_x`, `printf_f`, `printf_g`, `printf_c`, `ascii`, `sizeof_abi`, `sum`, `factorial`, `factorial_frames`, `factorial_event`, `factorial_stdout`, `call_label`, `double_bits_hex`, `neuron_term`, `neuron_sum`, `neuron_relu` (and their `_line` forms), `switch_line` or `switch_stdout`. Only when no function fits, use `{"value": "...", "reviewed": true}`, a literal that the claims reviewer checks.
- For a `sizeof` fact use `{"fn": "sizeof_abi", "args": ["int"]}` (data model LP64 by default, or `"LLP64"`, `"ILP32"`). It comes from a table in `ptk/expect.py`, never from the capture.
- If the capture differs from `expect`, the build fails with `ExpectationMismatch` and shows both values. A fact that selects a line the program never printed fails the same way, with the line count as the reason. Fix the program or the expectation. Never copy the captured value into `expect`.

**claims[]**: every teaching sentence. A sentence that appears in an artifact and isn't a claim, a narration line citing claims, or a `templates/chrome.json` string fails the build.
- `kind` is one of:
  - `definition`: what a term means;
  - `mechanism`: what the machine does, step by step;
  - `rule`: what the standard requires;
  - `caveat`: a limit or exception;
  - `undefined-behaviour`: the standard imposes no requirement;
  - `implementation-defined`: the implementation chooses and documents it (cite the platform fact);
  - `framing`: what this lesson's program does, with no claim beyond its source.
- `justification` explains why the sentence is true. `sources` cites at least one source: a C17 clause with a short quote, or the lesson's own program file. `facts` lists the facts whose values the sentence states.
- One idea per claim. Don't round, generalise or soften the text after review: any edit invalidates the review.

**misconceptions[]**: a wrong belief in the learner's words, and the claim that corrects it. Quizzes, Q&A and cards route wrong answers here.

**programs[].show**: `{"from": a, "to": b}`, the lines every listing shows. Set it when the program has a function before `main` (default: main's body).

**trace[]**: the states an explorer can show.
- Each state has `program`, `line`, the executed `path` (in order, repeats kept: a recursive call jumps back up), the `output` facts so far, `vars`, and optionally `frames` (the call stack, outermost first). A frame has `fn`, optional `call` (a fact that labels it, such as `factorial(2)`), `status` (`running`, `waiting`, `returning`) and, while returning, `ret` (the fact it returns).
- `reveals` lists the facts that this state shows for the first time.

**storyboard[]**: the video's scenes, in order.
- `state` is the trace state on screen.
- `narration[]` lines each cite the claims they state, and may carry a `spoken` respelling for TTS.
- `question` asks for a prediction. `answer_fact` names the answer. The scene's own state must not already show the answer, and no narration, caption or chapter title before the answer cue may state it. Optional `options` must have exactly one correct choice, and each wrong option names the misconception it reveals.
- `title_claims` tags a scene title with the claims it states or implies (`[]` for a neutral title). Every scene after a question needs it. A title that states the question's answer (it cites a claim about the answer fact or a part of it, or a claim the answer scene narrates) stays sealed in the IVE chapter list and the Q&A until the learner answers. A title at or before the question may not cite such a claim, and neither may the lesson's top-level `title_claims`.
- `ask` (optional): one bounded question the Q&A asks before it reveals the scene, in written forms (`%f`, `factorial(2)`), at most 60 characters before its one question mark. Without it the layer is a walkthrough step.
- Write `text` in written forms (`%f`, `ub.c`, `factorial(2)`) and put the spoken form in `spoken`; captions, the transcript and the Q&A show `text`, only TTS reads `spoken`. `lexicon/c.json` already speaks `%d`, `%u`, `%f`, `%c`, `%g` and the lessons' file names.
- A question scene's narration invites the pick ("Which answer do you predict? Pick one of the three before the answer plays."). The IVE stops there until the learner picks; the plain video gives 8 s under a bar.
- `key_nodes` names the figure elements that carry the mechanism in that scene. They must stay fully visible, with no inner scroll, at 390 px and 1440 px. A `code-trace` figure has `code`, `output`, `question`, `note` and `compare`, and `figure.elements` can add more.

**figure**: the still's layout. `kind: code-trace` takes the program, its trace states, notes pinned to lines (each a claim), an optional comparison program and state, and caption claims.
- `misconception`: one misconception the still shows as a labelled wrong belief with its correcting claim.
- `panel`: a mechanism diagram, drawn from facts in every medium; its element id is `panel`. Each element appears in a state once its fact is shown (the state's output, a reveal, or a token of a printed line).
  - `views`: one value through several printf conversions. `value {var, line, bits, hex}`, `lanes [{line, fact, via?, claim?}]` (a `via` fact is the converted value, such as the double's bits), `ub {program, line, claim, after}`.
  - `stack`: the call stack of each state's `frames`. The still draws every figure state side by side; pages and the film draw one state.
  - `neuron`: multiply, add and gate panels. `terms [{x, w, t}]`, `bias`, `sum`, `out`, `gate {line}`.
  - `place`: `side` (beside the program) or `hero` (full width above it).
  - `vars` (stack): `{"param": "n", "result": "r"}`. Every frame then shows its own n (the argument in its `call` fact) and r: `r = ?` before its declaration, `r = 3 * ▢` while it waits on its call line, the received value once a frame names it in `got`, and its `ret` when it returns. Give each frame its `line`.
- `explore`: the explorer's knob, one input the learner changes.
  - `values`: one captured run per value of `var` (`values[]: {value, program, facts: {role: fact}, claims}`), shown as a table; roles `bits`, `hex`, `d`, `u`, `f`, and `char` or `byte`.
  - `calls`: one captured run per argument, its whole stdout one fact (`facts: {out}`); the explorer replays it call by call with every frame's n and r.
  - `neuron`: `sliders [{var, min, max, step}]` over w2 and b, every point from `ptk/expect_neuron.py`; `checks [{program, at, facts}]` name variant programs captured at a few points, which must print exactly the grid's lines.
- `subject` (top level): the kicker's first part, default `C`.

**requested_media**: the media to build, from `still`, `explorer`, `qa`, `cards`, `video` and `ive`.

## Mechanism, not metrics (D20.5)

Every summary view is paired with the mechanism step that produced it. A total, a final output, a comparison or a result is never shown on its own. The learner first sees the step that computes it: the loop that adds, the frames that return, the case labels that fall through.

In the model, a summary scene sets `"view": "summary"` and `"mechanism": "<trace state id>"`. That state must already be on screen in the same or an earlier scene, or `ptk validate` fails at `/storyboard/<i>/mechanism`. The claims reviewer also checks this rule in prose. A narration line like "the sum is 10" needs the adding step before it.

## Writing a lesson from a request

1. Find the one mechanism the request is about, and the smallest C program that shows it. Use two programs when a contrast teaches it, such as with and without `break`.
2. List what the learner must see: each printed line, each variable value, each platform fact. Each becomes a fact with an independent `expect`.
3. Write the claims, one idea each, with the clause that makes each true. Write the misconception that the lesson corrects.
4. Lay out the trace states that the mechanism passes through. Then write the storyboard: setup, a prediction question, the mechanism step by step, the answer, and the summary paired with its mechanism.
5. Validate, repair (at most twice per error), then build.
