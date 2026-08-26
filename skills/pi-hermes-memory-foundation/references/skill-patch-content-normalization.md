<!-- capsule-v2 -->
# Skill patch content normalization — LLM format-drift cannot wipe or splice skill sections

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** How do you accept free-form section-patch payloads from an LLM and guarantee that format drift (JSON arrays instead of Markdown lists, JSON objects, stray `##` headers) can never wipe an existing section or inject a new one?

## Patch content normalization
**Path/Symbol:** `src/store/skill-store.ts` — `normalizeSkillPatchContent` (:91–153), `formatPatchList` (:73–84), `looksLikeJsonArray`/`looksLikeJsonObject` (:63–71), `LIST_SECTIONS` (:51), header-injection regex :142.
**Signature:** `normalizeSkillPatchContent(section: string, rawContent: string): { content: string } | { error: string }`.
**Data Shape:** input is a raw LLM string for one section body; output is either normalized Markdown body text or a single actionable error string. `LIST_SECTIONS = {"procedure","pitfalls","verification"}` (lowercased keys).

### Decisive source
```ts
// normalizeSkillPatchContent (91-153): ordered coercion ladder
let content = typeof rawContent === "string" ? rawContent.trim() : "";
if (!content) return { error: "New content is required for patch. Prefer structured fields ..." };
if (looksLikeJsonObject(content)) return { error: "Patch content looks like a JSON object..." };
if (looksLikeJsonArray(content)) {
  const parsed = JSON.parse(content);
  if (!Array.isArray(parsed)) return { error: "...not a string array." };
  const items = parsed.filter(i => typeof i === "string").map(i => i.trim()).filter(Boolean);
  if (items.length === 0) return { error: "Patch content JSON array must contain non-empty strings." };
  if (key === "when to use")        content = items.join("\n\n");            // paragraphs
  else if (LIST_SECTIONS.has(key))  content = formatPatchList(sectionName, items); // numbered / bulleted
  else                              content = items.map(i => `- ${i}`).join("\n");
} catch { return { error: "Patch content looks like a JSON array but could not be parsed..." }; }
// Reject payloads that would inject extra ## sections mid-body:
if (/^#{1,6}\s+\S/m.test(content)) return { error: "Patch content must not include Markdown section headers (## ...)." };
if (!content.trim()) return { error: "New content is required for patch." };
return { content: content.trim() };

// formatPatchList (73-84): pitfalls get bullets, everything else ordered steps
if (key === "pitfalls") return cleaned.map(item => `- ${item.replace(/^[-*]\s+/, "")}`).join("\n");
return cleaned.map((item, index) => `${index + 1}. ${item.replace(/^\d+\.\s+/, "").replace(/^[-*]\s+/, "")}`).join("\n");
```

**Flow:** (1) Section name must be non-empty after stripping leading `#`s. (2) Empty/non-string payload → error pointing at structured fields first. (3) Object-shaped payload → rejected outright (never coerced). (4) Array-shaped payload → parsed; non-strings filtered; empty-after-filter → error; then shaped per section kind (`when to use` → blank-line-separated paragraphs, pitfalls → `- ` bullets with existing bullet markers stripped, procedure/verification → `1.`-numbered with existing numbering stripped, unknown sections → generic bullets). (5) Unparseable array → error. (6) ANY remaining heading anywhere in the body (`m` flag) → error, because the patch replaces only ONE section's body and a nested header would split it into two on next patch. (7) Caller (`SkillStore.patch`, :463–524) runs this BEFORE scanning/loading, so a rejected payload never touches disk.

**Invariant:** a section patch can never create or destroy a `##` section boundary — object payloads are refused, arrays are coerced to list-shaped bodies whose items have their own list markers stripped (so numbering/bullets never double), and any residual heading fails the write. The regex strips BOTH prior numberings (`^\d+\.\s+`) and bullets (`^[-*]\s+`) before re-formatting, making re-patching idempotent (a patched procedure can be re-coerced without marker accumulation).

**Probe:** `tests/store/skill-store.test.ts` — `coerces JSON string arrays into ordered Procedure steps` (:355), `rejects JSON object patch payloads` (:372), `rejects empty patch content` (:385), `rejects patch content that injects section headers` (:395). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "normalizeSkillPatchContent formatPatchList looksLikeJsonArray", limit: 5 });
// live-verified rank-exact: formatPatchList :73-84, looksLikeJsonArray :63-66, normalizeSkillPatchContent :91-153
```

## Verdict
Adopt the coercion ladder (empty→object→array→header-injection ordering matters: cheap shape checks before parsing), the per-section-kind list shaping with marker stripping, and the blanket heading rejection for single-section patches. Adapt section names and list formats to the host. Omit the `when to use` paragraph special case unless the target has prose-shaped sections.
