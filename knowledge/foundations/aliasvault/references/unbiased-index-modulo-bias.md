<!-- capsule-v2 -->
# Unbiased index + deterministic seed RNG — how does password generation stay uniform AND replayable?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** How is modulo bias eliminated for word/char selection, and how can the UI regenerate the "same" password with different formatting?

## Rejection-sampled indexing
**Path/Symbol:** `core/rust/src/rng.rs:10-49` (`make_rng`, `unbiased_index`), consumption in `core/rust/src/password_generator/diceware.rs:15-31` and `basic.rs`.
**Signature:** `pub(crate) fn unbiased_index<R: RngCore + ?Sized>(rng: &mut R, max: usize) -> usize`; `pub(crate) fn make_rng(seed: Option<&str>) -> StdRng`.
**Data Shape:** Optional 64-hex-char seed ⇒ seeded `StdRng` (deterministic); absent/malformed ⇒ OS CSPRNG seed. All selection goes through `unbiased_index`, never `%`.

### Decisive source
```rust
/// Handles modulo bias by rejecting values above the largest multiple of `max` that fits in a u64.
let max = max as u64;
let rem = max.wrapping_neg() % max;   // 2^64 mod max, via wrapping negation
loop {
    let value = rng.next_u64();
    if rem == 0 || value < rem.wrapping_neg() {   // accept zone = largest multiple of max
        return (value % max) as usize;
    }
}
```

**Flow:** settings carry optional `seed` → same seed replays the SAME underlying words so the UI can flip separator/capitalization/salt options for comparison ("re-apply formatting options ... to the *same* underlying words", password_generator/mod.rs:135-140 doc) → diceware draws one index per word, one per capitalization coin-flip (Random mode), one for the salt char — 4 `unbiased_index(rng, ...)` call sites.
**Invariants:** (1) Powers-of-two maxes divide evenly (`rem == 0`) and must accept immediately — the loop would otherwise hang on `max > 2^63` edge cases (test comment "must accept immediately, never hang"). (2) Acceptance threshold is computed as `(!max+1) % max` = `2^64 mod max`; rejecting `value >= threshold` makes `(value % max)` perfectly uniform. (3) `max <= 1` short-circuits to 0 before any draw. (4) Malformed seeds silently degrade to CSPRNG rather than erroring.
**Probe:** `grep -c 'wrapping_neg() % max' core/rust/src/rng.rs` → `1`; `grep -c 'unbiased_index(rng' core/rust/src/password_generator/diceware.rs` → `4`; `grep -c 'never hang' core/rust/src/rng.rs` → `1`.

## Direct tests
**Path/Symbol:** `core/rust/src/rng.rs:51-89` (`unbiased_index_stays_in_range` over maxes {2,3,10,36,100}×1000 draws, `unbiased_index_handles_edge_maxes` incl. `usize::MAX`).
**Probe:** run upstream cargo test where toolchain exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "unbiased_index", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rejection-sampled indexing + opt-in deterministic seeding for generator UX; adapt RNG crate; omit StdRng specifics. In-file tests exist but were not executed here.
