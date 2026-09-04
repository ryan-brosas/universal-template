<!-- capsule-v2 -->
# Multi-token export fanout — how does one SDK stream send identical telemetry to N projects for migration?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** How are multiple tokens normalized, fanned out into exporter pipelines, and kept from double-printing project links?

## _load_configuration token normalization + _initialize fanout loop
**Path/Symbol:** `logfire/_internal/config.py:_initialize token loop` (`config.py:1336-1433`) + `normalize_token` in `config_params.py`.
**Signature:** `token: str | list[str] | None` (env `LOGFIRE_TOKEN` supports comma-separated); per-token headers `{'User-Agent': f'logfire/{VERSION}', 'Authorization': token}`.
**Data Shape:** each token yields its own exporter chain but SHARES one session object per token across traces/metrics/logs exporters.

### Decisive source
```python
token_list = [self.token] if isinstance(self.token, str) else self.token
printed_tokens: set[str] = set()
if credentials and show_project_link and credentials.token in token_list:
    credentials.print_token_summary(); printed_tokens.add(credentials.token)
...
for token in token_list:
    base_url = self.advanced.generate_base_url(token)     # region inferred FROM TOKEN
    otlp_forwarding_destinations.append((base_url, token))
    headers = {...}; session = OTLPExporterHttpSession()
    span_exporter = BodySizeCheckingOTLPSpanExporter(endpoint=urljoin(base_url,'/v1/traces'), session=session, compression=Gzip, headers=headers)
    span_exporter = QuietSpanExporter(RetryFewerSpansSpanExporter(RemovePendingSpansExporter(span_exporter)))
    add_span_processor(DynamicBatchSpanProcessor(span_exporter))
    metric_readers.append(PeriodicExportingMetricReader(QuietMetricExporter(OTLPMetricExporter(..., preferred_temporality=METRICS_PREFERRED_TEMPORALITY))))
    log_record_processors.append(BatchLogRecordProcessor(QuietLogExporter(OTLPLogExporter(...))))
    # Forgetting to include `headers=headers` previously allowed env vars like
    # OTEL_EXPORTER_OTLP_HEADERS to override ours since one session is shared.
    session.headers.update(headers)
```
Background validation runs once per distinct token in a thread named `check_logfire_token` (skipped on Emscripten); printed-link dedupe via `printed_tokens` because creds-file link prints eagerly.
**Flow:** normalize (str→[str]) → creds-file token merged as fallback (env WINS over file: "a token in an env var takes priority over a token in a creds file") → loop mints a fully decorated exporter trio per token sharing one session → final belt-and-braces `session.headers.update(headers)` re-asserts auth over any env leakage.
**Invariant:** Region/base-url derives from EACH token (multi-region migration supported); METRICS_PREFERRED_TEMPORALITY table (Counter DELTA / UpDown CUMULATIVE / Histogram DELTA / Observable* mixed) must ride BOTH the exporter and reader. The comment about header override is an incident record — keep the final update line.
**Probe:** `tests/test_configure.py::test_multiple_tokens` family — pins fanout and header assertion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "token_list generate_base_url BodySizeCheckingOTLPSpanExporter METRICS_PREFERRED_TEMPORALITY", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-destination pipeline minting with shared-session auth reassertion. Adapt the decoration stack order to your exporters. Omit forwarding destinations (`OTLPForwardingManager`) unless you also port the browser-proxy plane.
