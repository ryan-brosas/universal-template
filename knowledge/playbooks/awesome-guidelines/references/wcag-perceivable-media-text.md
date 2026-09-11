<!-- capsule-v2 -->
# Perceivable — do text alternatives, structure, and contrast meet WCAG 2.1 Level AA?

**Source:** WCAG 2.1 Principle 1; Understanding 1.1.1, 1.3.1, 1.4.3, 1.4.10. **Question:** Can users perceive content without vision, without color-only cues, and at 200% zoom?

## Media and text seam
**Path/Symbol:** images, video, audio, icons, charts in web UI.
**Signature:** equivalent text; decorative empty alt; captions where required.
**Data Shape:** `alt`, `aria-label`, `<track kind="captions">`, transcripts.

### Decisive pattern
```html
<img src="revenue-q3.png" alt="Q3 revenue rose 12% to $4.2M.">
<img src="divider.svg" alt="" role="presentation">
<video controls>
  <track kind="captions" srclang="en" src="promo.en.vtt">
</video>
```

**Flow:** **1.1.1** — every non-text content has text alternative serving equivalent purpose → controls/inputs named (ties **4.1.2**) → decorative/pure formatting → `alt=""` or CSS background → time-based media gets captions/transcripts per level → **1.3.1** expose headings, lists, table headers, label associations programmatically → **1.3.3** never “click the green button” without text/shape/position redundant cue → **1.3.4** support both orientations unless essential → **1.3.5** `autocomplete` on personal data fields.
**Invariant:** informative image without alt, or instruction relying on color alone, fails Perceivable review.
**Probe:** axe images; manual chart alt review; grep “red/green/left/right” in instructions.

## Visual presentation seam
**Flow:** **1.4.3** text contrast ≥ **4.5:1** (≥ **3:1** large text) → **1.4.4** **200%** resize without clipping essential content → **1.4.10** **320px** reflow without horizontal scroll for vertical prose → **1.4.11** UI icons/focus rings/input borders ≥ **3:1** → **1.4.12** tolerate user text-spacing overrides → **1.4.13** hover/focus overlays dismissible, hoverable, persistent.
**Invariant:** body text below 4.5:1 or broken layout at 200% zoom fails AA Perceivable.
**Probe:** contrast checker on text + controls; browser zoom 200%; 320px emulation; text-spacing bookmarklet.

## Verdict
Text alternatives, programmatic structure, contrast, reflow, and non-color cues for WCAG 2.1 AA Perceivable. Learning note: `wcag-accessibility-learning-note.md`.
