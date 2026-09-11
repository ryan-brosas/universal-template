<!-- capsule-v2 -->
# Security and verification — does Solcurity + tooling back CEI and external-call discipline?

**Source:** Solcurity Standard; Solidity security community practice. **Question:** Are value paths checks-effects-interactions guarded, tested, and statically analyzed?

## Effects seam
**Path/Symbol:** functions moving ETH/tokens or calling external contracts.
**Signature:** validate → update storage → external call; reentrancy lock documented.
**Data Shape:** explicit bounds checks; SafeERC20; no `tx.origin`.

### Decisive pattern
```solidity
function withdraw(uint256 amount) external nonReentrant {
    require(amount > 0 && amount <= _balances[msg.sender], "bad amount");

    _balances[msg.sender] -= amount;
    (bool ok, ) = msg.sender.call{value: amount}("");
    require(ok, "transfer failed");
}
```

**Flow:** follow checks-effects-interactions on every value path (Solcurity F6) → validate parameters even for trusted callers (F5) → prefer `external` over `public` when not called internally (F1) → set visibility/immutability/constant explicitly (V1–V4) → no `tx.origin` auth (C32); no `transfer`/`send` for ETH — use `.call{value:}("")` with success check (C33) → use SafeERC20 or check ERC20 return (C27) → no unbounded loops over user arrays (C3) → multiply before divide unless overflow risk (C24) → document reentrancy locks (C48) → external calls: assume reentrancy (X3–X4), check success, handle phantom functions (X8) → events: index actors/ids; avoid indexing dynamic strings/bytes (E1–E5) → SPDX at file top (T1); fuzz/unit test state invariants (F11–F12, P2–P3) → run Slither/Solhint and triage findings (P5).
**Invariant:** storage write after external call without guard, missing return check on low-level call, or spot AMM oracle use fails security review.
**Probe:** CEI ordering audit; Slither reentrancy/unused-return; Foundry/Hardhat test + fuzz on changed paths.

## DeFi/token seam
**Flow:** document unsupported rebasing/fee-on-transfer/decimal edge tokens; sanity bounds on oracle inputs (D1–D11).
**Invariant:** raw `balanceOf(this)` share price without documented recovery path fails DeFi review.
**Probe:** token compatibility matrix in NatSpec; oracle manipulation tests.

## Project verify seam
**Flow:** threat-model pass → line review → actor review → coverage gap review → static analysis (Solcurity general approach).
**Invariant:** storage-mutating PR without test delta fails verify gate.
**Probe:** `forge test` / `npm test`; coverage diff; Slither CI artifact.

## Verdict
CEI ordering, safe ETH/ERC20 calls, indexed events, SPDX, tests+fuzz+Slither on touched contracts. Learning note: `solidity-style-learning-note.md`.
