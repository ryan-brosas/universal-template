<!-- capsule-v2 -->
# query-boost-grammar — how does a raw question become a weighted full-text query?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** What boosting structure does FulltextQueryer emit for English vs Chinese, and what escaping rules protect the engine lexer?

## Weighted-term + phrase + synonym query builder
**Path/Symbol:** `FulltextQueryer.question` `rag/nlp/query.py:42-168`; field boosts `:32-40`; `paragraph` variant `:211-231`.
**Signature:** `question(txt, tbl="qa", min_match: float = 0.6) -> tuple[MatchTextExpr | None, list[str]]`.
**Data Shape:** `query_fields = ["title_tks^10","title_sm_tks^5","important_kwd^30","important_tks^20","question_tks^20","content_ltks^2","content_sm_ltks"]`; MatchTextExpr carries `{minimum_should_match: min_match, original_query}` on the Chinese arm and `{original_query}` only on the English arm (min_match rides extra_options unused there).

### Decisive source
```python
# English branch: term^weight plus synonym quotes plus bigram phrases
q = ["({}^{:.4f}".format(tk, w) + " {})".format(syn) for (tk, w), syn in zip(tks_w, syns) ...]
for i in range(1, len(tks_w)):
    ...
    q.append('"%s %s"^%.4f' % (tks_w[i-1][0], tks_w[i][0], max(tks_w[i-1][1], tks_w[i][1]) * 2))
...
return MatchTextExpr(self.query_fields, query, 100, {"original_query": original_query}), keywords
# Chinese branch: OR-of-groups, synonym fold, fine-grained subtokens
tk = f"{tk} OR \"%s\" OR (\"%s\"~2)^0.5" % (" ".join(sm), " ".join(sm))   # :148
if syns and tms:
    tms = f"({tms})^5 OR ({syns})^0.7"                                     # :159
```

**Flow:** normalize (full-width→half, traditional→simplified, strip Infinity ESCAPABLE chars `[ :|\r\n\t,，。？?/\`!！&^%%()\[\]{}<>*~'\"\\]+`) → empty-after-tokenize returns `(None, [])` (caller goes dense-only) → branch on `is_chinese`: English builds `term^w (syn)^w/4` groups + adjacent-bigram `"a b"^2max(w)`; Chinese splits into ≤256 weighted segments, each `(group)^w` joined by OR, synonyms folded at ^0.2/^0.7, fine-grained subtokens as quoted proximity `("s m")^0.5`, segment phrase boost ("tt"~2)^1.5 when multi-token. Keywords roster capped at 32 entries.
**Invariant:** every user-influenced token passes `sub_special_char` / quote-stripping before entering the query string (WordNet synonyms like "cat-o'-nine-tails" get `'` removed — comment cites Infinity lexer TokenError). The English branch NEVER sets minimum_should_match; porting it into the ES body changes recall semantics.
**Probe:** `sed -n '46,55p' rag/nlp/query.py | grep -c 'search_lexer.l defines ESCAPABLE'` → 1; `grep -n '"{}^{:.4f}".format(tk, w)' rag/nlp/query.py` → matches :78 pattern form `q = ["({}^{:.4f}"` → 1 hit; `sed -n '148p;159p' rag/nlp/query.py` shows the two Chinese boost folds (executed, present). Executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "FulltextQueryer question minimum_should_match synonym boost", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt the two-branch grammar and the escape-before-format rule; adapt boost constants (they encode corpus priors); omit WordNet/synonym Redis lookup if your host lacks the cache but keep keyword caps.
