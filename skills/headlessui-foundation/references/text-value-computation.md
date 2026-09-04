<!-- capsule-v2 -->
# Text value computation — what string does an option contribute to typeahead when it has aria labels, hidden spans, or emoji?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is getTextValue's precedence chain and the clone-and-strip innerText algorithm?

## getTextValue / getTextContents
**Path/Symbol:** `packages/@headlessui-react/src/utils/get-text-value.ts:3-83`.
**Signature:** `getTextValue(element: HTMLElement): string`; `getTextContents(element): string` (private).
**Data Shape:** returns trimmed string; emoji regex `/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g` (deliberate, `\p{Extended_Pictographic}` not yet relied on).

### Decisive source
```ts
export function getTextValue(element) {
  let label = element.getAttribute('aria-label')
  if (typeof label === 'string') return label.trim()            // 1. aria-label
  let labelledby = element.getAttribute('aria-labelledby')      // 2. aria-labelledby (space-separated ids)
  if (labelledby) {
    let labels = labelledby.split(' ').map((id) => {
      let labelEl = document.getElementById(id)
      if (labelEl) {
        let label = labelEl.getAttribute('aria-label')          //    2a. referenced el's own aria-label
        if (typeof label === 'string') return label.trim()
        return getTextContents(labelEl).trim()                  //    2b. referenced el's contents
      }
      return null
    }).filter(Boolean)
    if (labels.length > 0) return labels.join(', ')
  }
  return getTextContents(element).trim()                        // 3. own contents
}
function getTextContents(element) {
  let currentInnerText = element.innerText ?? ''
  let copy = element.cloneNode(true)                            // work on a CLONE
  for (let child of copy.querySelectorAll('[hidden],[aria-hidden],[role="img"]')) child.remove()
  let value = dropped ? copy.innerText ?? '' : currentInnerText // recompute ONLY if something was dropped
  if (emojiRegex.test(value)) value = value.replace(emojiRegex, '')
  return value
}
```

**Flow:** aria-label wins outright → aria-labelledby resolves each id recursively through the same rules and joins with ', ' → otherwise clone the node, delete `[hidden]`/`[aria-hidden]`/`[role=img]` subtrees, read innerText of the clone, strip emoji. innerText is used over textContent because it excludes script/style and reflects rendering.
**Invariant:** multiple labelledby ids join with COMMA+space (matches accessible-name computation); emoji stripping exists because typeahead matches single keystrokes — pictographs would poison prefixes; only re-read innerText on the clone when nodes were actually removed (innerText is expensive).
**Probe:** direct test `packages/@headlessui-react/src/utils/get-text-value.test.ts` pins precedence, hidden/aria-hidden/role=img stripping, and emoji removal. Graph probe resolves getTextValue + LabelProvider line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "getTextValue", name_pattern: "^getTextValue$", limit: 5 });
```

## Verdict
Adopt the precedence chain and clone-strip algorithm verbatim — this IS the accessible-text contract your typeahead should match; adapt the emoji vocabulary as Unicode support matures; omit the labelledby recursion only if your components never reference external labels.
