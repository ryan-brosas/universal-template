<!-- capsule-v2 -->
# Contract structure — is visibility order and file layout scannable?

**Source:** Solidity style §Order of Layout, §Order of Functions; Solcurity T3/T9/T10/T11. **Question:** Can a reader find constructor, receive/fallback, and external entrypoints without hunting?

## Structure seam
**Path/Symbol:** contract/library/interface units in `.sol` files.
**Signature:** pragma→import→types; in-contract: types→state→events→errors→modifiers→functions.
**Data Shape:** visibility ladder with view/pure last per group.

### Decisive pattern
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {Owned} from "./Owned.sol";

error InsufficientBalance(uint256 requested, uint256 available);

contract Vault is Owned {
    struct Position {
        uint128 amount;
        uint128 lockedUntil;
    }

    IERC20 public immutable token;
    mapping(address => Position) private _positions;

    event Deposited(address indexed account, uint256 amount);

    modifier onlyPositive(uint256 amount) {
        require(amount > 0, "zero");
        _;
    }

    constructor(IERC20 token_) {
        token = token_;
    }

    receive() external payable {}

    function deposit(uint256 amount) external onlyPositive(amount) {
        _positions[msg.sender].amount += uint128(amount);
        emit Deposited(msg.sender, amount);
    }

    function totalSupply() external view returns (uint256) {
        return token.totalSupply();
    }

    function _sync(address account) internal {
        // ...
    }
}
```

**Flow:** file order: pragma → imports (external deps first, blank line, then local; named imports per Solcurity T10–T11) → file-level events/errors/interfaces/libraries/contracts → inside contract: type declarations → state variables → events → errors → modifiers → functions → function groups: constructor → receive → fallback → external (state-changing, then view/pure) → public → internal → private → keep inheritance linear; mark `abstract` when base is incomplete (Solcurity T3/T7) → use explicit visibility on every function and state variable → when widening visibility internal→external, rename with `_` removal and review every call site (style guide underscore convention) → emit constructor-set events if mutators elsewhere emit for same field (Solcurity T8).
**Invariant:** constructor after externals, wildcard import blob, or deep diamond inheritance without documented reason fails structure review.
**Probe:** visibility-order walk; import grouping check; inheritance graph ≤2 levels preferred.

## Modifier seam
**Flow:** modifiers avoid storage writes except reentrancy guard; no external calls in modifiers (Solcurity M1–M2).
**Invariant:** modifier that mutates storage or calls out fails modifier review.
**Probe:** modifier body side-effect scan.

## Verdict
Canonical element order, visibility ladder, named grouped imports, linear inheritance. Learning note: `solidity-style-learning-note.md`.
