<!-- capsule-v2 -->
# Legacy template migration to variant tree — how do I migrate old flat message templates (with a REVERSED if-then-else encoding) into a structured variants AST without corrupting user text?

**Source:** lh-basis (Linked Helper extract) NO LICENSE — learn-only, patterns recorded, zero code copied `extract mtime 2026-08-15`; Codebase Memory project `lh-basis` (dist plane outside roots — direct source probes). **Question:** when a product evolves its template format from `{valueParts[], variables[]}` arrays into a node tree with variants, what does a safe migration look like — and where does the classic then/else index trap hide?

## Format sniffing → per-node interleave → reversed-options if-then-else → wrap-in-single-variant

**Path/Symbol:** `MessageTemplate/LegacyMessageTemplate.js:LegacyMessageTemplate.migrateMessageTemplate/isLegacyMessageTemplateFormat/migrateSubjectTemplate/migrateAttachmentImageUrlTemplate/migrateMessageTemplateConfigIfNeeded`; helpers `helpers/object.js:isPlainObject`.
**Signature:** `migrateMessageTemplate(legacy) -> {type:"variants", variants:[{type:"variant", child: groupNode}]}`; `isLegacyMessageTemplateFormat(x) -> boolean`; `migrateMessageTemplateConfigIfNeeded(config) -> config` (returns ORIGINAL object untouched unless any of its three template slots is legacy).
**Data Shape:** legacy node = `{valueParts: string[], variables?: string[]}` OR an if-then-else marker `{type:"if-then-else", valueParts, variables?, options: {0: legacy[], 1: legacy[]}}`; target nodes = `{type:"text"|"var", value|name}` under `{type:"group"|"if"|"then"|"else"|…}`; attachment twin adds image-url shapes (`{type:"text", textTemplate}` or vendor `{type:"uclic"|"hyperise", baseUrl, variables}`).

### Decisive source
```js
// INTERLEAVE: parts[i] is the text BEFORE variable[i] (text-first pairing):
function toNodes({valueParts, variables}) {
  const n = Math.max(valueParts.length, variables?.length ?? 0), out = [];
  for (let i = 0; i < n; i++) {
    if (valueParts[i]) out.push({type:"text", value:valueParts[i]});
    if (variables?.[i]) out.push({type:"var", name:variables[i]});
  }
  return out;
}

// RECURSION WITH THE TRAP INSIDE: options[1] is THEN, options[0] is ELSE.
function build(nodes) {
  return nodes.reduce((group, node) => {
    if ("type" in node && node.type === "if-then-else") {
      group.children.push({
        type: "if",
        if:   { type: "group", children: toNodes(node) },
        then: build(node.options[1]),     // <-- [1] = THEN (reversed vs intuition)
        else: build(node.options[0]),     // <-- [0] = ELSE
      });
    } else {
      group.children.push(...toNodes(node));
    }
    return group;
  }, {type:"group", children:[]});
}

// SNIFF-THEN-MIGRATE, PER SLOT, RETURNING THE ORIGINAL WHEN NOTHING IS LEGACY:
function migrateMessageTemplateConfigIfNeeded(cfg) {
  let migrated;
  if (isLegacyMessageTemplateFormat(cfg.messageTemplate))
    migrated = migrateMessageTemplate(cfg.messageTemplate);
  if (isLegacyMessageTemplateFormat(cfg.subjectTemplate)) …
  if (isLegacyAttachImageUrlTemplateFormat(cfg.attachmentImageUrlTemplate)) …
  return migrated ?? cfg;               // modern configs pass through UNTOUCHED
}
```

**Flow:** on load, each config template slot (message / subject / attachment-image-url) is sniffed independently → legacy array format is detected structurally (plain objects with `valueParts: string[]`, if-markers carrying `options.0/options.1` arrays) → each legacy node interleaves into text/var children with the if-condition built from its own `valueParts` → nested if-then-else recurses with options[1]→then, options[0]→else → the whole tree wraps as ONE variant so downstream consumers see uniform `{variants:[…]}` shape → modern-shaped values short-circuit and return the original config object unchanged.
**Invariant:** the options-index reversal is the whole trap — migrating `options[0]`→then silently SWAPS branch content for every historical template, producing grammatically valid messages that promise the wrong thing (e.g. else-branch greeting sent to matched prospects). Detection must be structural over EVERY element (`Array.isArray && every(isLegacyNode)`), not a probe of element zero, because mixed arrays would half-migrate. The migrate function must be IDEMPOTENT at the config level: `migrated ?? cfg` returns the same reference when nothing changed so persistence layers can skip writes by identity. Text/var pairing is positional (`valueParts[i]` precedes `variables[i]`) — sorting or re-pairing by existence order scrambles sentences around variables.
**Probe:** no public tests (proprietary extract) — coverage caveat. Deterministic probes verified at extract (anchored at `lh-basis/core/local-source/dist`): `grep -c "options\\[1\\]" MessageTemplate/LegacyMessageTemplate.js` ⇒ exactly 1 (the single decisive then-site); `grep -oP "type:.?\"if-then-else\"" MessageTemplate/LegacyMessageTemplate.js | wc -l` ⇒ 2 (detector + builder); `grep -n "migrateAttachmentImageUrlTemplate" MessageTemplate/LegacyMessageTemplate.js` pins the third slot's vendor-shape branch (`uclic|hyperise`). Graph anchor: project `lh-basis` has no in-graph node for this file (dist excluded from indexing by design) — direct source probes only, consistent with sibling lh-basis capsules.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-migrations", query: "CREATE TABLE", limit: 5 });
// migration-family context lives in lh-basis-migrations; this seam itself is source-probe only
```

## Verdict
Adopt the shape: sniff-per-slot structurally, recurse with an explicit (and tested!) options-index map, wrap in a single-variant envelope for uniform downstream typing, and return the original object when no slot needs migration. Adapt node vocabulary to your editor's AST. Omit nothing structural — but WRITE THE REVERSAL DOWN as a named constant in your port (`THEN_INDEX = 1`) because the next maintainer will "fix" it. Contrast message-template-substitution (linvo's runtime `{{var}}` substitution — the RENDER side; this capsule is the STORAGE-format migration side). Patterns only — no-license source.
