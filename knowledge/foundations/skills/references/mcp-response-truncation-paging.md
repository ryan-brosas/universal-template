<!-- capsule-v2 -->
# MCP response truncation & paging — how does an LLM-facing tool bound oversized responses while keeping the agent able to continue?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96af16`; Codebase Memory `skills`. **Question:** What is the truncation protocol for tool responses so the calling agent neither drowns nor dead-ends?

## CHARACTER_LIMIT gate + truncate-to-half + continuation message
**Path/Symbol:** `skills/mcp-builder/reference/node_mcp_server.md`:"Character Limits and Truncation" (:382–405); error taxonomy :408–434.
**Signature:** `export const CHARACTER_LIMIT = 25000;` — module-level constant; per-tool check `if (result.length > CHARACTER_LIMIT)`.
**Data Shape:** response envelope gains `truncated: true` and `truncation_message` describing before→after item counts plus the exact continuation affordance (`Use 'offset' parameter or add filters to see more results.`).

### Decisive source
```typescript
if (result.length > CHARACTER_LIMIT) {
    const truncatedData = data.slice(0, Math.max(1, data.length / 2));
    response.data = truncatedData;
    response.truncated = true;
    response.truncation_message =
      `Response truncated from ${data.length} to ${truncatedData.length} items. ` +
      `Use 'offset' parameter or add filters to see more results.`;
}
```
**Flow:** generate full result → serialize length check against module-level limit → on overflow cut data to HALF (never to exactly the limit), flag + explain → agent reads truncation_message and pages via offset/filters; hard failures route through a separate status-keyed error ladder (404/403/429 → actionable sentence each).
**Invariant:** Truncation must be *declared and actionable* — a silent cut or a generic "truncated" without a next step breaks agent loops; the message must name the parameter that continues the work. The limit lives at module level so every tool shares one budget constant.
**Invariant (asymmetry):** This contract exists ONLY in the Node guide — `search_code project=skills file_pattern=python_mcp_server.md pattern="CHARACTER_LIMIT|truncated"` returns **0 matches** (verified live 2026-08-26). A porter reading only the Python reference will ship unbounded responses.

**Probe:** repo-root deterministic probes: `grep -n 'CHARACTER_LIMIT = 25000' skills/mcp-builder/reference/node_mcp_server.md` = line 388; `grep -c 'CHARACTER_LIMIT' skills/mcp-builder/reference/python_mcp_server.md` = 0; `grep -n "data.length / 2" skills/mcp-builder/reference/node_mcp_server.md` = line 395.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "CHARACTER_LIMIT", file_pattern: "node_mcp_server.md", regex: false });
```
Live result 2026-08-26: single enriched hit group `node_mcp_server Module 1-970`, raw matches at lines 388/394 (+ truncat* family 395–401, 959).

## Verdict
Adopt the declared-truncation protocol (limit constant → half-cut → truncated flag → continuation message naming offset/filters) for any LLM-facing search/list tool; adopt the per-status actionable error strings alongside it. Adapt the 25k number and envelope field names to your host. Omit nothing — this is pure interface guidance. Caveat: guidance prose, not enforced code (no upstream tests exist in this repo); treat as design contract, verified by direct read at pin main@3b3fad96af16.
