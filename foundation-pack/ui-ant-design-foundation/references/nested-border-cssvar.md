<!-- capsule-v2 -->
# Nested-border CSS-var protocol — how do parent/child component borders coordinate through a custom property instead of props?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter coordinating styles between a host component and embedded instances of itself needs a publish/consume/reset channel that survives DOM nesting without React context.

## Publish / consume / reset
**Path/Symbol:** `components/table/style/bordered.ts:genBorderedStyle` (8–173), using `genCssVar(antCls, 'table')` from `components/theme/util/genStyleUtils.ts`.
**Signature:** `const [varName, varRef] = genCssVar(antCls, 'table')` → `varName('nested-border-top')` declares `--ant-table-nested-border-top`; `varRef(name, fallback)` reads it back with a default.
**Data Shape:** one published variable per wrapper scope; consumed exactly once (`container:first-child`); reset in one nested scope.

### Decisive source
```ts
[`${componentCls}-wrapper`]: {
  [varName('nested-border-top')]: tableBorder,            // PUBLISH
  [`${componentCls}${componentCls}-bordered`]: {
    [`> ${componentCls}-container`]: {
      '&:first-child': {
        borderTop: varRef('nested-border-top', tableBorder), // CONSUME w/ fallback
      },
    },
  },
  [`${componentCls}-cell`]: {
    [`> ${componentCls}-wrapper:only-child,
       > ${componentCls}-expanded-row-fixed > ${componentCls}-wrapper:only-child`]: {
      [varName('nested-border-top')]: 0,                     // RESET for nested
    },
  },
},
```

**Flow:** every Table wrapper publishes its resolved top border as `--ant-table-nested-border-top`. A bordered container's first child reads that variable (fallback = its own computed border) so a title bar and body share ONE border line even when values differ per theme. When a table is EMBEDDED in another table's cell (`-wrapper:only-child`), the outer cell re-publishes the variable as `0`, so the inner table inherits no stray top border — coordination happens entirely through the CSS cascade.
**Invariant:** fallback always equals the locally-computed value, so a consumer rendered outside any publisher is still correct; the reset targets ONLY direct-child nesting scopes (`:only-child`), never global. Related bordered-plane contracts captured here: header split-line `th::before` neutralized under `-bordered` (`backgroundColor:'transparent !important'`); fixed-right separator dedup — `-cell-fix-right-first:not(-cell-fix-right-last)::after` carries `borderInlineEnd` only when ≥2 fixed-right columns exist (#56287, prevents doubled vertical line); expanded-row-fixed gets an `::after` border at `insetInlineEnd: lineWidth`; scrollbar-width compensation via `boxShadow: 0 lineWidth 0 lineWidth tableHeaderBg` on `-cell-scrollbar`.

**Probe:** `components/table/__tests__/__snapshots__/demo.test.ts.snap` nested-table demos render both wrapper scopes (outer publish + inner reset) — grep the snap for `nested-table-border-debug` demo output.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "genBorderedStyle nested-border-top varName varRef", limit: 10 });
```

## Verdict
Adopt the publish/consume/reset custom-property protocol for self-nesting components — it removes prop/context plumbing and composes across library boundaries. Adapt variable naming to your prefix scheme (see cssvar-naming-contract). Omit antd's specific bug-fix selectors unless you inherit the same double-border geometry. Coverage: bordered.ts read in full (175 lines), `no_recorded_issue`.
