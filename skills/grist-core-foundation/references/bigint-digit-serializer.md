<!-- capsule-v2 -->
# Digit-base BigInt serializer — how do >2^53 integers survive JS→Python marshalling without a bignum library?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What minimal representation converts huge ints to decimal strings (or safe numbers) in ~70 lines?

## Digits array + repeated mod/divide by radix; toNative() prefers Number when lossless
**Path/Symbol:** `app/common/BigInt.ts`: whole file (:11–72): ctor contract (:11–16), `toNative` (:21–24), `toString(radix=10)` (:38–47), `_mod` (:50–58), `_divide` (:61–71).
**Signature:** `new BigInt(base: number, digits: number[], sign: 1|-1)` — digits LEAST-significant first, each in `[0, base)`.
**Data Shape:** Pure value class; no arithmetic beyond div/mod needed for serialization.

### Decisive source
```ts
public toString(radix: number = 10): string {
  const copy = this.copy();                 // _divide mutates: work on a copy
  const decimals = [];
  while (copy._digits.length > 0) {
    decimals.push(copy._mod(radix).toString(radix));
    copy._divide(radix);
  }
  if (decimals.length === 0) return "0";    // zero has NO digits
  return (this._sign < 0 ? "-" : "") + decimals.reverse().join("");
}
private _mod(divisor: number): number {
  let res = 0; let baseFactor = 1;
  for (const digit of this._digits) {
    res = (res + (digit % divisor) * baseFactor) % divisor;
    baseFactor = (baseFactor * this._base) % divisor;   // mod at EVERY step: no overflow
  }
  return res;
}
```

**Flow:** consumers (marshalling of BigInt cell values crossing the sandbox pipe) hold the digit representation → `toNative()` returns a Number iff `Number.isSafeInteger`, else the base-10 string → strings are what Python's int() ingests. `_divide` carries remainders downward (`digits[i-1] += (digits[i] % divisor) * base`) then pops drained high-order zeros so the while-loop terminates.
**Invariant:** The zero case is structural: an empty digits array must render "0", not "" — and `_divide` MUST pop leading (most-significant) zeros or the loop never ends. Every multiply accumulates under `% divisor` because intermediate `base^n` overflows doubles long before the value does. Sign lives OUTSIDE the digits (magnitude-only), so negation never touches the array.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -cF "decimals.length === 0" app/common/BigInt.ts && sed -n "7,10p" test/common/BigInt.ts'` → exactly 1 zero-guard; test title "should represent and convert various numbers correctly".
Direct tests: `test/common/BigInt.ts` :6–22 (round-trips incl. unsafe magnitudes).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"BigInt digits base toString toNative","limit":4,"detail":"ids"}'
```

## Verdict
Adopt as-is for wire-format conversion; adapt if your host has native BigInt64 semantics (then this class may be redundant); omit the copy-on-toString only if you accept destructive reads.
