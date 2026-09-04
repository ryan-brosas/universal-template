<!-- capsule-v2 -->
# DOM sanitizer level lattice — how do you mask/obscure/hide recorded DOM content with parent-inherited, attribute-driven, and privacy-mode levels that can also be LOWERED at runtime?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What is the sanitization precedence order (parent vs attributes vs domSanitizer vs privateMode) and why does the level store need both escalate-only and recompute paths?

## Sanitizer computeLevel / handleNode / setLevel / sanitize
**Path/Symbol:** `tracker/tracker/src/main/app/sanitizer.ts:computeLevel` (:69-107), `handleNode` (:124-130), `setLevel` (:114-122), `sanitize` (:132-149), `SanitizeLevel` enum (:5-9), `stringWiper` (:41-44).
**Signature:** `computeLevel(node: Node, parentLevel: SanitizeLevel): SanitizeLevel`; `handleNode(id, parentID, node)`; `sanitize(id: number, data: string): string`.
**Data Shape:** `levels: Map<nodeId, SanitizeLevel>` where Plain(0) is NEVER stored (absent = Plain); Obscured(1) wipes text to `*`s; Hidden(2) suppresses the node entirely. Attribute vocabulary: `data-openreplay-masked|obscured` → Obscured; `data-openreplay-htmlmasked|hidden` → Hidden; `data-openreplay-unmask` opts OUT of privateMode.

### Decisive source
```ts
// Pure recomputation of a node's level from the live DOM + parent level.
computeLevel(node: Node, parentLevel: SanitizeLevel): SanitizeLevel {
    if (this.options.privateMode) {
      if (isElementNode(node) && !hasOpenreplayAttribute(node, 'unmask')) return SanitizeLevel.Obscured
      ...
    }
    let level = SanitizeLevel.Plain
    if (parentLevel >= SanitizeLevel.Obscured || (isElementNode(node) &&
        (hasOpenreplayAttribute(node,'masked') || hasOpenreplayAttribute(node,'obscured')))) level = SanitizeLevel.Obscured
    if (parentLevel === SanitizeLevel.Hidden || (isElementNode(node) &&
        (hasOpenreplayAttribute(node,'htmlmasked') || hasOpenreplayAttribute(node,'hidden')))) level = SanitizeLevel.Hidden
    if (this.options.domSanitizer !== undefined && isElementNode(node)) {
      const l = this.options.domSanitizer(node)
      if (l === SanitizeLevel.Obscured && level < SanitizeLevel.Obscured) level = SanitizeLevel.Obscured
      if (l === SanitizeLevel.Hidden) level = SanitizeLevel.Hidden     // custom HIDDEN can override attr-Obscured
    }
```

**Flow:** on node insertion `handleNode` computes from live DOM+parent and commits ESCALATE-ONLY (`if (level > this.getLevel(id))`) — a mid-session re-parent can't silently unmask what an earlier ancestor hid → `resanitize()` (public API) recomputes and calls setLevel in BOTH directions so toggling attributes at runtime genuinely demotes levels → text capture routes through `sanitize()`: Obscured+ wipes every non-whitespace char via stringWiper; Plain applies optional digit→0 and email masking.
**Invariant:** Two write paths exist BY DESIGN: incremental handleNode must never lower (it only sees one subtree; a lowered value could be stale), while resanitize/setLevel may raise AND lower (full recomputation against live DOM is authoritative). The map-not-Sets representation exists exactly so levels are deletable (Plain deletes the entry — keeps the map small and makes "un-obscure" possible). Custom domSanitizer Hidden overrides attribute-level Obscured because the callback is the embedder's last word.
**Probe:** `grep -c 'hasOpenreplayAttribute' tracker/tracker/src/main/app/sanitizer.ts` from repo root → **5** (verified live); direct tests: `npx jest src/tests/sanitizer.unit.test.ts` in `tracker/tracker` → 17/17 green incl. parent-hidden inheritance and domSanitizer override cases.
**Retrieve:** search_graph project openreplay query "Sanitizer computeLevel SanitizeLevel privateMode" → rank-1 Method `Sanitizer.computeLevel :69-107`, Enum `SanitizeLevel :5-9` line-exact.

## Verdict
Adopt the four-source precedence lattice (privateMode > parent > attrs > defaults) with split escalate-only/recompute write paths as pure privacy behavior; adapt the attribute names and Map keying to your DOM id scheme; omit email/digit regex specifics (locale-dependent product choice).
