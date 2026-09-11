<!-- capsule-v2 -->
# Memory-graph CLI wrapper — how do you give an LLM a safe thin CLI over a raw MCP graph CLI?

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a 23-line wrapper make a raw MCP CLI (`codebase-memory-mcp`) safe and ergonomic for an LLM to call — avoiding shell-quoting of JSON arguments entirely?

## Thin args-file wrapper over codebase-memory-mcp
**Path/Symbol:** `scripts/mgraph.mjs` (whole file, 23 lines); helpers `run` (:13), `argv` (:14), `jfile` (:15), `out` (:16); dispatch chain :17–22. Graph-resident as `dsh-template.scripts.mgraph.{run,argv,jfile,out}`.
**Signature:** `node scripts/mgraph.mjs arch|hot|search|cover|daemon …`; internal `run(args)` → `spawnSync('codebase-memory-mcp', args, { encoding:'utf8', maxBuffer:64*1024*1024 })`.
**Data Shape:** subcommands map onto five MCP calls — `arch --project X [--aspects a,b] [--path P]` → `get_architecture`, `hot --project X` → `get_architecture` with `aspects:['hotspots']`, `search --project X <query>` → `search_graph`, `cover --project X <path>` → `check_index_coverage`, `daemon start|status|stop` → passthrough. Every structured call serializes its options with `JSON.stringify` to `/tmp/mgraph-<name>.json` (`jfile`) and passes `--args-file <path>`.

### Decisive source
```js
const CB = 'codebase-memory-mcp';
function run(args){ const r = spawnSync(CB, args, { encoding:'utf8', maxBuffer:64*1024*1024 }); return r; }
function jfile(name,obj){ const p='/tmp/mgraph-' + name + '.json'; fs.writeFileSync(p, JSON.stringify(obj)); return p; }
// search: the LAST positional arg is the query — never shell-quoted, never inline JSON
else if(cmd==='search'){ const f=jfile('search',{project:argv('--project',''),query:process.argv[process.argv.length-1]}); out(run(['cli','--json','search_graph','--args-file', f])); }
```

**Flow:** (1) parse only flag-style args by position (`argv` scans `process.argv.indexOf(k)+1`); (2) build a plain options object; (3) write it to a fixed `/tmp/mgraph-<cmd>.json` file; (4) spawn `codebase-memory-mcp cli --json <tool> --args-file <file>`; (5) forward stdout+stderr verbatim (`out`); unknown verbs print usage, no crash.
**Invariant:** complex arguments NEVER travel through the shell — they go through the args-file, so quoting/history-expansion mangling of inline JSON is structurally impossible; the wrapper stays dependency-free (node builtins only) so the template keeps its install-free invariant; `maxBuffer` is raised to 64 MB because architecture dumps exceed the default 1 MB.

**Probe:** executed live at HEAD `ffb36822`: `node scripts/mgraph.mjs search --project dsh-template "resolveCommands apply"` returned the two plugin functions (`resolveCommands` 56–64, `apply` 66–93); `node scripts/mgraph.mjs cover --project dsh-template scripts/mgraph.mjs` returned `no_recorded_issue`/`metadata_match`. No test runner exists in-repo (coverage caveat: probes are the executable evidence).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "mgraph wrapper codebase-memory cli", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the args-file pattern (write JSON options to a temp file, pass `--args-file`) whenever a target CLI accepts structured args — it kills an entire class of LLM shell-quoting bugs; adopt the five-verb reduction too (LLMs need few verbs, not full CLI surface). Adapt the wrapped binary, verb table, and `/tmp` naming to the host. Omit nothing else — the whole value is that there is nothing else (23 lines).
