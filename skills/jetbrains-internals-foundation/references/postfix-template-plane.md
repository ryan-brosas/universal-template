<!-- capsule-v2 -->
# Postfix template plane — how are code-transformation snippets declared as before/after pairs?

**Source:** JetBraBeans IDE distributions (proprietary distribution); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How are postfix (`.expr` → transformation) templates declared, and what is the before/after/description triple + `<spot>` marker contract?

## Connected graph-selected seam
**Path/Symbol:** `plugins/javascript-plugin/lib/modules/intellij.javascript.backend.jar:postfixTemplates/<TemplateName>/{before,after}.<lang>.template + description.html` (322 in localization-ja mirror; 81 in the JS backend jar); core set also in `intellij.platform.ide.jar`.
**Signature:** dir per template class; `after.ts.template` = transformed snippet with `<spot>` marking the caret landing; `before.ts.template` = pre-transform shape; `description.html` = human prose.
**Data Shape:** `JSArgumentPostfixTemplate/after.ts.template` = `function m(id) {\n    foo(<spot>id</spot>)\n}` — the `<spot>` element is the caret anchor; the `before` template is the matcher pattern. Templates are language-suffixed (`.ts.template`, `.es6.template`) so one template dir can carry per-dialect variants.

### Decisive source
```
postfixTemplates/JSArgumentPostfixTemplate/after.ts.template
function m(id) {
    foo(<spot>id</spot>)
}
```

**Flow:** user types `expr.` → postfix engine matches the template's `before` shape against the expression → applies `after` with `<spot>` as caret → `description.html` feeds the popup. Localization packs mirror the dir tree and translate only `description.html` (prose), never the code templates.
**Invariant:** `<spot>` is the ONLY caret marker and appears exactly once per after-template; the `before`/`after` pair must stay in lockstep — a porter who edits one without the other breaks the transform. The `<lang>` suffix is how dialects coexist in one dir.
**Probe:** `unzip -p plugins/javascript-plugin/lib/modules/intellij.javascript.backend.jar postfixTemplates/JSArgumentPostfixTemplate/after.ts.template` → contains `<spot>`; `unzip -l … | grep -c postfixTemplates` → 81.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "postfix template completion", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: dir-per-template with before/after language-suffixed pairs + `<spot>` caret marker + separate prose description, localization mirroring only prose. Adapt the marker to your editor's caret model. Omit the template corpus. This is the transformation twin of pass-2's live-template-set-contract (liveTemplates = insert snippets; postfixTemplates = `.trigger` transforms).
