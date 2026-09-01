---
name: solidity-coding-practices
description: "Use when authoring or reviewing Solidity, official layout/naming, NatSpec ABI docs, contract structure, Solcurity CEI/external-call checks, forge fmt/test and Slither in CI."
disable-model-invocation: true
---

# Solidity Coding Practices

Application skill for official Solidity style + Solcurity (archived `awesome-guidelines` capsules). Project-specific guides override when stricter.

## Core Principle

Solidity quality is **consistent layout + documented public API + security-aware effects ordering**, CapWords types, mixedCase members, visibility ladder, CEI on value paths.

## When to Use / NOT

- Smart contracts (Foundry/Hardhat/Truffle), libraries, interfaces, upgradeable proxies.
- Setting up `forge fmt`, NatSpec, Slither, fuzz tests, named imports.

**NOT when:**

- Vyper/Move/Cairo, different language guides.
- Generated ABI bindings only, validate generators, not hand-style rules.

## Workflow

1. **Formatting**, indent, wraps, braces (`solidity-style-formatting-layout.md`).
2. **Naming/NatSpec**, CapWords/mixedCase, public docs (`solidity-style-naming-natspec.md`).
3. **Structure**, file/contract order, visibility ladder (`solidity-style-contract-structure.md`).
4. **Security**, Solcurity CEI/calls/events (`solidity-style-security-verify.md`).
5. **Verify**, `forge fmt`/`forge test`, Slither on changed contracts.

## Red Flags

- Tab characters or mixed tab/space
- Lines >120 without wrap
- Imports mid-file or wildcard-only imports
- Missing SPDX license identifier
- Contract filename mismatch (lowercase file, CapWords type)
- Wrong function order (externals before constructor)
- Modifier order wrong (`override view` vs `view override`)
- `mapping (uint => uint)` or `uint []` spacing
- Single-quoted strings by default
- `else` on new line after `if` block
- Alignment padding around `=`
- Space inside `receive ()` / `fallback ()`
- Missing `_` on internal/private helpers
- External function promoted from internal without call-site review
- Missing NatSpec on new public/external API
- Storage update after external call (CEI violation)
- `tx.origin` for authorization
- `transfer`/`send` for ETH payouts
- Unchecked ERC20 return values
- `assert` for user-input validation
- Unbounded loop over user-controlled length
- Modifier with storage writes (except reentrancy lock) or external calls
- Dynamic type indexed in events
- Deep inheritance diamond without documented reason
- Spot AMM price used as oracle
- Bug fix without unit/fuzz regression
- Slither findings ignored without documented rationale

## Verification

- `forge fmt --check` (or prettier-plugin-solidity) on changed `.sol`
- `forge test` / project test runner on touched contracts
- NatSpec coverage spot-check on new externals
- Visibility-order and import-group walk
- Slither (or Solhint) on PR diff
- Capsule checklist: CEI on value-moving functions


## References

- `awesome-guidelines/references/solidity-style-learning-note.md`
- `awesome-guidelines/references/solidity-style-formatting-layout.md`
- `awesome-guidelines/references/solidity-style-naming-natspec.md`
- `awesome-guidelines/references/solidity-style-contract-structure.md`
- `awesome-guidelines/references/solidity-style-security-verify.md`
