<!-- capsule-v2 -->
# Reachability complexity governor — when does a linter downgrade its CFG analysis from precise to approximate?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you bound worst-case rule cost on pathological functions while keeping precision for normal code?

## exceeds_complexity_threshold + dual analyzers
**Path/Symbol:** `crates/biome_js_analyze/src/lint/correctness/no_unreachable.rs:NoUnreachable::run` (:63-78), `COMPLEXITY_THRESHOLD` (:205), `exceeds_complexity_threshold` (:215-261), `analyze_simple` (:263-367), `analyze_fine` (:369+).
**Signature:** `const COMPLEXITY_THRESHOLD: u32 = 20;`; `fn exceeds_complexity_threshold(cfg: &JsControlFlowGraph) -> bool`; dispatch: `if exceeds_complexity_threshold(cfg) { analyze_simple(cfg, &mut signals) } else { analyze_fine(cfg, &mut signals) }`.
**Data Shape:** score inputs = block count, jump-edge count (each Jump +1; conditional also +1), side-effecting statements × live exception/cleanup handler-list lengths (via `NonZeroU32::new(len).take()` so each statement counts handlers at most once).

### Decisive source
```rust
// no_unreachable.rs:215-240 — cyclomatic-approximating score computed from
// the SAME graph it governs; handler lists multiply the cost of every
// potentially-throwing statement, which is where real blow-up lives
for block in &cfg.blocks {
    let mut exception_handlers = NonZeroU32::new(block.exception_handlers.len() as u32);
    let mut cleanup_handlers = NonZeroU32::new(block.cleanup_handlers.len() as u32);
    for inst in &block.instructions {
        if has_side_effects(inst) && let Some(handlers) = exception_handlers.take() {
            edges += handlers.get();
            conditionals += 1;
        }
        match inst.kind {
            InstructionKind::Jump { conditional, .. } => {
                edges += 1;
                if conditional { conditionals += 1; }
            }
            …
```

**Flow:** run() scores the graph → under threshold: fine analysis (exact reachability with terminator attribution powering "because this statement will return/throw beforehand" detail labels :100-200) → over: simple analysis (cheaper walk, coarser diagnostics) → both emit `UnreachableRanges`.
**Invariant:** The threshold is a performance valve, not a semantic switch — both paths must be SOUND (never report reachable code as unreachable); only diagnostic detail degrades. Handler-count weighting is essential: exception edges are what make deep try nesting quadratic. A porter who scores only block/edge counts will time out on generated `try` soup.
**Probe:** `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/{HighComplexity.js,issue-3654.js}(+.snap)` pin the degraded path on real pathological inputs.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "exceeds_complexity_threshold", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the governor pattern (score → exact/approximate fork, soundness preserved) verbatim. Adapt the score weights to your IR's actual cost drivers. Omit the specific message-pluralization ladder (product copy).
