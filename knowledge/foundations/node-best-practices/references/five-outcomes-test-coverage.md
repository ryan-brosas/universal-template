<!-- capsule-v2 -->
# Five-outcomes test coverage — what five observable outputs must a flow test assert, and why is "the response" never enough?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What is the complete set of side-effects a test must verify beyond the HTTP response?

## Response / state / external call / queue / observability
**Path/Symbol:** `sections/testingandquality/test-five-outcomes.md` (explainer :3, five categories :5-15).
**Signature:** a checklist discipline, not an API. For every triggered action, assert across up to five outcome classes:
1. **Response** — data correctness, schema, HTTP status.
2. **New state** — data actually persisted (the "product was failed to persist regardless of positive response" trap, README 4.13 Otherwise).
3. **External calls** — outbound HTTP/transport to collaborators (SMS, email, card charge).
4. **Message queues** — a message placed in an MQ consumed by other components.
5. **Observability** — errors handled correctly, proper logging/metrics for the ops user.

### Decisive source
```text
// test-five-outcomes.md :3 — the framing
Note that we don't care about how things work. Our focus is on outcomes,
things that are noticeable from the outside and might affect the user.
```

**Flow:** design tests outcome-first: name each flow's possible observable outputs, then assert each. The doc's "backend testing checklist" image is the concrete enumeration aid (README 4.13 links the PDF checklist).
**Invariant:** a test that asserts only the response is incomplete even when green — it cannot detect a write that silently failed, an external call that never fired, or a missing queue message. Each outcome class carries distinct techniques (data handling, integration mocking, MQ tooling, observability).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'Observability\|Message queues\|External calls' sections/testingandquality/test-five-outcomes.md` ≥ 3.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "Message queues", "limit": 10}'
# resolves `sections/testingandquality/test-five-outcomes.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the five-outcome checklist as the test-planning frame for any service. Adapt the outcome taxonomy to the domain (some flows lack queues/observability). Omit the specific checklist PDF link — external asset.
