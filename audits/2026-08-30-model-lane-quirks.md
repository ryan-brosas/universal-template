# Model-lane quirks — dated machine observations (2026-08-30)

Runtime state; do not copy into tracked config or philosophy. Re-verify each
item after any version change (veda / pi / agy upgrades).

- Versions at observation: veda 0.75.9, pi 0.84.4, agy 2026.2.
- AGY Gemini lanes work via veda and via direct `agy -p`.
- AGY Claude models (claude-sonnet-4-6, claude-opus-4-6-thinking) reject
  `--effort` at any level (fixed thinking); the direct
  `agy --model <model> -p ...` invocation works while the veda lane injects
  effort and currently fails — resolve to the direct agy lane and re-verify
  on veda upgrades.
- claude-code backend installed but unauthenticated (/login required).
- github-copilot: auth-reported ready but functionally broken — removed from
  all chains; re-add only after it works.
- yolo-auto/qwen3.8-27b: spam-safe lane (owner-approved, no rate concern).
- pi provider readiness is environment-scoped — check per lane.
- Catalog context columns are base-tier values: an active Pro subscription
  can raise the effective window (owner-confirmed 256K on
  yolo-auto/qwen3.8-27b vs 131.1K listed). Owner-confirmed effective limits
  override catalog numbers for context budgeting.
