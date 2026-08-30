<!-- capsule-v2 -->
# Formatting and layout — does the file match Solidity PEP-8 rhythm?

**Source:** Solidity style §Code Layout. **Question:** Are indent, wraps, braces, and spacing diff-friendly at 120 columns?

## Layout seam
**Path/Symbol:** `.sol` contract files.
**Signature:** 4-space indent; ≤120 cols; SPDX + pragma header; imports at top.
**Data Shape:** two blank lines between contracts; one between functions.

### Decisive pattern
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Owned} from "./Owned.sol";

contract TokenVault {
    mapping(address => uint256) private _balances;

    function deposit(uint256 amount) external {
        _balances[msg.sender] += amount;
    }

    function balanceOf(address account) external view returns (uint256) {
        return _balances[account];
    }
}
```

**Flow:** use 4 spaces per level — never tabs → wrap lines >120 with first arg on its own line, one indent level, one arg per line, closing `);` alone on final line → surround top-level contracts with two blank lines; separate functions with one blank line → keep imports immediately after pragma at file top → K&R braces: `{` same line as declaration, closing `}` aligned with opener, single space before `{` → `if (cond) {` / `for (...)` spacing; put `else`/`else if` on same line as closing `}` of prior block → short single-statement `if` may omit braces only when body is one line → function modifier order: visibility, mutability, virtual, override, custom modifiers → `mapping(uint => uint)` and `uint[]` without extra spaces → double-quoted strings; single space around operators (tighten only for precedence like `2**3`) → no alignment padding around `=` → no space inside `receive()`/`fallback()` parens.
**Invariant:** tabs, mid-file imports, dangling `else`, or alignment-column `=` padding fail layout review.
**Probe:** `forge fmt` / `prettier-plugin-solidity`; `grep $'\t'`; line-length spot check.

## Wrap seam
**Flow:** multiline calls, events, returns, and constructor bases follow same wrap rules as function args.
**Invariant:** multiple args on one wrapped line or closing paren sharing a line with last arg fails wrap review.
**Probe:** visual scan of long `emit`, `returns (...)`, and base-constructor lists.

## Verdict
Four-space, 120-col wraps, SPDX header, import-top, K&R braces, operator spacing. Learning note: `solidity-style-learning-note.md`.
