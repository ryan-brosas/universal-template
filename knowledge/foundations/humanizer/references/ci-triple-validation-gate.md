<!-- capsule-v2 -->
# ci-triple-validation-gate — which three independent checks gate a prompt-only repo in CI?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** What does minimal-but-sufficient CI look like for a repository whose entire product is Markdown plus two manifests?

## Three validators, one job, read-only permissions
**Path/Symbol:** `.github/workflows/validate.yml` whole file (:1–29); companion pre-publish checklist in `AGENTS.md` :27.
**Signature:** n/a — workflow YAML; one job `check` on `ubuntu-latest`.
**Data Shape:** Triggers: every pull_request + push to main. Permissions: `contents: read` (nothing in the pipeline writes). Toolchain: Node 22 + Python 3.12 setup actions.

### Decisive source
```yaml
      - name: Check package files
        run: python3 scripts/validate-package.py
      - name: Check skill discovery
        run: npx --yes skills@1.5.20 add . --list
      - name: Check Claude marketplace
        run: |
          npm install --global @anthropic-ai/claude-code
          claude plugin validate .
```
(:22–29. Three INDEPENDENT authorities: the repo's own zero-dep validator, the ecosystem's discovery CLI at a PINNED version, and Claude's own manifest validator.)

**Flow:** checkout → set up Node/Python → run the in-repo consistency gates (versions, layout, numbering, rules, budget) → ask the skills.sh CLI (`skills add . --list`, pinned to 1.5.20 so a CLI behavior change can never silently redefine discovery) to enumerate what it discovers from this repo → install claude-code globally and run its manifest validator against the plugin/marketplace JSON. AGENTS.md :27 mirrors the same trio as the manual pre-publish checklist, so local and CI verification are identical commands.

**Invariant:** A merge requires agreement between self-authored checks AND the external loaders that will actually consume the package; version-pinning external tooling is deliberate supply-chain discipline for a repo with no lockfile of its own. Least-privilege permissions because nothing here needs write access.

**Probe:** Deterministic probes executed: direct read of validate.yml whole pins all three steps verbatim; step 1 (`python3 scripts/validate-package.py`) executed live in-lane with exit 0 and sentinel output — steps 2–3 require network installs (npx skills / @anthropic-ai/claude-code) and were NOT executed in the read-only lane; recorded as an honest partial-execution caveat rather than a claimed pass.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", qn_pattern: "validate" })
```
(matches `humanizer..github.workflows.validate.yml.__file__` among File nodes.)

## Verdict
Adopt the three-authority shape for any prompt-as-product repo: (1) your own dependency-free consistency script, (2) the real discovery/loader CLI pinned to an exact version run against the repo itself, (3) each target host's own validator. Adopt `--list`-style dry runs as the non-mutating way to test installers. Adapt tool names/pins to your hosts. Omit build/test matrices — there is no build step, and pretending otherwise adds no safety.
