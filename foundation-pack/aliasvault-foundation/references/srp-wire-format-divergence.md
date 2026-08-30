<!-- capsule-v2 -->
# SRP wire-format divergence from the `srp` crate — which exact K/M1/M2 formulas keep Rust clients, the .NET API, and JS tests interoperable?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** When porting the SRP core to a new platform, where does the RustCrypto `srp` crate's output deviate from the wire format shared with `SecureRemotePassword` (.NET) and `secure-remote-password` (JS)?

## Wire-format-specific primitives section
**Path/Symbol:** `core/rust/src/srp/mod.rs:366-406` (`derive_session_key`, `compute_m1`, `compute_m2`), header comment :367-372.
**Signature:** `fn derive_session_key(s: &BigUint) -> Vec<u8>`; `fn compute_m1(a_pub: &[u8], b_pub: &[u8], salt: &[u8], identity: &str, key: &[u8]) -> Vec<u8>`; `fn compute_m2(a_pub: &[u8], m1: &[u8], key: &[u8]) -> Vec<u8>`.
**Data Shape:** All values cross FFI as UPPERCASE hex strings; group elements left-padded with zeros to `N_BYTES = 256` (:22) via `to_padded_bytes`; identity is lowercased at every entry point (`srp_derive_session` :215, `srp_derive_private_key` :149).

### Decisive source
```rust
// These deviate from the `srp` crate and must not be replaced with its versions:
// the SecureRemotePassword (.NET/JS) format hashes the padded premaster secret
// into K and uses the RFC 2945 M1, while the crate uses raw S and M1 = H(A|B|S).
/// Derive the session key K = H(PAD(S)) from the premaster secret.
fn derive_session_key(s: &BigUint) -> Vec<u8> {
    Sha256::digest(&to_padded_bytes(s)).to_vec()
}
/// Compute M1 = H(H(N) XOR H(g) | H(I) | s | A | B | K)
/// Note: H(g) uses g without padding, unlike k = H(N, PAD(g))
```

**Flow:** client `srp_derive_session` (:208-247): reject malicious B → recompute A_pub padded → `u = H(PAD(A)|PAD(B))` via crate's `compute_u` → `S = (B - k·g^x)^(a+u·x)` via crate → **K = SHA256(PAD(S))** locally → **M1 = SHA256(H(N)⊕H(g) | H(I) | s | PAD(A) | PAD(B) | K)** locally → server mirrors in `srp_derive_session_server` (:315-364) and returns M2 = H(A|M1|K); client verifies M2 constant-time (`ct_eq`, :274).
**Invariants:** (1) The three local functions are the ONLY deviation — u, k, and premaster S still come from the `srp` crate; swapping them for crate versions breaks every existing account. (2) H(g) inside M1 is UNPADDED while k = H(N, PAD(g)) is padded — an asymmetry a porter will "fix" and break. (3) Identity lowercasing happens before hashing everywhere (test `test_identity_lowercased` :627 proves mixed-case client + lowercase server interop). (4) Proof comparisons use `subtle::ConstantTimeEq`, never `==`.
**Probe:** `grep -c 'must not be replaced with its versions' core/rust/src/srp/mod.rs` → `1`.

## Full-flow direct test
**Path/Symbol:** `core/rust/src/srp/mod.rs:558-622` (`test_full_srp_flow`), fixed-vector pins :491-504 (`test_fixed_values`) and :508-526 (`test_session_fixed_values`).
**Invariant:** registration(salt→x→v) → login(A,B,M1,M2) round-trips entirely inside one file with deterministic expected hex for private key/verifier/session key/proof; a tampered M2 (first char flipped) must fail `srp_verify_session`.
**Probe:** `grep -c 'fn test_full_srp_flow' core/rust/src/srp/mod.rs` → `1`; `grep -n 'derive_session_key' core/rust/src/srp/mod.rs | wc -l` → `3` (def + 2 call sites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "srp_derive_session", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves `core.rust.src.srp.mod.srp_derive_session` plus wasm/uniffi twins line-exact.)

## Verdict
Adopt the exact K/M1/M2 formulas + 256-byte zero-padding + lowercase-identity normalization as one atomic contract; adapt hex-string vs byte transport per host FFI; omit the .NET/JS twin implementations. Caveat: cargo runner unavailable in inspo clone (deterministic probes substituted); upstream `#[cfg(test)]` suite is the authoritative runner.
