<!-- capsule-v2 -->
# campaign-template-two-layer-compile — How do base template and campaign body compose into one executable template?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** How is `{{ template "content" . }}` wired so subject/body/altbody/header templates share one FuncMap?

## AddParseTree grafting with per-part compilation
**Path/Symbol:** `models/campaigns.go:CompileTemplate` (:141-242), `hasTplExpr` (:244-247); template func providers `manager.TemplateFuncs` (:371-432) + sprig subset with env/exec/host lookups DELETED (`makeGnericFuncMap` :654-674).
**Signature:** `func (c *Campaign) CompileTemplate(f template.FuncMap) error`.
**Data Shape:** names BaseTPL="base", ContentTpl="content"; visual campaigns get body `{{ template "content" . }}` passthrough.

### Decisive source
```go
baseTPL, err := template.New(BaseTpl).Funcs(f).Parse(body) // TemplateBody as base
...
msgTpl, err := template.New(ContentTpl).Funcs(f).Parse(body) // campaign Body
out, err := baseTPL.AddParseTree(ContentTpl, msgTpl.Tree)   // GRAFT child into base
c.Tpl = out
```

**Flow:** subject compiled separately IF it contains `{{...}}` (txt/template — no HTML escaping in subjects) → base = TemplateBody (or content-passthrough for visual/plain-empty) → markdown converted BEFORE message compile when ContentType=markdown → message tree grafted under name "content" so base's `{{ template "content" . }}` renders it → altbody and custom headers each conditionally compiled when they contain template expressions (HeaderTpls map preserved per header-set for render time). Regexp pre-pass (`regTplFuncs`) rewrites legacy `{{ TrackLink "..." }}`-style call syntaxes before parsing.
**Invariant:** The FuncMap must be IDENTICAL across all parts (TrackLink needs *CampaignMessage at execute time; sprig's env/expandenv/getHostByName are security-deleted). Compilation happens ONCE per campaign load in newPipe — never per message; per-message work is only Execute.
**Probe:** `bash -c "cd <repo> && grep -nF 'AddParseTree' models/campaigns.go"` → :211; `grep -cF 'delete(sprigFuncs, \"env\")' internal/manager/manager.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "CompileTemplate base content", limit: 10 });
```
## Verdict
Adopt two-layer graft composition with shared sanitized FuncMap compiled once per job. Adapt Go template specifics to your engine. Omit markdown conversion choice.
