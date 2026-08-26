<!-- capsule-v2 -->
# Issuer-partitioned JWT realm — how do you make one signing key serve ten token lifetimes without them being interchangeable?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How are access, refresh, invite, admin and file-download tokens prevented from replaying across endpoints while sharing one RSA keypair?

## Per-purpose issuers + one generic decoder
**Path/Symbol:** `src/auth.rs:112` (`decode_jwt`), `src/auth.rs:50-77` (the 11 `JWT_*_ISSUER` LazyLocks), typed decoders `src/auth.rs:130-176` (`decode_login`, `decode_invite`, `decode_admin`, `decode_send`, `decode_file_download`, `decode_2fa_remember`, …).
**Signature:** `decode_jwt<T: DeserializeOwned>(token: &str, issuer: String) -> Result<T, Error>`; every purpose-specific decoder is a one-liner binding the issuer.
**Data Shape:** issuer string = `{domain_origin}|{purpose}` e.g. `https://vw.example|login`, `…|invite`, `…|2faremember`. Algorithm pinned RS256 (`JWT_ALGORITHM`, auth.rs:41). Validation: leeway 30s, `validate_exp`+`validate_nbf` true, `set_issuer(&[issuer])`. Token whitespace is stripped before decode (`token.replace(char::is_whitespace, "")`).

### Decisive source
```rust
pub fn decode_jwt<T: DeserializeOwned>(token: &str, issuer: String) -> Result<T, Error> {
    let mut validation = jsonwebtoken::Validation::new(JWT_ALGORITHM);
    validation.leeway = 30; // 30 seconds
    validation.validate_exp = true;
    validation.validate_nbf = true;
    validation.set_issuer(&[issuer]);
    let token = token.replace(char::is_whitespace, "");
    match jsonwebtoken::decode(&token, PUBLIC_RSA_KEY.wait(), &validation) {
        Ok(d) => Ok(d.claims),
        Err(err) => match *err.kind() { /* "Token is invalid"/"Issuer is invalid"/"Token has expired" mapping */ }
    }
}
```

**Flow:** encode always with `JWT_HEADER` (RS256) via `encode_jwt` (auth.rs:105) which PANICS on failure — a misconfigured key aborts startup-time flows instead of emitting bad tokens. Decode maps three error kinds to clean messages; everything else becomes "Error decoding JWT: …".
**Invariant:** a token minted for issuer X can never authenticate an endpoint decoding with issuer Y — the claim type AND issuer must both match. Adding a new token purpose = new issuer const + new claims struct + new decode fn, never reuse of an existing pair.
**Probe:** `grep -c 'ISSUER: LazyLock' src/auth.rs` → `11`.

## Key bootstrap is lazy, persisted and single-init
**Path/Symbol:** `src/auth.rs:82-103` (`initialize_keys`), auth.rs:48-49 (`PRIVATE_RSA_KEY`/`PUBLIC_RSA_KEY` OnceLocks).
**Data Shape:** RSA-2048 PEM read through the OpenDAL storage operator for `PathType::RsaKey`; generated on first boot if absent (`Rsa::generate(2048)` then written back); `OnceLock::set` twice errors ("must only be initialized once"). Decoding key derived from the PUBLIC pem, not the private.
**Flow:** startup → read (NotFound tolerated) → generate-or-load → set both OnceLocks → all later encode/decode use `.wait()`.
**Invariant:** the private key never leaves storage unencrypted but IS the only trust root — rotating it invalidates every outstanding token of every realm at once.
**Probe:** `grep -n 'Rsa::generate(2048)' src/auth.rs | wc -l` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "decode_jwt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt issuer-suffixed realms over one shared secret as the core porting pattern; adapt the domain_origin source to your config plane; omit Rocket's `OnceLock/LazyLock` specifics in favor of your runtime's equivalent. Coverage caveat: none of the cited paths carry recorded index issues; direct tests absent upstream — probes are deterministic source pins.
