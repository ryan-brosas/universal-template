# Install the optional CodeRabbit integration

The CLI and agent skills are separate. An installed, authenticated CLI needs no
second installation. Check live help before choosing setup or review commands.
See [official CLI documentation](https://docs.coderabbit.ai/cli) for supported
installation and authentication; do not print tokens or install silently.

## Selective repository-local installation

From the intended repository root, after checking for existing destinations:

```sh
npx skills add coderabbitai/skills --skill code-review --agent pi --copy -y
```

The inspected installer writes the vendor skill under `.pi/skills/code-review/`
and records its source in `skills-lock.json`. Review its installation summary;
other hosts or installer versions may use different destinations. Do not pass
`--global` or `--all` unless that broader scope is explicitly requested.

Keep the installed vendor skill cold by setting these frontmatter fields in its
local `SKILL.md`, without rewriting its body:

```yaml
invocation: vendor
disable-model-invocation: true
```

Pi honors the hidden flag; other hosts need verified visibility behavior or a
filtered skill view. Preserve the upstream license with local copies. Installer
updates may replace metadata: inspect the updated content and reapply the cold
visibility policy before exposing it. Do not publish machine-local vendor files.
The installer lock is source provenance, not a project component or skill registry.

Use the first-party `coderabbit-review` skill or the `coderabbit` prompt as the
explicit entry point. Prompt availability follows the host’s configured prompt
mounts; use its normal reload/new-session mechanism after installation.

## Why not install everything?

The reviewed upstream `code-review` description claims generic and autonomous
review ownership. Its `autofix` skill prescribes per-change approvals and a single
summary comment rather than this template’s in-thread replies and resolution.
Keep the existing PR owner; do not silently make either vendor skill the default
review workflow. `coderabbit skills` installs every skill in its verified release,
so it is broader than the selective command above.

Source inspected: [coderabbitai/skills at aa49953](https://github.com/coderabbitai/skills/tree/aa49953c4cb2590e35480637b1b6a29cf4187cfa),
MIT-licensed. CLI 0.7.6 help exposed `--agent`, `--committed`, and `--uncommitted`,
while that upstream revision still showed `-t`. Live CLI help owns the current
contract. Installation/readiness checks do not establish review quality or authorize
an external code submission.
