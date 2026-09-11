<!-- capsule-v2 -->
# Diceware generator with replayable seed — how are passphrases assembled so formatting is configurable but entropy source fixed?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What is the word→capitalize→join→salt pipeline, and where does each random draw occur?

## Generation pipeline
**Path/Symbol:** `core/rust/src/password_generator/diceware.rs:15-31` (`generate`), :45-74 (`capitalize_word`), :77-96 (`add_salt`); enums in `mod.rs:36-83`; clamps `mod.rs:182-193`.
**Signature:** `pub fn generate<R: RngCore + ?Sized>(settings: &PasswordSettings, rng: &mut R) -> String` — generic over RNG so tests inject seeded instances.
**Data Shape:** Settings (PascalCase JSON persisted by apps): word_count, language (unknown codes FALL BACK to English — "the TypeScript model and apps never need updating to add a language"), capitalization {None,TitleCase,Uppercase,Lowercase,Random}, separator {None,Dash,Space,Underscore,Dot}, salt {None,Prefix,Sprinkle,Suffix}.

### Decisive source
```rust
let chosen: Vec<String> = (0..settings.word_count)
    .map(|_| {
        let word = words[unbiased_index(rng, words.len())];
        capitalize_word(word, settings.capitalization, rng)
    })
    .collect();
...
Salt::Sprinkle => {
    let mut chars: Vec<char> = passphrase.chars().collect();
    let index = unbiased_index(rng, chars.len() + 1);   // +1 allows appending at END
    chars.insert(index, salt_char);
```

**Flow:** per word: uniform index → capitalization transform (TitleCase uppercases first char + lowercases REST; Random flips each alphabetic char with its own coin flip) → join by separator or concat for None → optional single random alphanumeric salt char prepended/inserted/appended. Length clamps applied BEFORE generation (`length.clamp(1, MAX_PASSWORD_LENGTH)`), never after.
**Invariants:** (1) Every randomness flows through `unbiased_index` (4 sites) — no `%` selection anywhere. (2) Sprinkle's insertion range is `len+1`, i.e., a salt char may land AFTER the last character; off-by-one here biases positions. (3) Random capitalization consumes one draw PER CHARACTER, so the same seed yields identical output only if the option set is identical. (4) Salt is exactly ONE character from [a-zA-Z0-9] regardless of option.
**Probe:** `grep -c 'unbiased_index(rng' core/rust/src/password_generator/diceware.rs` → `4`; `grep -c 'chars.len() + 1' core/rust/src/password_generator/diceware.rs` → `1`; `grep -c 'fall back to' core/rust/src/password_generator/mod.rs` → `1`.

## Direct tests
**Path/Symbol:** `core/rust/src/password_generator/tests.rs` (seeded-RNG determinism suite upstream).
**Probe:** run upstream cargo test where toolchain exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "generate_password", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the draw-per-word + per-char-capitalization + single-salt-char pipeline with clamped settings; adapt wordlists/enums; omit Rust generics. In-file tests exist but were not executed here.
