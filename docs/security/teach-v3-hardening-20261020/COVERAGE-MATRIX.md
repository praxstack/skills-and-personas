# Coverage of Claude's verdict and the security review

Checked against repository revision `8514b97`, after v3.0.1 publication.
This is a status correction and inventory, not a new security certification.
A shipped patch does not close every recommendation in the original review.

## Claude's ten findings

| Original item | Current state | Evidence or remaining work |
|---|---|---|
| 1. Mutable rollback target | Fixed | Old rollback points to a preserved snapshot; v3.0.1 has separate versioned targets and a successful rollback dry run. |
| 2. Divergent nested teach-pro-max | Fixed | Nested copy removed; installer does not expose it as the public alias. |
| 3. Distribution self-check fails | Fixed | Accepted embedded artifact restored; 759-file verifier passes. |
| 4. Standalone install fails | Fixed | Complete local fallback; actual standalone skills CLI install and ZIP install passed without teacher. |
| 5. 56/56 mixes automated and human results | Reporting corrected; historical form not reconstructed | Current README/guide distinguish 52 automated criteria from four listening approvals. User confirmed all four; no invented per-clip measurements were added. Historical receipts remain unchanged. |
| 6. Script assertions presented as checks | Open; disclosure corrected | Errata identify the asserted fields. Real behavioral evidence and a separately versioned evaluator are still needed. Governing changes need explicit approval under the identity-preservation policy. |
| 7. Old activation approval overstated | Historical errata issued | The original provenance remains ambiguous. The later v3.0.1 activation follows the explicit continuation authorization and has a new local receipt. |
| 8. Thin/disclosed routing improvement | Reporting corrected; improvement unproven | The one-case gain and absent baseline E2E comparison are disclosed. No fresh uncontaminated improvement study has been run. |
| 9. Practice-first references | Fixed in current teacher | Subject/series defaults corrected and canonical precedence added. Historical embedded implementation remains subordinate to the wrapper's explanation-first rule. |
| 10. Public side-branch material/archives | Open | Inventory and cleanup plan exist. Removing current files does not erase historical Git objects. Destructive ref deletion/history rewrite requires a specific decision. |
| Film/still quality below original ambition | Open | Security release did not rebuild exemplar lessons into a new mechanism-animation standard. Passing technical checks is not visual acceptance. |

The later private bank must not be confused with the older public evaluation
holdout. Older public prompts are no longer held out. No new privacy guarantee
for all historical branches is made here.

## Eleven security findings

| ID | Status | Actual boundary |
|---|---|---|
| SEC-001 upload escape | Fixed at reported upload entry | Portable IDs, confinement, links rejected; validation/hash/upload bind to one descriptor. |
| SEC-002 shell eval | Fixed | Sink removed; fixed allowlisted actions need separate repair authorization. |
| SEC-003 host execution | Default path and code-checker isolation fixed; broader rendering isolation open | Structural checking does not execute code; whole checker has a restricted Docker mode. Reviewed first-party host execution remains explicit. Entire hostile courses and other rendering helpers do not yet have one automatic portable isolation adapter. |
| SEC-004 domainless cookies | Fixed at enrichment entry | Domainless format rejected, exact-host sessions and origin rules enforced. |
| SEC-005 internal-network requests | Fixed in the patched transport | Numeric validated addresses used at connect time; browser HTTP goes through broker; redirects/origins checked, service workers disabled, WS upstream isolated. Live personal Canva authentication was not exercised. |
| SEC-006 mutable bootstrap | Fixed in the cited appendix | Does not mean all installation instructions throughout the portfolio have been pinned. |
| SEC-007 journal links | Fixed in Teacher journal | Descriptor-relative no-follow access, ownership/link checks and atomic writes. |
| SEC-008 course paths | Fixed in the tested course workflow | Private snapshots consumed by extract/build/test/narration and descriptor-relative output publication; linked-course behavior preserved. |
| SEC-009 unbounded resources | Partially fixed; earlier closure overstated | Response/capture limits and browser transfer allowance exist. Resource-count and total-job byte/disk/time quotas, plus browser-process CPU/memory ceilings, remain open. |
| SEC-010 journal modes | Fixed | 0700 directories, 0600 files; ambient umask is not the privacy control. |
| SEC-011 active citations | Fixed at the reported template sink | Schemes allowlisted and CSP added. Portfolio-wide HTML sanitization and isolated artifact hosting remain broader work. |

The previous statement that all security areas were fully repaired was too
broad. The tested patches remain shipped; the unresolved boundaries above must
not inherit a passing status from those focused tests.

## Portfolio recommendations from the full skill-gap review

| Original recommendation | Current state |
|---|---|
| 1. Remove eval | Delivered for skillpack-check. |
| 2. One execution trust/isolation contract | Partial: checker delivered; whole-course/renderer isolation remains. |
| 3. One fetch policy and total job quotas | Partial: transport enforced inside enrichment; shared portfolio library and complete job quotas remain. |
| 4. One safe-path/private-state library | Partial: course and journal hardened separately; no portfolio-wide consolidation. |
| 5. Reproducible/stale-proof archives | Deterministic generator and current archives delivered; CI does not yet compare every archive to the accepted source tree. |
| 6. Collapse 13 duplicate identities | Open: live inventory still has 129 entries, 116 unique names and 13 duplicate names across skills/new-skills. Removing the nested teacher copy did not solve these separate pairs. |
| 7. Consistent portfolio evidence | Open: old reports not regenerated as current evidence; link checker still hardcodes a former home path. |
| 8. Comprehensive CI | Partial: focused security workflow passes; whole-portfolio lint, links, duplicates, dependency locks, archive freshness and ongoing secret checks are not all covered. |
| 9. Standalone teacher injection boundary | Delivered in teacher/SKILL.md. |
| 10. Minimum allowed-tools declarations | Open: live scan finds zero declarations among the 129 top-level entrypoints. Scope metadata must not be mistaken for enforced authorization. |
| 11. Setup vs offline runtime | Partial: policy and diagram default corrected; Kokoro can still download missing assets and Pyodide loads a CDN runtime. Other optional engines need their own audit. |
| 12. Generated artifact safety | Partial: reported citation sink/CSP fixed; mature sanitization and isolated execution origins are not universal. |
| 13. Pin all installation instructions | Partial: cited bootstrap fixed; no completed portfolio-wide pin audit. |
| 14. Learner privacy consistency | Teacher journal hardening delivered; shared implementation and every-engine parity still need verification. |
| 15. Expand SECURITY.md | Open: policy still names skill files and .skill archives, and its GitHub-direct-message fallback is not a concrete verified private reporting channel. |

## Next work, in order

1. Close SEC-009 job quotas and resource-process limits with negative tests and
   ordinary controls; keep the existing acceptance thresholds unchanged.
2. Extend restricted execution to whole-course extraction/rendering while
   preserving the safe structural/default path.
3. Repair current portfolio inventory, paths and duplicate identities without
   silently replacing divergent skills; add CI for those product checks.
4. Enforce explicit setup/network boundaries in optional engines and Pyodide;
   document enforceable host capability scopes and expand the security policy.
5. Propose a separately versioned behavior evaluator with observable checks,
   a fresh private bank and a baseline comparison. Do not edit the frozen one.
6. Build and review substantially improved stills, explorers and animated films
   against the original visual objective. No security score substitutes for it.
7. Execute public-history cleanup only after the exact destructive plan is approved.
