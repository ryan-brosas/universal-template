<!-- capsule-v2 -->
# Git workflow and documentation — do branches, commits, and README match elsewhen project guidelines?

**Source:** project-guidelines §1 Git, §2 Documentation, §11 Licensing. **Question:** Is collaboration isolated in feature branches with documented, maintained project context?

## Git seam
**Path/Symbol:** repo default branch workflow, PR process.
**Signature:** feature branch from develop; rebase; PR; protected mainlines.
**Data Shape:** 50/72 imperative commits; delete merged branches.

### Decisive pattern
```text
git checkout develop && git pull
git checkout -b feature/add-checkout
# … commits …
git rebase -i develop && npm test && npm run lint
git push --force-with-lease && open PR
```

**Flow:** work in **feature branch** branched from **`develop`** — never push directly to **`develop`/`master`** → **rebase** onto latest develop before PR; resolve conflicts locally → PR only after **build + tests + lint** pass → **commit messages**: ≤50 char imperative subject, 72-wrap body explaining **what/why** → delete **local/remote feature branch** after merge → **protect** develop and master → use project **`.gitignore`** template.
**Invariant:** direct push to protected mainline or PR with failing lint/tests fails project workflow review.
**Probe:** branch protection settings; CI required checks on PR; sample commit message format.

## Documentation seam
**Flow:** scaffold **`README.md`** from **README.sample.md** (install, dev, build, test, style, API, license) → keep README **updated** as project evolves → **comment** non-obvious intent; link GitHub/Stack Overflow discussions → remove **commented-out code** and stale comments → comments complement, not replace, clean code → verify **license** and asset rights (MIT/Apache/BSD for deps).
**Invariant:** empty/default README on active project or license-incompatible assets fail docs review.
**Probe:** README sections vs sample; grep large commented blocks; LICENSE file present.

## Verdict
Feature-branch PR workflow, disciplined commits, living README, intentional comments. Learning note: `js-project-learning-note.md`.
