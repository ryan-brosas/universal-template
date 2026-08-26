<!-- capsule-v2 -->
# <Seam> — <one porting question>

**Source:** <Repository> <license> `<branch>@<commit>`; Codebase Memory `<project>`. **Question:** <one precise question a porter must answer>.

## <Connected graph-selected seam>
**Path/Symbol:** `<path>:<symbol>` (<line range>).
**Signature:** `<callable signature>`.
**Data Shape:** <inputs, defaults, ownership, output/failure shape>.

### Decisive source
```<language>
<minimal source excerpt that prevents the likely wrong port>
```

**Flow:** <ordered behavioral transition>.
**Invariant:** <must-not-break property>.
**Probe:** `<direct-test-path>` (<observable behavior it pins>).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "<project>", query: "<symbol or relationship>", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt <portable behavior>; adapt <host-specific detail>; omit <non-portable source behavior>. <State any direct-test/index coverage caveat.>
