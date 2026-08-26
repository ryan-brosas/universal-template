<!-- capsule-v2 -->
# inline-image-cid-embed — How are <img data-embed> tags turned into cid attachments exactly once?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** Where in the pipeline does body rewriting happen and how are duplicate images deduped?

## Regex-tagged embed with per-campaign CID cache
**Path/Symbol:** `internal/manager/manager.go` — consts/regexes (:33-39), `LoadInlineImages` (:766-781), `applyInlineImages` (:783-817), `MakeContentID` (:820-823), `filenameFromSrc` (:826-834), attachment headers (:837-859).
**Signature:** `func (m *Manager) applyInlineImages(body string, cache map[string]string) (string, []models.Attachment)`.
**Data Shape:** tag marker attribute `data-embed`; Content-ID = hex(sha1(src)[:8]) + "@email"; one attachment part per UNIQUE src filename.

### Decisive source
```go
cid, ok := cache[src]
if !ok {
	if a, c, err := m.store.GetInlineAttachmentByFilename(fname); err == nil {
		atts = append(atts, a)
		cid = c
	} else {
		m.log.Printf("inline image %q not embedded: %v", src, err)
	}
	cache[src] = cid // negative results cached too
}
if cid == "" { return tag } // leave unresolved tags untouched
return reImgSrc.ReplaceAllString(tag, `${1}src="cid:`+cid+`"`)
```

**Flow:** BEFORE template compile, scan campaign body AND template body with one shared cidCache → each `<img ... data-embed ...>` tag's src resolved to filename (URL-path aware, `path.Base`) → media fetched once per unique src → img rewritten to `src="cid:<id>"`, attachment appended with Content-ID/inline disposition headers. Already-cid sources and unresolvable filenames pass through untouched. attachMedia later skips re-adding if ANY non-inline attachment exists (idempotence guard).
**Invariant:** Resolution happens once per CAMPAIGN (shared cache across body+template), not per message — doing it per-subscriber would multiply DB fetches and duplicate MIME parts. Failed lookups are cached as empty so a missing image logs once, not per recipient. Plain-text campaigns short-circuit entirely.
**Probe:** `bash -c "cd <repo> && grep -cF 'data-embed' internal/manager/manager.go"` → 3 (const + 2 regex/contains uses); `grep -cF '@email' internal/manager/manager.go` → 1; `grep -cF 'GetInlineAttachmentByFilename' internal/manager/manager.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "inline image cid embed", limit: 10 });
```
## Verdict
Adopt pre-compile one-shot asset embedding with negative-result caching. Adapt regex tagging to your editor's marker convention. Omit the sha1-CID scheme specifics.
