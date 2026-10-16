# Zero-API runtime boundary

The Visual Lab is a local static artifact. Its trust boundary ends at the browser/document: no provider SDK, API key, network request, telemetry, service-worker update, remote import, CDN, remote font, or hidden subscription automation is allowed. ChatGPT/Codex stays a human-operated tutor and may receive a receipt only after the learner explicitly copies or exports it.

The runtime uses a strict local CSP (`default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'`) and a source scan that rejects remote URLs and forbidden runtime APIs. A missing or unverified runtime routes to the existing static Markdown/HTML path.

Rollback removes only `runtime/prax-visual-lab`, its lesson examples, and its evidence; the existing renderer, router, and installed skill remain untouched.
