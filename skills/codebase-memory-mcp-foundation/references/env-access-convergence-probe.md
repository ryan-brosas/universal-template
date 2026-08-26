<!-- capsule-v2 -->
# Env-access parity probe — how does a convergence suite document a KNOWN pipeline gap without lying green?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you write a test for a bug you haven't fixed yet so it cannot be mistaken for a pass?

## Named known-gap assertion with class taxonomy
**Path/Symbol:** `tests/test_convergence_probe.c:cp_configures_go_getenv` (355–380) + `[KNOWN class 14]` taxonomy.
**Signature:** fixture-driven: index `os.Getenv("CBM_PARITY_TOKEN")` through the full pipeline, assert `CONFIGURES >= 1`.
**Data Shape:** Documents that extract_env_accesses captures env reads into `result->env_accesses`, but NO src/pipeline pass consumes them to emit CONFIGURES — stdlib accessors never resolve to in-graph nodes, and configlink needs a ConfigVariable target.

### Decisive source
```c
/* REAL BUG: internal/cbm/extract_env_accesses.c extracts os.Getenv into
 * result->env_accesses, but NO pipeline pass under src/pipeline ever consumes
 * env_accesses to emit CONFIGURES. ... Stdlib env-accessor calls therefore
 * produce 0 CONFIGURES. [KNOWN class 14] */
ASSERT_TRUE(cfg >= 1);
```

**Flow:** fixture indexes an env accessor call → probe asserts the DESIRED edge exists → while the gap is open this documents the expectation (and fails loudly if someone "fixes" extraction away); when fixed, it converts to a plain regression pin.
**Invariant:** Known-gap tests must NAME the defect class and cite both producing and consuming modules; they must assert the desired behavior, not codify the broken one.
**Probe:** `tests/test_convergence_probe.c:cp_configures_go_getenv` plus its Python/C#/Rust twins (381–498); parallel-parity twin at tests/test_pipeline.c:1616.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "env_accesses", limit: 5 });
```

## Verdict
Adopt named-class convergence probes for acknowledged gaps; adapt to your taxonomy; never let such probes pass vacuously — assert the target behavior.
