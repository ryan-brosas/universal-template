<!-- capsule-v2 -->
# Naming and NatSpec — does the ABI read like mixedCase + documented exports?

**Source:** Solidity style §Naming Conventions, §NatSpec; Solcurity V5/F15/T6/T12. **Question:** Can reviewers infer role from names and NatSpec without opening bodies?

## Naming seam
**Path/Symbol:** contracts, libraries, functions, state, events.
**Signature:** CapWords types; mixedCase members; UPPER_CASE constants; `_` internal prefix.
**Data Shape:** `Congress.sol` ↔ `contract Congress`; library `self` first arg.

### Decisive pattern
```solidity
/// @title Simple token ledger
/// @notice Tracks balances and emits transfer events
contract SimpleToken {
    uint256 public constant MAX_SUPPLY = 1_000_000e18;

    mapping(address => uint256) private _balances;

    event Transfer(address indexed from, address indexed to, uint256 amount);

    /// @notice Move tokens to `to`
    /// @param to Recipient account
    /// @param amount Units to send
    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        _balances[from] -= amount;
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }
}
```

**Flow:** name contracts/libraries CapWords matching filename (`Owned.sol` / `Owned`) → structs, events, enums CapWords → functions, args, locals, state mixedCase → constants ALL_CAPS → modifiers mixedCase → prefix non-external functions and internal state with `_`; use trailing `_` only on intentional name collisions → never use `l`, `O`, or `I` as one-letter names → library ops on custom struct: first arg named `self` → annotate entire public ABI with NatSpec (`@notice`, `@dev`, `@param`, `@return`) → contract-level `@title` and interaction `@dev` per Solcurity T6/T12 → comment why for CEI locks, unchecked blocks, precision loss (Solcurity C39–C48).
**Invariant:** lowercase contract filename, missing NatSpec on new external function, or external-facing helper without `_` review when visibility changes fails naming review.
**Probe:** export list vs NatSpec coverage; internal `_` grep on private helpers.

## NatSpec seam
**Flow:** triple-slash above declarations; document side effects and trust assumptions on value-moving functions.
**Invariant:** public/state-changing function without `@notice`/`@param` fails ABI doc review.
**Probe:** missing `@notice` on external/public mutators checklist.

## Verdict
CapWords types, mixedCase API, `_` internal boundary, full public NatSpec. Learning note: `solidity-style-learning-note.md`.
