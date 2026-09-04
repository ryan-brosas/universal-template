<!-- capsule-v2 -->
# You.com capability pair: status-classified retries, sources as ToolReturn metadata, freshness validated at construction

## Source / Question
`pydantic_ai_harness/youdotcom/_toolset.py` (373L) + `_capability.py` (172L) + `_research.py` (337L) @ `main@f971198` (PR #646) — Wrapping a rate-limited external search API: which failures can the MODEL fix by rephrasing vs which mean the run is misconfigured, and how do citations travel without forcing the model to parse prose?

## Path / Symbol
`youdotcom/_toolset.py` — `recoverable` decorator (:178–210), `_PROPAGATE_STATUS = frozenset({401,402,403})` (:49), `validate_freshness` (:84–96), `default_client` (:168–175), `YouClient` protocol (:99–165), `_web_result_body` preference ladder (:223–240), `YouSearchToolset.web_search/get_page` (:297–373); `_capability.py` — construction bounds + domain mutual-exclusion (:104–114); `_research.py` — `answer/research/finance_research` with ModelRetry-on-empty (:129–196), `_with_sources/_prefix_warnings/_render_content` helpers (:53–74), effort Literals + `output_schema×'lite'` rejection (:35–42, :281–282).

## Signature
```python
_PROPAGATE_STATUS = frozenset({401, 402, 403})   # auth/billing/authorization = configuration, abort
def recoverable(fn):                              # order matters:
    except httpx.HTTPStatusError as error:        #   inspect response status BEFORE broad handler
        if error.response.status_code in _PROPAGATE_STATUS: raise
        raise ModelRetry(...) from error
    except (httpx.HTTPError, NoResponseError) as error: raise ModelRetry(...)
    except YouError as error:                     # SDK error: getattr status_code may be absent
        status = getattr(error, 'status_code', None)
        if isinstance(status, int) and status in _PROPAGATE_STATUS: raise
        raise ModelRetry(...)
```

## Data Shape
Citations ride STRUCTURED: `ToolReturn(text_with_sources_block, metadata={'sources': [{'url','title'}, …]})` so apps render citations from `ToolReturnPart.metadata` "without parsing the text" (_toolset docstring :250–254); web_search additionally carries `search_uuid`/`latency` for tracing. Empty/absent results are ModelRetry ("Rephrase the question"), never empty-string successes.

### Decisive source
Freshness gate (:71–96): keywords {day,week,month,year} or `YYYY-MM-DDtoYYYY-MM-DD` fullmatch with REAL dates via strptime and start≤end — "Malformed ranges (non-ASCII digits, impossible or reversed dates, trailing characters) are rejected here rather than forwarded to You.com." Body preference ladder (:223–240): configured extraction mode picks preferred field, other field is fallback when both present; results fall back contents→snippets→description; URL-less results skipped and count capped at num_results (:319–325). Domain triad rule: include_domains mutually exclusive with exclude/boost — API rejects combining allowlist with either (:70–73). Research background-mode result (not a synthesized answer) ⇒ ModelRetry (:551 test pins it). `default_client` raises UserError naming BOTH env vars (`YDC_API_KEY`, legacy `YOU_API_KEY_AUTH`) with a fix-it example (:168–175).

**Flow:** capability validates bounds at `__post_init__` → toolset builds default client lazily → call under `recoverable` → classify status → render text+sources block → attach structured metadata.
**Invariant:** 4xx-model-fixable becomes retry; config-state propagates; every tool result carries machine-usable sources even when the text already lists them.

## Probe (direct test)
`tests/youdotcom/test_youdotcom.py` (59 tests) — `test_auth_and_billing_propagate` :476, `test_http_status_error_auth_propagates` :487, `test_rate_limit_becomes_model_retry` :470, `test_you_error_without_status_becomes_model_retry` :481, markdown-vs-highlights preference matrix :344–395, `test_skips_urlless_results_and_caps_count` :397, title fallback chain :423–433, `test_background_task_response_raises_model_retry` :551, env-var matrix :583–594.

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'validate_freshness recoverable source_list'
# File nodes: pydantic_ai_harness.youdotcom._{toolset,capability,research}.__file__
```

## Verdict
**Adopt** the status-classification decorator and metadata-sources pattern for any search/API wrapper. **Adopt** construction-time validation of API-side constraints. **Adapt** propagate-status set to your vendor's semantics. **Omit** finance endpoints unless needed.
