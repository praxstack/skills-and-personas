# TODOS

## P2: Learner compile-and-trace server (CEO D4.12)
- **What:** A localhost service that compiles and traces the learner's own edited C in explorers.
- **Why:** The explorers would run Prax's code, not just captured examples.
- **Pros:** Live experimentation with exact results.
- **Cons:** It runs untrusted code from a browser, so it needs its own threat model (origin checks, sandbox, rate limits).
- **Context:** Deferred from the v2.1 CEO review on 2026-10-18. Start from the capture runner's sandbox (WP2) and cpx's process handling.
- **Effort:** L, about M with CC. **Depends on:** v2.1 accepted.

## P2: Topic packs for C++, DSA and GATE CS (D4.16)
- **What:** Lesson packs built with the v2.1 compiler.
- **Why:** These are the next stages of Prax's plan after C.
- **Cons:** Large content effort. Every claim needs review.
- **Context:** Needs v2.1's lesson model and gates. **Effort:** XL, about L with CC.

## P3: Manim math track (D4.14, D4.15)
- **What:** Enable Manim `MathTex` once a LaTeX or Typst install is approved.
- **Why:** 3Blue1Brown-grade derivations for recurrences and the master theorem.
- **Cons:** About 100 MB to 4 GB of TeX installed on the host. Needs Prax's OK.
- **Effort:** M.

## P3: cpx integration
- **What:** Cards and exam drills write to the C repo's attempt log, so `cpx revisit` schedules them.
- **Why:** One spaced-review loop instead of two.
- **Effort:** M. **Depends on:** v2.1 accepted. The C repo's attempt log format is in `tools/cpx/attempts.py`.
