# Prax Teach v3 release evidence errata

Date: 2026-10-20
Applies to: published v3.0.0 evidence and result pages
Policy: additive correction; the historical evidence files remain unchanged

1. The reported `56/56` combines 52 automated checks with four human listening
   judgments. Those categories must be reported separately. The learner later
   explicitly confirmed listening to all four clips and said they sounded
   good, so the four human judgments are valid; they are not automated checks.
2. Several review-script fields for explanation order, optional practice,
   fallback behavior, offline behavior, and default persistence were recorded
   as assertions rather than observations. They do not independently verify
   those properties.
3. The activation report described earlier approval more strongly than the
   preserved conversation supports. Activation was performed, but the cited
   approval provenance is ambiguous.
4. The measured routing improvement was one case, observed once per round, and
   the failing case had been disclosed between rounds. The baseline was not run
   through the final end-to-end artifact suite, so no broader end-to-end
   improvement claim is supported.
5. The v3.0.0 release remains downloadable, but its source had four release
   defects found after publication: a mutable rollback target, a divergent
   nested compatibility skill, an integrity-manifest mismatch, and a broken
   standalone `teach-pro-max` path. The current hardening branch repairs these;
   the old tag is not rewritten.
