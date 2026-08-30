# Solidity style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `solidity-style-*.md` capsules, `solidity-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Solidity Style Guide](https://docs.soliditylang.org/en/latest/style-guide.html) — Code Layout, Order of Layout, Naming, NatSpec (primary) | 4-space indent; 120 cols; SPDX+pragma+import order; contract element order; function visibility order; modifier order; mixedCase/CapWords/UPPER_CASE; `_` prefix for internal; NatSpec on public ABI |
| [Solcurity Standard](https://github.com/transmissions11/solcurity) (secondary) | checks-effects-interactions; visibility/immutability; reentrancy; external calls; SWC refs; events/indexing; SPDX; named imports; Slither/fuzz; DeFi oracle/token edges |

**Scope:** Solidity ≥0.8 contracts (Foundry/Hardhat). Project style guides override when stricter. Solcurity is a review checklist, not a formatter.

## Mental model

Solidity quality is **consistent layout + explicit visibility + security-aware effects ordering**:

1. **Formatting** — 4 spaces, 120 cols, wrapped args, K&R braces, blank-line rhythm.
2. **Naming/NatSpec** — CapWords contracts, mixedCase functions/vars, UPPER_CASE constants; NatSpec on public interface.
3. **Structure** — file/contract element order; constructor→receive→fallback→external→public→internal→private; `_` on non-external API.
4. **Security/verify** — Solcurity V/F/C/X/T/P probes; CEI; no `tx.origin`; SafeERC20; Slither + tests.

## Decision tables

### Code layout

| Topic | Rule |
|---|---|
| Indent | 4 spaces; no tabs |
| Line length | ≤120 chars; one arg per wrapped line; `);` alone on last line |
| Blank lines | 2 between top-level contracts; 1 between functions |
| Imports | top of file after pragma; named imports grouped (Solcurity T10–T11) |
| Braces | open same line; close aligned; space before `{` |
| Control | `if (cond) {` spacing; `else` on same line as prior `}` |
| Functions | visibility → mutability → virtual → override → modifiers |
| Mappings/arrays | `mapping(uint => uint)`; `uint[]` (no space before `[`) |
| Strings | double quotes |
| Operators | single space; precedence may tighten (`2**3`, `2*y`) |

### File & contract order

| Level | Order |
|---|---|
| File | pragma → import → events → errors → interfaces → libraries → contracts |
| Contract | types → state → events → errors → modifiers → functions |
| Functions | constructor → receive → fallback → external → public → internal → private; view/pure last in group |

### Naming

| Entity | Convention |
|---|---|
| Contracts/libraries | CapWords; filename matches core contract |
| Structs/events/enums | CapWords |
| Functions/args/locals/state | mixedCase |
| Constants | UPPER_CASE_WITH_UNDERSCORES |
| Modifiers | mixedCase |
| Internal/private | `_leadingUnderscore` on functions and state |
| Collision | `trailingUnderscore_` when name clashes |
| Avoid single-letter | `l`, `O`, `I` |

### NatSpec

| Case | Rule |
|---|---|
| Public ABI | `@notice`/`@dev`/`@param`/`@return` on exports |
| Contract header | `@title`, `@author`, interaction `@dev` (Solcurity T6/T12) |
| Why comments | document CEI locks, unchecked, precision loss (Solcurity C39–C48) |

### Solcurity highlights (review probes)

| Area | Key checks |
|---|---|
| Variables | explicit visibility; prefer immutable/constant; pack slots (V1–V10) |
| Functions | external when possible; CEI (F6); bounds on params (F5); no `owner==0` init (F17) |
| Modifiers | no storage writes except reentrancy lock (M1); no external calls (M2) |
| Code | 0.8 math (C1); no unbounded loops (C3); no `tx.origin` (C32); SafeERC20 (C27); EIP-712 (C11) |
| External calls | reentrancy path (X3–X4); phantom functions (X8) |
| Events | index actors/ids; no dynamic index (E1–E5) |
| Contract | SPDX (T1); linear inheritance (T3); receive for ETH (T4) |
| Project | unit+fuzz+Slither (P2–P5) |

## Anti-patterns

- Tabs or mixed tab/space indent
- Imports mid-file
- Wrong function visibility order
- Modifier order scrambled (`override view` vs `view override`)
- `mapping (uint => uint)` spacing
- Single-quoted strings as default
- Public/internal functions without visibility rethink
- Missing `_` when promoting internal → external
- `else` on new line after `if` block
- Alignment padding around `=`
- Space inside `receive ()` / `fallback ()`
- Missing SPDX license identifier
- `transfer`/`send` for ETH (prefer `.call{value:}("")`)
- `tx.origin` authorization
- Storage update after external call (CEI violation)
- `assert` for user input validation
- Unbounded loop over user-controlled array
- Spot AMM price as oracle (DeFi D3)
- Missing NatSpec on public functions
- Wildcard imports without named symbols
- Bug fix without regression/fuzz test

## Skill trace

| Artifact | Role |
|---|---|
| `solidity-style-formatting-layout.md` | indent, wraps, braces, spacing |
| `solidity-style-naming-natspec.md` | CapWords/mixedCase, NatSpec ABI |
| `solidity-style-contract-structure.md` | file/contract order, visibility ladder |
| `solidity-style-security-verify.md` | Solcurity CEI/calls/events/tooling |
| `solidity-coding-practices/SKILL.md` | formatter + Slither/foundry in CI |
