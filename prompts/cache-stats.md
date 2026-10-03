---
description: Report prompt cache hit rate and miss sources
argument-hint: "[days | target]"
---
Report the prompt cache rate for the requested window, defaulting to the last 7
days. Run:

`bash ~/.agents/knowledge/playbooks/prompt-cache-efficiency/check-cache.sh --days 7`

Treat a numeric argument as the day window (for example `30` becomes
`--days 30`); treat a percentage argument as the target to compare against.
Report the overall cached-input percentage, the current miss total against the
98% and 99% budgets, and the per-model rates. Read
[prompt cache efficiency](../knowledge/playbooks/prompt-cache-efficiency/README.md)
for the method before recommending workflow changes. Do not edit configuration
or instructions just to move the number.

${ARGUMENTS:-}
