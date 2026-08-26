<!-- capsule-v2 -->
# HashUtil git-style offset aliases — how does grist resolve `HEAD~2^1` against a flat state list without a commit graph?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the parsing contract for hash aliases over DocState arrays, and which malformed inputs must throw?

## Split on operator runs, walk parts, every step is additive
**Path/Symbol:** `app/server/lib/HashUtil.ts` — `class HashUtil` (:17–45), constructor takes `DocState[]` MOST-RECENT-FIRST; `hashToOffset(hash: string): number` (:27–44). Direct test: `test/server/lib/HashUtil.ts` (34 assertions).
**Signature:** `hashToOffset(hash: string): number` → index into the constructor's array (0 = newest); throws `"Cannot read hash"` / `"cannot parse hash"`.
**Data Shape:** `DocState = {n: number, h: string}` (`n`=action count, `h`=trigram hash); grist history is FIRST-PARENT-ONLY, so `^N` beyond 1 is illegal by construction.

### Decisive source
```ts
// HashUtil.ts:27-44
public hashToOffset(hash: string): number {
    const parts = hash.split(/([~^][0-9]*)/);
    hash = parts.shift() || "";
    let offset = hash === "HEAD" ? 0 : this._state.findIndex(state => state.h === hash);
    if (offset < 0) { throw new Error("Cannot read hash"); }
    for (const part of parts) {
      if (part === "^" || part === "^1") {
        offset++;
      } else if (part.startsWith("~")) {
        offset += parseInt(part.slice(1) || "1", 10);
      } else if (part === "") {
        // pass
      } else {
        throw new Error("cannot parse hash");
      }
    }
    return offset;
}
```
Test matrix highlights (test/server/lib/HashUtil.ts): `"HEAD"`→0 but `"head"` THROWS (:10–13 — case-sensitive sentinel); `"312355"` THROWS (unknown hash :15–18); `"3123~3"`→4 walks OFF THE END without error (:21–37) — bounds are the CALLER's job; `"~"`,`"~~"`,`"~e"`,`"HEAD^2"`,`"HEAD^e"` all THROW (:33–36,46–48).

**Invariant:** (1) `split(/([~^][0-9]*)/)` with a CAPTURING group interleaves separators into the result — `parts.shift()` peels the base token; empty strings between adjacent operators are skipped by the `part === ""` arm (that's why `"HEAD~~"` works). (2) `^` accepts ONLY bare or `^1`; any other caret suffix (`^2`, `^e`) throws — encodes "no merge parents in grist". `~N` accepts any non-negative integer with default 1 when digits are absent (`part.slice(1) || "1"`). (3) Offsets are purely ADDITIVE: alias chains compose in any order (`HEAD~^1~2` == 4), because first-parent history is linear. (4) NO bounds check: `HEAD~99` returns a too-large index; callers (DocApi compare endpoints) must validate against `_state.length`. (5) Hash lookup is EXACT full-trigram equality, case-sensitive.

**Flow:** `/api/docs/:docId/compare`-family endpoints take `leftHash`/`rightHash` → `new HashUtil(await activeDoc.getDocStates())` per request (states freshest-first from action history) → offsets drive ActionSummary diff windows.

**Probe:** direct test exists and is byte-cited:
```bash
cd /mnt/hdd/utopia/inspo/grist-core
grep -c 'finder.hashToOffset(' test/server/lib/HashUtil.ts   # 34 assertions
grep -nF 'split(/([~^][0-9]*)/)' app/server/lib/HashUtil.ts  # 28
grep -nF 'parseInt(part.slice(1) || "1", 10)' app/server/lib/HashUtil.ts  # 36
grep -nF 'part === "^1"' app/server/lib/HashUtil.ts          # 33
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "hashToOffset state hashes HEAD parent alias", limit: 4 });
// → grist-core.app.server.lib.HashUtil.HashUtil.hashToOffset Method app/server/lib/HashUtil.ts 27-44 rank#1
```

## Verdict
Adopt for any linear-history store (append-only logs, undo stacks) that wants ergonomic git-flavored addressing: capturing-split parse + additive walk + strict `^` grammar. KEEP the caller-side bounds check discipline (this class deliberately omits it); keep case-sensitivity of `HEAD`. Omit `~N` multi-step only if your UX never emits compound aliases.
