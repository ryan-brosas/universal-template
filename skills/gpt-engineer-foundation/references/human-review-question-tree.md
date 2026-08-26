<!-- capsule-v2 -->
# human-review-question-tree — What Review shape does the terminal question tree produce, and how do skipped questions encode?

**Source:** gpt-engineer MIT `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory `gpt-engineer`. **Question:** How do the y/n/u answers flow into a serializable Review, including the skip paths?

## Question-tree seam
**Path/Symbol:** `gpt_engineer/applications/cli/learning.py:human_review_input` (:122-174) + `Review` (:46-70) + `ask_for_valid_input` (:177-180) + `TERM_CHOICES` (:112-119).
**Signature:** `human_review_input() -> Optional[Review]`; `Review(ran: Optional[bool], perfect: Optional[bool], works: Optional[bool], comments: str, raw: str)`.
**Data Shape:** three-tier ternary answers (y=true / n=false / u=None uncertain) plus free-text comments; `raw` is a joined transcript string.

### Decisive source
```python
if not check_collection_consent():
    return None                                  # consent gate FIRST
ran = ask_for_valid_input(input("Did the generated code run at all? " + TERM_CHOICES))
if ran == "y":
    perfect = ask_for_valid_input(input("Did ... everything you wanted? " + TERM_CHOICES))
    if perfect != "y":
        useful = input("Did ... anything useful? " + TERM_CHOICES); useful = ask_for_valid_input(useful)
    else:
        useful = ""
else:
    perfect = ""; useful = ""
...
return Review(
    raw=", ".join([ran, perfect, useful]),
    ran={"y": True, "n": False, "u": None, "": None}[ran],
    works={"y": True, "n": False, "u": None, "": None}[useful],
    perfect={"y": True, "n": False, "u": None, "": None}[perfect],
    comments=comments,
)
```

**Flow:** consent gate (None short-circuit) → Q1 ran always asked → only on ran=="y" ask perfect → only on perfect!="y" ask useful and comments → assemble Review with dict-mapped bools; every answer passes the strict `while not in ("y","n","u")` re-ask loop.
**Invariant:** (1) Skipped questions become EMPTY STRINGS in `raw` but None in typed fields — `"y, y, "` with trailing space is the all-good transcript (pinned verbatim by test). (2) The mapping dict makes unknown keys KeyError-proof impossible because `ask_for_valid_input` gates every entry to y|n|u before mapping — keep that gate when porting or the dict lookup crashes. (3) `u` (uncertain) and skip both serialize as null — downstream cannot distinguish them except via `raw`. (4) Comments are requested whenever perfection was not affirmed, i.e. also for ran=="n" runs. (5) The whole tree runs ONLY post-consent; review collection fires solely on the generate tail of main (`collect_and_send_human_review` :141-177 has exactly one production caller per graph trace).
**Probe:** `tests/applications/cli/test_learning.py` — no-consent⇒None :9-13; all-"y" ⇒ `raw == "y, y, "`, `works is None`, `comments == ""` :16-26; side_effect ["y","n","y",""] ⇒ `raw == "y, n, y"`, works True :29-39.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "human_review_input Review ran perfect works comments raw", limit: 10 });
```

## Verdict
Adopt the three-question decision tree with string-transcript-plus-typed-null duality; adapt question wording/colors; omit if your host collects reviews via web UI (then reuse only the Review dataclass shape). Direct tests pin the two decisive transcripts at pin.
