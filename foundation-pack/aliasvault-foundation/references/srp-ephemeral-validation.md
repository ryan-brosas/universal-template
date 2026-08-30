<!-- capsule-v2 -->
# SRP malicious-ephemeral validation — why must B≡0 (mod N) and A≡0 (mod N) be rejected before session math?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** Which peer-supplied ephemeral values can crash or weaken the handshake, and where exactly is each check placed?

## Client-side B rejection
**Path/Symbol:** `core/rust/src/srp/mod.rs:221-226` (`srp_derive_session`), server-side A rejection :330-335 (`srp_derive_session_server`).
**Signature:** `if &b_pub % &G_2048.n == BigUint::default() { return Err(SrpError::InvalidParameter(...)) }`.
**Data Shape:** Inputs are hex strings parsed to `BigUint`; group is RFC 5054 2048-bit `srp::groups::G_2048`. Failure mode is a typed `SrpError::InvalidParameter` — NOT an authentication failure (`Ok(None)` is reserved for bad M1).

### Decisive source
```rust
// Safeguard against malicious B (B mod N must not be 0)
if &b_pub % &G_2048.n == BigUint::default() {
    return Err(SrpError::InvalidParameter(
        "server public ephemeral is invalid".to_string(),
    ));
}
```

**Flow:** client receives B from login-initiate → modulo check runs BEFORE any session derivation → same guard on the server for client A before computing premaster secret → both sides then proceed with crate primitives.
**Invariants:** (1) The check is `value mod N == 0`, so it rejects BOTH `B = 0` and `B = N` (and N·k). (2) It must run before `compute_premaster_secret`, which would otherwise panic/misbehave on degenerate inputs. (3) Error type distinguishes protocol violations (`Err`) from wrong-password outcomes (`Ok(None)`).
**Probe:** `grep -c 'b_pub % &G_2048.n' core/rust/src/srp/mod.rs` → `1`; `grep -c 'a_pub % &G_2048.n' core/rust/src/srp/mod.rs` → `1`.

## Direct tests
**Path/Symbol:** `core/rust/src/srp/mod.rs:710-750` (`test_malicious_server_public_rejected`, `test_malicious_client_public_rejected`).
**Data Shape:** Both tests iterate `["00", n_hex]` — zero and the full modulus — asserting `matches!(result, Err(SrpError::InvalidParameter(_)))`.
**Probe:** `grep -c 'for bad_b in \["00", n_hex.as_str()\]' core/rust/src/srp/mod.rs` → `1`; `grep -c 'fn test_malicious_client_public_rejected' core/rust/src/srp/mod.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "SrpError InvalidParameter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pre-session `mod N == 0` rejection with the Err-vs-None error taxonomy; adapt error type to host language; omit the specific hex transport. Source wins over graph: guards confirmed at pin `95903e92` in both derive functions; direct tests exist in-file.
