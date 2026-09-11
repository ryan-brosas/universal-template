# Install the optional CodeRabbit integration

The CLI and agent skills are separate. An installed, authenticated CLI needs no
second installation. Check live help before choosing setup or review commands.
See [official CLI documentation](https://docs.coderabbit.ai/cli) for supported
installation and authentication; do not print tokens or install silently.

## Selective repository-local installation

After approval to install and checking existing destinations, prepare the inspected
revision in a temporary source checkout. Do not rely on a moving branch name:

```sh
checkout=$(mktemp -d)
git clone --no-checkout https://github.com/coderabbitai/skills.git "$checkout"
git -C "$checkout" checkout --detach aa49953c4cb2590e35480637b1b6a29cf4187cfa
```

Verify that `git -C "$checkout" rev-parse HEAD` is exactly the requested commit,
the checkout is clean, and inspect its selected `skills/code-review/SKILL.md` and
`LICENSE` before copying. Stop on any mismatch.

Installer tested: `skills@1.5.23`, published from
[vercel-labs/skills](https://github.com/vercel-labs/skills). The downloaded
[package archive](https://registry.npmjs.org/skills/-/skills-1.5.23.tgz) matched:

```text
sha512-+hMNBSi35yfX0sKD+ZcRm9y5or7u313OdkcvrRvJAsAzGCaA8wRTu2OmVdN0KRbk9ybqKby5dijkn6OVvNTUmw==
```

Verify downloaded installer bytes against that integrity before first use, or
use a locally verified copy. Do not silently substitute a newer installer or
vendor revision; review and test an intentional update. This pin records package
identity and tested behavior, not a comprehensive security audit.

From the intended destination
repository root, install from that verified local checkout:

```sh
npx --yes skills@1.5.23 add "$checkout" --skill code-review --agent pi --copy -y
```

The inspected installer writes `.pi/skills/code-review/`. Verify the installed
body against the checked-out file before use and retain the upstream license with
the local copy. Review the installation summary: other hosts or installer versions
may use different destinations. A GitHub-source install may record provenance in
`skills-lock.json`; a local-path install may not. Neither replaces commit and
content verification. Do not use `--global` or `--all` without broader authorization.

Keep the vendor skill cold by adding these local frontmatter fields without
rewriting its body:

```yaml
invocation: vendor
disable-model-invocation: true
```

Pi honors the hidden flag; other hosts need verified visibility or a filtered
view. Updates may replace metadata: inspect the new revision and reapply the cold
policy before exposing it. Do not publish machine-local vendor files. Use the
first-party `coderabbit-review` skill or `coderabbit` prompt as the explicit entry
point; availability follows the host’s prompt mounts and reload mechanism.

## Why not install everything?

The upstream `code-review` description claims generic and autonomous review
ownership. Its `autofix` skill uses per-change approvals and a single summary
comment rather than this template’s in-thread replies and resolution. Keep the
existing PR owner. `coderabbit skills` installs every skill in its verified release,
so it is broader than the selective command above.

Source inspected: [coderabbitai/skills at aa49953](https://github.com/coderabbitai/skills/tree/aa49953c4cb2590e35480637b1b6a29cf4187cfa),
MIT-licensed. CLI 0.7.6 help exposed `--agent`, `--committed`, and `--uncommitted`,
while that upstream revision still showed `-t`. Live help owns the current
contract. Setup checks establish neither review quality nor upload authorization.
