<!-- capsule-v2 -->
# Dependent-argument completion — how does a prompt argument's autocompleter read earlier arguments, and what do static file resources add?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/everything); Codebase Memory `servers`. **Question:** How is the two-stage department→name completer wired through `completable()`, and when does directory-scan registration degrade gracefully?

## context.arguments threading + missing-dir silent skip
**Path/Symbol:** `src/everything/prompts/completions.ts` (whole file, 64L: schema :15–42; registration :45–63); companion `src/everything/resources/files.ts` (:16–64 scan-register loop; :70–77 mime map; :83–89 safe reader).

**Signature:** `completable(zodSchema, (value: string, context?: { arguments?: Record<string,string> }) => string[])` — the SECOND positional arg of the SDK completer callback receives the request's argument context; the later argument reads `context?.arguments?.["department"]`. Prompt handler destructures validated args: `({ department, name }) => ({ messages: [...] })`.

### Decisive source
```ts
// src/everything/prompts/completions.ts:24-41
name: completable(
  z.string().describe("Choose a team member to lead the selected department."),
  (value, context) => {
    const department = context?.arguments?.["department"];   // ← EARLIER argument
    if (department === "Engineering") {
      return ["Alice", "Bob", "Charlie"].filter((n) => n.startsWith(value));
    } else if (department === "Sales") { /* ...David/Eve/Frank... */ }
    else if (department === "Marketing") { /* ...Grace/Henry/Iris... */ }
    else if (department === "Support")  { /* ...John/Kim/Lee... */ }
    return [];                                // unknown/absent department ⇒ NO suggestions
  }
),
```

```ts
// src/everything/resources/files.ts:22-27 + :83-89 — graceful degradation pair
let entries: string[] = [];
try { entries = readdirSync(docsDir); }
catch (e) { return; }                          // missing/unreadable docs dir ⇒ register NOTHING
// ...
function readFileSafe(path: string): string {
  try { return readFileSync(path, "utf-8"); }
  catch (e) { return `Error reading file: ${path}. ${e}`; }   // read failure ⇒ error STRING as content
}
```

**Flow:** client requests `completion/complete` for the `name` argument → SDK passes typed `value` plus `context.arguments` holding already-supplied args → completer filters its per-department roster by `startsWith` and returns ≤N suggestions → on prompt GET the handler receives zod-parsed strings and renders one user message. File resources: at construction, scan `docs/`; per FILE entry (statSync.isFile check) register `demo://resource/static/document/<encodeURIComponent(name)>` with extension-derived mimeType (.md/.markdown→text/markdown, .txt→text/plain, .json→application/json, default text/plain).

**Invariant:** an unknown or missing earlier argument yields EMPTY suggestions (`return []`) — never a guess across departments. Registration-time vs read-time failure asymmetry in files.ts is deliberate: unreadable DIRECTORY skips the whole family silently (no broken URIs listed), while unreadable individual FILE returns an error-message string as content so the URI still resolves. Directories are excluded from registration.

**Probe:** `src/everything/__tests__/prompts.test.ts:83–111` pins the rendered message `'Please promote Alice to the head of the Engineering team.'` and cross-department variants; `resources.test.ts:268–282` asserts `registerFileResources` registers against the real docs dir; template-side completers separately pinned in `resource-template-completers`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "createMockServer prompts completions", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt `completable()` with context-threaded dependent filtering (empty-on-unknown), extension-mapped static file resources with encodeURIComponent'd URIs, and the skip-family-vs-error-content failure asymmetry; adapt rosters/mime map to your domain; omit client-side guessing of dependent values and omit registering unreadable directories.
