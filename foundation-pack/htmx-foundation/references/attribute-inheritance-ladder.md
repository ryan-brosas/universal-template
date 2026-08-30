<!-- capsule-v2 -->
# Attribute inheritance ladder — how do closest-value lookup, `hx-disinherit`, `hx-inherit`, and literal `"unset"` compose?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** When an element omits an attribute like `hx-target`, from where does the value come, and how must a porter reproduce disinherit/unset without breaking explicit local values?

## getClosestAttributeValue: nearest-wins walk with a sentinel short-circuit
**Path/Symbol:** `src/htmx.js:getClosestAttributeValue` (:490-498) over `getAttributeValueWithDisinheritance` (:466-483); raw dual-prefix read `getAttributeValue` (:417-419); walk primitive `getClosestMatch` (:452-458).
**Signature:** `function getClosestAttributeValue(elt, attributeName)` → `string | undefined`; helper `function getAttributeValueWithDisinheritance(initialElement, ancestor, attributeName)` → `string | 'unset' | null`.
**Data Shape:** Every attribute read resolves BOTH prefixes: `getAttributeValue` returns `getAttribute(name) || getAttribute('data-' + name)` (raw attribute wins over data twin). Walk state is one closure variable `closestAttr`; there is no early return inside the predicate.

### Decisive source
```js
function getAttributeValueWithDisinheritance(initialElement, ancestor, attributeName) {
    const attributeValue = getAttributeValue(ancestor, attributeName)
    const disinherit = getAttributeValue(ancestor, 'hx-disinherit')
    var inherit = getAttributeValue(ancestor, 'hx-inherit')
    if (initialElement !== ancestor) {
      if (htmx.config.disableInheritance) {
        if (inherit && (inherit === '*' || inherit.split(' ').indexOf(attributeName) >= 0)) {
          return attributeValue
        } else {
          return null
        }
      }
      if (disinherit && (disinherit === '*' || disinherit.split(' ').indexOf(attributeName) >= 0)) {
        return 'unset'
      }
    }
    return attributeValue
}

function getClosestAttributeValue(elt, attributeName) {
    let closestAttr = null
    getClosestMatch(elt, function(e) {
      return !!(closestAttr = getAttributeValueWithDisinheritance(elt, asElement(e), attributeName))
    })
    if (closestAttr !== 'unset') {
      return closestAttr
    }
}
```

**Flow:** start at the element itself (`initialElement === ancestor` branch skips inherit logic — own attributes always apply) → walk ancestors via `parentElt` (which steps into ShadowRoot hosts, :425-429) → first ancestor whose computed value is truthy wins → if that winner is the string `'unset'`, return `undefined`.
**Invariant:** The `'unset'` value is a SENTINEL that means "stop inheriting" only for lookups that pass through it; an ancestor *below* the unset marker still sees its own nearer value because the walk stops at the first hit. `hx-disinherit="*"` blocks all inherited attrs; a space-separated list blocks named ones. With `config.disableInheritance = true` the default flips: nothing inherits except attrs named in the ancestor's `hx-inherit` list (`'*'` allowed). Note `getClosestMatch`'s predicate assigns-and-coerces, so an ancestor value of `'unset'` is truthy there but converted to `undefined` by the final check — porters who treat it as falsy mid-walk will wrongly fall through to grandparents.

**Probe:** `grep -n "unset properly unsets a given attribute" /mnt/hdd/utopia/inspo/external/htmx/test/core/internals.js` → hits :142 and :148; the third test "unset does not unset a value below it in the hierarchy" (:154-158) asserts `getClosestAttributeValue(div,'foo') === '2'` when `foo=unset` sits ABOVE `foo=2`. Disinherit default-mode boundary pinned by `test/attributes/hx-disinherit.js` "disinherit exclude single attribute" (:24). Executed headless (Node vm, Element subclasses): own-parent unset → undefined; literal own `foo=unset` → undefined; unset-above-nearer → `'2'`; `hx-disinherit:'foo'` blocks foo but not bar; `'*'` blocks all; strict mode returns `null` for non-inherited and `2` with `hx-inherit:'foo'`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "disinherit inherit unset closest attribute", limit: 4 });
```
(rank-1 `src.htmx.getClosestAttributeValue src/htmx.js 490-498`)

## Verdict
Adopt the nearest-wins walk, both-prefix resolution, and the three-way composition (own value > inheritance rules > unset sentinel). Adapt the `'unset'` magic string into a typed sentinel if your host language has symbols. Omit ShadowRoot stepping in `parentElt` only if your host has no shadow DOM. Coverage caveat: browser-only semantics (real DOM inheritance through live trees) verified here headless against source-derived expectations, not the repo's mocha runner.
