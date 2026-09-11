<!-- capsule-v2 -->
# Variant-table callout — how do I ship one banner component that covers success/info/warn/error/neutral without a variant prop explosion?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What is the minimal data shape of a multi-variant notice component, and how do warn vs error differ?

## Callout
**Path/Symbol:** `apps/web/ui/shared/callout.tsx:Callout` (33–64); variants table 5–31.
**Signature:** `Callout({variant?: keyof typeof calloutVariants = "neutral"; size?: 1 | 2 = 2; className?; children}: PropsWithChildren<…>)`.
**Data Shape:** five rows of `{icon: Icon, containerClassName, iconClassName}`; container base = `flex items-start gap-2.5 rounded-[10px] border text-sm font-normal` + size padding (`px-4 py-3` for size 2, `px-3 py-2` for size 1).

### Decisive source
```tsx
const calloutVariants = {
  success: { icon: CircleCheck,   containerClassName: "border-green-200 bg-green-50 text-green-900",  iconClassName: "text-green-600" },
  info:    { icon: CircleInfo,    containerClassName: "border-blue-200 bg-blue-50 text-blue-900",      iconClassName: "text-blue-600" },
  warn:    { icon: TriangleWarning, containerClassName: "border-amber-200 bg-amber-50 text-amber-900", iconClassName: "text-amber-600" },
  error:   { icon: TriangleWarning, containerClassName: "border-red-200 bg-red-50 text-red-900",       iconClassName: "text-red-600" },
  neutral: { icon: CircleInfo,    containerClassName: "border-neutral-200 bg-neutral-50 text-neutral-900", iconClassName: "text-neutral-600" },
};
```

**Flow:** variant lookup → icon + color triad applied → children in `min-w-0` wrapper (long content truncates instead of overflowing) → fixed-height icon column keeps multi-line rows aligned.
**Invariant:** warn and error share the SAME icon (TriangleWarning) and differ ONLY by palette — porters who add a second icon break upstream visual parity; text color is set on the CONTAINER (children inherit), not per-element; `min-w-0` on the content div is load-bearing inside flex.
**Probe:** `grep -c 'border-' apps/web/ui/shared/callout.tsx` → **5** (one border class per variant row); `grep -c 'TriangleWarning' apps/web/ui/shared/callout.tsx` → **3** (import + warn + error rows).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "Callout calloutVariants", limit: 5 });
```

## Verdict
Adopt the flat variant-table shape (icon + two class strings per row); adapt palette tokens to your design system; omit size prop if you only need one density. Product-shell component — no direct tests; probe pins are the evidence class.
