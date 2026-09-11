<!-- capsule-v2 -->
# Prerelease-blind version compare — how do you compare semver-ish version strings numerically without a semver library, and what must callers guard themselves?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** Why is `isOutdated` deliberately prerelease-blind, and where is the null contract enforced?

## normalizeVersion / getMajorVersion / isOutdated — strip, split, numeric-walk
**Path/Symbol:** `apps/web/src/features/instance-settings/utils.ts` (whole, 37L): `normalizeVersion` (lines 10–12), `getMajorVersion` (lines 14–18), `isOutdated` (lines 23–36). Consumers: `service.ts:getUpdateStatus` only.
**Signature:** `getMajorVersion(version: string) → number | null`; `isOutdated(current: string, latest: string) → boolean`.
**Data Shape:** versions like `v4.5.1`, `5.0.0-beta.1`, `unknown`, `""` are all valid inputs; malformed input is a return value (`null`), never a throw.

### Decisive source
```ts
function normalizeVersion(version: string) {
  return version.replace(/^v/, "").split(/[-+]/)[0];
}
export function getMajorVersion(version: string) {
  const normalized = normalizeVersion(version);
  if (!/^\d+(\.\d+){0,2}$/.test(normalized)) return null;
  return Number(normalized.split(".")[0]);
}
// Compares release numbers only — prerelease/build suffixes are ignored, so
// "4.2.0-beta.1" is not outdated relative to "4.2.0". Callers that must not
// cross majors need to guard with getMajorVersion themselves.
export function isOutdated(current: string, latest: string) {
  const a = normalizeVersion(current).split(".").map((n) => Number(n) || 0);
  const b = normalizeVersion(latest).split(".").map((n) => Number(n) || 0);
  const len = Math.max(a.length, b.length);
  for (let i = 0; i < len; i++) {
    const ai = a[i] ?? 0;
    const bi = b[i] ?? 0;
    if (ai !== bi) return ai < bi;
  }
  return false;
}
```

**Flow:** both sides strip the leading `v` and everything from the first `-` or `+` → component-wise numeric walk padded with zeros to the longer side (`4.9 < 4.10` because comparison is NUMERIC, not lexicographic; missing components count as 0) → first difference decides, equality means not-outdated. `getMajorVersion` adds a strict whole-string regex so garbage like `4foo` / `4.5x` returns null instead of a truncated number. The update service layers the two: within-major needs `getMajorVersion(latest) === currentMajor` BEFORE trusting `isOutdated`.
**Invariant:** two documented sharp edges. (1) Prereleases sort EQUAL to their release — correct here ("is my channel's latest newer than me" ignores channel), wrong if you need semver pre-release ordering; the doc-comment pushes major-crossing duty onto callers because `isOutdated("4.2.0", "5.0.0") === true`. (2) `Number(n) || 0` silently maps non-numeric components to 0 — acceptable only because `getMajorVersion`'s strict regex gates the security-relevant path; `isOutdated` alone is a heuristic, not a validator.
**Probe:** direct test `apps/web/src/features/instance-settings/utils.test.ts` (whole, 52L): tagged/untagged extraction (:5–11), prerelease-ignores (:13–15, :49–51), `4foo`/`4.5x → null` (:22–25), numeric `4.9.0 < 4.10.0` (:33–35), cross-major true (:45–47). Runner caveat: vitest unavailable in checkout — assertions read directly at pin.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "getMajorVersion isOutdated normalizeVersion", limit: 10 });
```

## Verdict
Adopt when you need dependency-free "am I behind?" checks against release tags; adapt the regex looseness (1–3 components accepted) to your tagging scheme; omit entirely in favor of a real semver lib if you must order prereleases or enforce ranges. If you port it, port its TESTS too — the null-on-garbage and numeric-ordering cases are exactly the ones a naive `split('.')+parseInt` rewrite gets wrong.
