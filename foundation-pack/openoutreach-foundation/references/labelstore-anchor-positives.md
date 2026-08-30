<!-- capsule-v2 -->
# LabelStore with anchor positives — how does a co-occurrence walk bootstrap when nothing has been accepted yet?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** Node expansion only offers tokens that shared a *qualified* profile with the node — what happens on a campaign with zero acceptances, and how is that loop broken?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/pipeline/select.py:LabelStore.load` (:107-163), `counts` (:192-207), `cooccurring` (:209-227).
**Signature:** `LabelStore.load(campaign) -> LabelStore`; `counts(pairs) -> (a, b)`; `cooccurring(pairs, candidates) -> list[(field, token)]`.
**Data Shape:** in-memory list of `(frozenset[str] tokens, int label)`; verdict = 1 unless (state==FAILED and outcome==WRONG_FIT); anchors appended as label 1.

### Decisive source
```python
# load(): the anchors are what make the cold phase work at all
for profile in campaign.anchor_profiles or []:
    if profile:
        tokens.append(profile_tokens(profile))
        labels.append(1)                       # synthetic ideals count as positives
        anchors += 1

def counts(self, pairs):
    wanted = {token for _, token in pairs}
    for tokens, label in zip(self._tokens, self._labels):
        if wanted <= tokens:                   # field-agnostic subset test
            ...

def cooccurring(self, pairs, candidates):
    # candidate must appear alongside `pairs` in >=1 QUALIFIED profile:
    if label and wanted <= tokens: live |= tokens
    return [(f, t) for f, t in candidates if t in live and (f, t) not in set(pairs)]
```

**Flow:** load once per discovery pass → every node's a/b is a microsecond set-containment scan → expansion offers only co-occurring tokens.
**Invariant:** Without anchors the frontier cannot grow past its depth-1 seed nodes: expansion needs a qualified profile, a campaign with no acceptance has none, one-token queries matching millions of wrong people produce no acceptance — a closed loop. Synthetic ideal profiles (written in `profile_text`'s shape) break it and are counted permanently ("a small, constant nudge that matters early and is swamped by real evidence"). Anchors deliberately do **NOT** feed the vocabulary: an anchor is one flat string with no per-field structure, and guessing would file "united states" as a job title. The store is re-derived every pass instead of maintained as counters ("no counter anywhere to drift out of step with the labels").
**Probe:** `tests/test_select.py::TestAnchorsAsPositives` (:113-171), `TestLabelStore` (:55-112).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "LabelStore", limit: 5 });
```

## Verdict
Adopt: label store = token sets + verdicts rebuilt per pass; anchor/synthetic positives counted in evidence but excluded from per-field vocabularies; expansion gated on real co-occurrence (self-limits with depth, keeps every child a proposition the evidence can speak to). Adapt the verdict mapping to your outcome columns; omit the Django value_list plumbing.
