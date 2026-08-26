<!-- capsule-v2 -->
# MCP Builder Server-Quality Contract — what makes an MCP server's tools actually usable by LLMs?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96`; Codebase Memory `skills`. **Question:** Beyond protocol correctness, which design rules and evaluation discipline determine MCP server quality?

## Design doctrine + connection harness + eval gate
**Path/Symbol:** `skills/mcp-builder/SKILL.md` (Phases 1-4); connection helpers `scripts/connections.py` (`MCPConnection` 13-70, `MCPConnectionStdio` 73-85, `MCPConnectionSSE` 88-97, `MCPConnectionHTTP` 100-109); deep guides `reference/mcp_best_practices.md`, `reference/node_mcp_server.md`, `reference/python_mcp_server.md`, `reference/evaluation.md`.
**Signature:** Tool registration with Zod (TS) / Pydantic (Python) input schemas; `outputSchema` + `structuredContent`; annotations `{readOnlyHint, destructiveHint, idempotentHint, openWorldHint}`; XML eval format `<evaluation><qa_pair><question>…<answer>…`.
**Data Shape:** Eval = 10 questions, each independent, read-only, multi-tool-call complex, realistic, string-verifiable, stable over time.

### Decisive source
```markdown
**API Coverage vs. Workflow Tools:** ... When uncertain, prioritize
comprehensive API coverage.
...
**Actionable Error Messages:** Error messages should guide agents toward
solutions with specific suggestions and next steps.
...
#### 4.3 Evaluation Requirements
Ensure each question is:
- **Independent**: Not dependent on other questions
- **Read-only**: Only non-destructive operations required
- **Complex**: Requiring multiple tool calls and deep exploration
- **Realistic**: Based on real use cases humans would care about
- **Verifiable**: Single, clear answer that can be verified by string
    comparison
```

**Flow:** Research (protocol docs via sitemap+`.md` fetch, framework guides loaded on demand) → implement shared infra (authed API client, error helpers, JSON/Markdown response formatting, pagination) → per tool: constrained input schema w/ examples in field descriptions, structured output where possible, async I/O, actionable errors, honest hint annotations → review for DRY/typed/described → build + test via MCP Inspector (`npx @modelcontextprotocol/inspector`) → author the 10-question eval by exploring with READ-ONLY ops first, solving each question yourself before shipping.
**Invariant:** Quality is measured at the LLM-usable level, not endpoint parity: naming uses consistent action-oriented prefixes (`github_create_issue`); every question must be self-solvable and string-checkable or the benchmark is noise. Transport choice: Streamable HTTP stateless-JSON for remote, stdio for local.
**Probe:** `python -m py_compile your_server.py` then MCP Inspector session exercises tools live; the bundled `connections.py` classes demonstrate the three transports' connect/exchange/cleanup shapes as executable reference.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "MCPConnection Stdio HTTP SSE", limit: 10 });
```

## Verdict
Adopt: coverage-first tool design, annotation honesty, actionable-error rule, and the 6-property eval-question bar — all protocol-level and host-independent. Adapt language guides to your SDK version (protocol itself already covered by mcp-spec-and-servers-foundation). Omit Anthropic's doc-fetch mechanics. Caveat: reference/*.md guides are external-fetch dependent; scripts are the executable surface.
