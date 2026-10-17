# AskTheMove teaching presentation

Use a patient coach annotating readable printed matter. This adapts the local
ChessLab `site/DESIGN.md` inspected at commit
`7bef53b8e2a2bd23240da1f71bb2607f08cdd3ab`; no site assets or fonts are copied.

| Job | Default | Rule |
| --- | --- | --- |
| Explanation | Serif prose, ink `#171d29` on paper `#fbfaf4` | Readable long text and clear hierarchy |
| Technical evidence | Monospace code, data and equations | Exact characters, labels and geometry |
| Coach annotation | Short handwriting, blue `#1f48ae` | Explain one identified connection |
| Correction | Red `#c92324` with the word “Correction” | Name what changes and why |

The embedded stylesheet uses local fallback families. Vollkorn, Courier Prime and
Kalam appear only if already available; exact branded font rendering is not
promised. Generated HTML embeds the CSS and needs no font/network request or
package-relative stylesheet. Quotations remain serif. Use existing semantic HTML
for a short coach note, with a visible label when useful:

```html
<div role="note" aria-label="Coach note">
<p>Coach note: doubling both sides preserves the ratio.</p>
</div>
<div role="note" aria-label="Correction">
<p>Correction: doubling only the numerator changes the ratio.</p>
</div>
```

These elements use already accepted attributes. They do not create an animation
or interaction runtime. Keep notes to about 60 words; place long reasoning in the
lesson. Code inside a note remains monospace. Never add handwriting to all text,
unexplained arrows, wobbly diagram geometry, sticky-note decoration or looping
motion.

For rich host artifacts, preserve the same object names, units and semantic colors
across static drawings, animation, controls and video. Explain the input, mechanism,
intermediate states, result and limitations. A changed variable must produce the
stated model effect. Link every annotation to a claim. Drawing/reveal order follows
the explanation, while the complete finished figure stays immediately accessible.
Offer Back/Next/Replay or seeking when they help, with keyboard operation and no
forced autoplay. Reduced motion shows the complete state; no-script delivery keeps
the complete explanation. Videos need captions, transcript and key-state equivalent.

Learner style or accessibility requests override this default at any time. The
static stylesheet follows system dark mode, increased contrast and forced colors.
A host can apply a requested presentation separately without weakening the static
sanitizer. Inspect real output before making browser or accessibility claims.
