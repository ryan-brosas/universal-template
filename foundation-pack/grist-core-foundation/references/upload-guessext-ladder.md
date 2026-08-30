<!-- capsule-v2 -->
# Extension sniffing ladder — which of originalName, mimeType, and file CONTENT wins when they disagree?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact precedence order for picking a stored extension, and which special cases short-circuit content inspection?

## json-mime trust > csv-origExt hardcode > agree-check > magic-byte detect > generic-mime demotion
**Path/Symbol:** `app/server/lib/guessExt.ts` — `guessExt(filePath, fileName, mimeType)` (:15–59); called from `handleOptionalUpload` (`uploads.ts`:237) and `_fetchURL` (:490).
**Signature:** `guessExt(filePath: string, fileName: string, mimeType: string | null): Promise<string>`.
**Data Shape:** input = on-disk path (for content sniffing), client-supplied name, transport-declared mime; output = dotted lowercase ext (e.g. `".csv"`).

### Decisive source
```ts
const origExt = path.extname(fileName).toLowerCase();
let mimeExt = extension(mimeType); if (mimeExt) mimeExt = "." + mimeExt;
if (mimeExt === ".json") {
  // It's common for JSON APIs to specify MIME type, but origExt might come from a URL with
  // periods that don't indicate a meaningful extension. Trust mime-type here.
  return mimeExt;
}
if (origExt === ".csv") {
  // File type detection doesn't work for these, and mime type can't be trusted. E.g. Windows
  // may report "application/vnd.ms-excel" for .csv files.
  return origExt;
}
// If extension and mime type agree, let's call it a day.
if (origExt && (origExt === mimeExt || lookup(origExt.slice(1)) === mimeType)) {
  return origExt;
}
// If not, let's take a look at the file contents.
const detected = await fileTypeFromFile(filePath);
if (detected) { return "." + detected.ext; }        // magic bytes win when detection works
if (mimeExt === ".txt" || mimeExt === ".bin") {
  return origExt || mimeExt;                        // too generic — only as last resort
}
return origExt || mimeExt;                          // tough call
```

**Flow:** every upload (multipart or URL-fetched) passes through this BEFORE registration → JSON mime is trusted unconditionally (URLs carry junk dots) → `.csv` in the NAME beats everything except json-mime because magic-byte detection cannot identify CSV and Windows mimes lie → name/mime agreement ends it → otherwise libmagic-style content detection decides → generic text/plain & octet-stream are demoted below any real hint.
**Invariant:** precedence order is a security-relevant contract — import parser selection AND attachment re-download naming both key on this value, so "trust the browser" and "trust magic bytes" are both wrong alone; content sniffing runs on the STORED file (post-download), never on the client string; the function NEVER throws on unknown types — worst case returns a best-effort string.
**Probe:** `test/server/lib/uploads.ts` (:213–244 exercises the ladder through fetchURL: csv content-type + url basename → `{origName:"url", ext:".csv"}`; text/plain + `/file.csv` URL → url wins; application/json + `/file3.csv` → `.json` wins); `test/server/lib/ActiveDoc.ts`:1252 uses `guessExt(filePath, file.name, null)` for attachment fixtures.
**Caveat:** runner-blocked here; probes recorded as pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "guessExt fileTypeFromFile mime-types extension lookup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-rung ladder verbatim — each rung exists because a real failure mode was observed (Windows csv mime lies, URL junk dots, magic-byte gaps). Adapt the special-case list to your product's formats. Omit any single-signal shortcut; the whole point is disagreement resolution.
