# Extraction: structure, styles, patterns

## Three CSS layers

| Layer | Source | Answers |
|---|---|---|
| Network CSS | saved `.css` responses from the archive | exact rules as shipped |
| CSSOM | `document.styleSheets` dump | what the browser parsed, including inline and injected styles |
| Computed styles | `getComputedStyle` on selected elements | rendered values after cascade and inheritance |

## CSSOM dump

```js
[...document.styleSheets].flatMap(s=>{try{return [...s.cssRules].map(r=>r.cssText)}catch(e){return []}}).join("\n")
```

## CSS custom properties

```js
(()=>{const out={};for(const ss of document.styleSheets){let rules;try{rules=ss.cssRules}catch(e){continue}
for(const r of rules){const sel=r.selectorText||"";if(sel===":root"||sel==="html"){
for(let i=0;i<r.style.length;i++){const p=r.style[i];if(p.startsWith("--"))out[p]=r.style.getPropertyValue(p)}}}}
return JSON.stringify(out,null,1)})()
```

## Computed styles (selected elements, bounded property list)

Do not dump every property for every node. Pick elements that answer the question and a property set that matters:

```js
(()=>{const props=["display","position","width","gap","padding","margin","font-family","font-size",
"font-weight","line-height","color","background-color","border-radius","box-shadow","transition"];
const out=[];for(const el of document.querySelectorAll("h1,h2,nav,a,button,section,footer")){
if(out.length>40)break;const cs=getComputedStyle(el);
out.push({tag:el.tagName,cls:(el.className||"").toString().slice(0,40),
style:Object.fromEntries(props.map(p=>[p,cs.getPropertyValue(p)]))})}
return JSON.stringify(out)})()
```

## Patterns, not components

Repeated visual structures are recorded as patterns: navigation, hero, card grid, pricing card, form controls, footer, sidebar items, modals, tables, command palettes. Count repetitions (`querySelectorAll` length), describe structure, and never claim framework boundaries without source evidence.

## Tokens (deep mode only)

Derive candidates from frequency, not from single values: font families and sizes, spacing values, radii, shadows, colors, breakpoint media queries, transition durations and easings. Store them under `design/*.json`. Adoption maps against the current project's tokens through `reference-driven-development`; never a blind copy.

## Responsive evidence

Default viewports: desktop 1440 and mobile 390. Add tablet or other sizes only when the CSSOM media queries show a meaningful change. Per viewport: screenshot plus layout metrics (`pageInfo()`, element boxes). Do not screenshot every 100 pixels.

## Interaction states

Capture a state as rendered HTML plus a screenshot: navigation open, dropdown, modal, hover, focus, selected tab, accordion, mobile menu. Only states the question needs, non-destructive only. Name files by state (`dropdown-open.png`).

## JavaScript

Keep JavaScript responses in the raw archive. Do not reverse-engineer minified bundles by default; runtime behavior, DOM, and CSS are cheaper evidence. Open a bundle only for a specific implementation question that rendered evidence cannot answer.
