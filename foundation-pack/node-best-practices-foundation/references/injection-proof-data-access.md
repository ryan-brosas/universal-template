<!-- capsule-v2 -->
# Injection-proof data access — ORM/parameterization plus validation, with the NoSQL $where trap called out

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which code shapes open SQL and NoSQL injection, and what's the structural fix?

## Validate (joi/yup) + map via ORM/ODM; never interpolate or pass JS into queries
**Path/Symbol:** `sections/security/ormodmusage.md` (rule :5-6, library list :10-15, NoSQL example :19-32, SQL example :36-40).
**Signature:** ORM family — TypeORM / sequelize / mongoose / Knex / Objection.js / waterline — all guarantee parameterized queries + bindings.
**Data Shape:** vulnerable SQL: `WHERE id = '<userinput>'` string interpolation. Vulnerable NoSQL: `$where: (obj) => ... <userInput>` — a JS function evaluated IN the database.

### Decisive source
```javascript
// ormodmusage.md :21-29 — NoSQL injection that is ALSO a DoS
db.balances.find({
  active: true,
  $where: (obj) => obj.credits - obj.debits < userInput
});
// userInput = "(function(){var date = new Date(); do{curDate = new Date();}
// while(curDate-date<10000); return Math.max();})()"  -> denial of service
```

**Flow:** hand-built query strings let quote-escape payloads break out (`'evil'input'`, :39) → arbitrary WHERE semantics. NoSQL variants execute where the API parses input — sometimes app layer, sometimes DB (:52-54). The `$where` shape is doubly dangerous: JS injection inside the DB process spins an infinite loop = DoS, or exfiltration logic.
**Invariant:** parameterization alone is NOT the whole fix — the doc pairs it with schema validation FIRST (joi/yup) so structure+length are bounded before any query sees the value. ORMs give parameterized queries by default; raw-string escape hatches (`sequelize.literal`-style) reintroduce the hole and need review-gating.
**Probe:** no runner upstream. Deterministic probe: `grep -cF '$where' sections/security/ormodmusage.md` >= 1 && `grep -c 'TypeORM\|mongoose\|Knex' sections/security/ormodmusage.md` >= 3.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "parameterized", "limit": 10}'
# resolves `sections/security/ormodmusage.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt validate-then-parameterize as the standing data-access rule; ban `$where`/JS-in-query constructs outright. Adapt ORM choice per stack. Omit stored-procedure debates — the contract is about not concatenating or evaluating untrusted text.
