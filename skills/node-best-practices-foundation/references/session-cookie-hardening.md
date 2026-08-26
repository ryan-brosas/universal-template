<!-- capsule-v2 -->
# Session middleware default-hardening — which three express-session defaults leak, and what replaces each?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Why is stock session middleware an attacker tell, and which knobs close it?

## Rename, secure-flag, httponly, expiry — four settings off default
**Path/Symbol:** `sections/security/sessions.md` (explainer :8-12, config example :19-30).
**Signature:** `app.use(session({ secret, name, cookie: { httpOnly, secure, maxAge } }))`.
**Data Shape:** the doc's canonical hardened shape: unique `name` replacing default `connect.sid`; `cookie.secure: true` (HTTPS-only transport); `cookie.httpOnly: true` (blocks client-side JS reads); explicit `maxAge` in ms (example `60000*60*24`).

### Decisive source
```javascript
// sessions.md :21-29
app.use(session({
  secret: 'youruniquesecret', // signs the session ID stored in the cookie
  name: 'youruniquename',     // remove the default connect.sid
  cookie: {
    httpOnly: true,           // minimize XSS risk of client reading cookie
    secure: true,             // only send cookie over https
    maxAge: 60000*60*24       // expiry in ms
  }
}));
```

**Flow:** attacker probes `connect.sid` presence → learns Express + express-session → targets module-specific CVEs; renaming removes the fingerprint. `secure:true` kills MITM cookie capture; `httpOnly` kills XSS exfiltration; bounded `maxAge` caps replay windows.
**Invariant:** the most common omission is the session NAME (:10) — teams tighten cookies but ship the default name, keeping the framework fingerprint intact. Defaults exist for developer convenience, not safety: "Many popular session middlewares do not apply best practice/secure cookie settings out of the box."
**Probe:** no runner upstream. Deterministic probe: `grep -c 'connect.sid' sections/security/sessions.md` >= 1 && `grep -c 'secure: true' sections/security/sessions.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "secure: true", "limit": 10}'
# resolves `sections/security/sessions.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt all four settings as a launch checklist item. Adapt names/secrets per environment; pair with `anti-csrf-double-submit` thinking (see nexus-public foundation) for unsafe-method protection. Omit nothing — each knob maps to a named attack class.
