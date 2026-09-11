<!-- capsule-v2 -->
# Branch naming — how should a feature branch read in `git branch -a`?

**Source:** agis/git-style-guide CC BY 4.0; catalog `AGENTS.md`. **Question:** What branch name lets reviewers infer intent without opening the diff?

## Branch identity seam
**Path/Symbol:** workflow convention (no single file).
**Signature:** `git checkout -b <name>` before first push.
**Data Shape:** lowercase ASCII, hyphens between words, optional ticket prefix; ≤3 hyphen segments in catalog default.

### Decisive examples
```shell
git checkout -b oauth-migration          # good — intent clear
git checkout -b issue-15                   # good — tracker id
git checkout -b feature-a/alice            # good — personal under team branch
git checkout -b New_Feature                # bad — case/underscore noise
```

**Flow:** name from ticket or feature → push `-u origin` → delete remote after merge (`git branch --merged` on main).
**Invariant:** branch name is the first line of history metadata — vague names (`fix`, `updates`) fail review triage.
**Probe:** `git branch --show-current` matches project regex; PR title/body references same intent.

## Verdict
Adopt short lowercase hyphen names; adapt ticket prefix format to tracker; omit slashes unless team uses shared feature branches. Learning note: `git-style-learning-note.md`.
