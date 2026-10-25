# Bounded runtime verification — 25 October 2026

Original authored inputs were executed with existing provisioned local tools, without installs, source repairs or paid APIs. This is trusted host execution, not an isolated hostile-code claim. No subjective listening or every-client UI claim is made.

- Manim0.22.0, shared-resolver Python3.12.13: original vector-addition scene rendered1280×720 H.264,4seconds/60frames,642411bytes. [Actual MP4](evidence/manim-addition/build/silent.mp4), [inspected final frame](evidence/manim-addition-frame-2.png), [successful commands](commands-addition.json), [media identity](addition-media.json). One initial authored Python list/scalar error was corrected; its failure is retained separately. No runtime/evaluator changed.
- Original Manim translation and hand-drawn JavaScript canvas also rendered2seconds/30frames. Full ffmpeg decoding exited0 for all three outputs. [Hand-drawn MP4](evidence/handdrawn/build/probe.mp4), [commands](commands.json), [metadata/hashes](media.json).
- The vector scene uses u=(2,0), v=(0,1), tip-to-tail addition and actual resultant(2,1). Three frames were inspected, including the complete endpoint/axes/labels.

## Complete inventory

[Capability matrix](capability-matrix.json) records all47 registry entries and separates raw discovery from actual runtime evidence. [Package resolution](package-probe.json) checks the workspace, teacher, scoped Node and global npm roots. Eight optional JavaScript engine packages are absent in those roots despite raw registry detection from Node alone. CDN-only/host-only capabilities remain unverified; missing Python/CLI prerequisites are explicit. Detection is not a successful render, and absence in these roots does not mean no copy exists anywhere on disk.

Kokoro ONNX, the standard lesson/course renderer and visual QA have scoped prerequisites available but were not executed in this optional-engine probe. Their actual course-level results are recorded with the GATE DA suite separately. Manim prose mentions0.21.0 while actual resolved runtime is0.22.0; these receipts bind the actual version.

The full local probe record and every extracted frame remain in this plan's retained execution workspace. The selected public evidence here is additive and does not replace prior release regressions.
