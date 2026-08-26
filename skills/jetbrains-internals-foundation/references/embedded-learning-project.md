<!-- capsule-v2 -->
# Embedded learning project — how is an interactive tutorial shipped as a real git repo inside a jar?

**Source:** JetBrains IDE distributions (proprietary distribution); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How does an IDE ship a hands-on tutorial as a self-contained git repository with YAML lesson metadata, and what does the lesson format look like?

## Connected graph-selected seam
**Path/Symbol:** `pycharm/plugins/featuresTrainer/lib/git-learning-project.jar:learnProjects/GitProject/` — 1,072 entries, ~1,070 under `.git/` (a real embedded repo: packed-refs, objects/, HEAD).
**Signature:** lesson files `sphinx_cat.yml`, `simple_cat.yml`, `puss_in_boots.yml`, `martian_cat.yml` + `.gitignore`; the rest is a functioning git object store so the IDE can reset/checkout the tutorial state.
**Data Shape:** each `.yml` is a YAML object describing a task: `cat:` with fields `name`, `gender`, `breed`, `personality_type`, `fur_type`, `fur_pattern`, `fur_colors[]`, `tail_length`, `eyes_colors[]`, plus numeric invariants (`eyes_number: 2`, `ear_number: 2`, `paws_number: 4`), `favourite_things[]`, and a `behavior:` list of `- <verb>:` with `condition:` + `actions[]`.

### Decisive source
```yaml
cat:
  name: Oreshek
  breed: mongrel
  personality_type: skittishness
  fur_pattern: solid
  fur_colors: [ black ]
  eyes_number: 2
  ear_number: 2
  paws_number: 4
  favourite_things:
    - bunch of candy wrappers
  behavior:
    - eat:
        condition: want to eat
        actions: [quietly ask for food]
```

**Flow:** featuresTrainer plugin loads `learnProjects/<Project>/` from the jar → reads lesson YAML → presents tasks against the embedded working tree → user edits files in the repo → the trainer verifies against the git baseline (reset available because the full object store ships).
**Invariant:** the tutorial is a REAL git repo, not a snapshot — shipping the object store is what makes "reset to start" and per-step verification possible without network. Lesson YAML uses a fixed entity schema (attributes + numeric invariants + behavior rules).
**Probe:** `unzip -l plugins/featuresTrainer/lib/git-learning-project.jar | awk '{print $4}' | grep -c '\.git/'` → ~1072; `unzip -p … learnProjects/GitProject/simple_cat.yml | head -3`.
**Coverage caveat:** resource plane; direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "features trainer lesson learn project", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: embed a real git repo as the tutorial substrate, YAML lesson schema with entity attributes + invariants + behavior rules, reset-from-object-store for step replay. Adapt lesson schema to your domain. Omit the cat-themed sample content. Complements pass-2's tips-and-help-surface (passive tips vs this active hands-on repo).
