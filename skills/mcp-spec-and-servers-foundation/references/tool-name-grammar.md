<!-- capsule-v2 -->
# Tool name grammar — which characters/lengths may a tool name use, and how do namespaced names survive client routing?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6` (`docs/specification/2026-07-28/server/tools.mdx` §Tool Names :309–333 — CURRENT normative rule; origin `seps/986-specify-format-for-tool-names.md`, Final, now superseded). Codebase Memory `modelcontextprotocol`. **Question:** What is the portable tool-name alphabet and the compatibility duty when renaming tools?

## 1–128 chars; case-sensitive; `[A-Za-z0-9_.-]` (NO slash); no spaces or commas
**Path/Symbol:** `docs/specification/2026-07-28/server/tools.mdx` §Tool Names :309–333 (current rule); `seps/986-specify-format-for-tool-names.md` (origin SEP: 1–64 chars, allowed `/` — **superseded by the modern spec, which dropped `/` and raised the cap to 128**).

**Signature:** n/a — lexical rule, not an API.

**Data Shape (CURRENT, 2026-07-28):** allowed = ASCII letters, digits, `_`, `-`, `.`; length 1–128 inclusive; case-sensitive; unique within a server; no spaces/commas/special chars. Valid examples: `getUser`, `DATA_EXPORT_v2`, `admin.tools.list`. **`/` is NOT an allowed character in the current spec** (SEP-986's `user-profile/update` example no longer conforms).

### Decisive source
```md
# 2026-07-28/server/tools.mdx :309-333 (CURRENT — source wins over the older SEP)
- Tool names SHOULD be between 1 and 128 characters in length (inclusive).
- Tool names SHOULD be considered case-sensitive.
- The following SHOULD be the only allowed characters: uppercase and lowercase ASCII
  letters (A-Z, a-z), digits (0-9), underscore (_), hyphen (-), and dot (.)
- Tool names SHOULD NOT contain spaces, commas, or other special characters.
- Tool names SHOULD be unique within a server.
```
Uniqueness is scoped to a single server (tools.mdx :321–331): clients/proxies that aggregate tools from multiple servers MAY hit collisions (two servers each exposing `search`) and SHOULD implement a disambiguation strategy such as prefixing with a server identifier. The server `name` (from `serverInfo`) is NOT guaranteed unique and SHOULD NOT be relied on for disambiguation.

**Flow:** author picks a conforming name at registration → clients route on the raw string (case-sensitivity means `getUser` ≠ `getuser`) → dots enable hierarchical namespacing (`admin.tools.list`) without extra protocol machinery → renames ship aliases + deprecation warnings (SEP-986's alias-migration duty, still good practice).

**Invariants:**
1. **Case-sensitivity is normative**: lowercasing incoming tool-call names breaks conforming servers.
2. **`.` is a first-class name character**, not a separator imposed by any client — porters who split on it to "find the server" mis-parse legal names.
3. **`/` is NOT legal in the current spec** — a porter copying SEP-986's `user-profile/update` example (or an older capsule) into a modern server emits a non-conforming name. Use `.` or `_` for namespacing instead.
4. Spaces/commas/specials are excluded to avoid parsing ambiguity in flattened tool menus.

**Probe:** deterministic — grep every registered tool name in the servers repo against the current pattern (all everything-server + filesystem/memory/git/fetch/time catalogs use kebab/dot names, no slashes, all ≤128); no runtime test exists for the lexical rule itself (docs-only caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "registerTool name kebab case catalog", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the CURRENT alphabet/length/case rules — 1–128 chars, `[A-Za-z0-9_.-]`, no `/`, no spaces/commas — and the alias migration path for ANY new tool surface; adapt your own naming convention within it (kebab-case is common, not required); omit client-side assumptions that names never contain dots, and omit `/` from names entirely in modern servers. Corrects the earlier SEP-986-only reading (1–64 + `/`) against the current spec — the SEP is the origin, the 2026-07-28 tools page is the live rule. Fills the naming gap left open by `schema-registration.md`, which pins the Tool wire shape but not its lexical constraints.
