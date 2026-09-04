<!-- capsule-v2 -->
# GCP credential priority ladder — four methods, silent skips, default-credentials safety net

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** in what order does a Vertex/GenAI consumer resolve GCP credentials, and which candidate failures are silently skipped vs fatal?

## Connected graph-selected seam
**Path/Symbol:** `mem0/utils/gcp_auth.py`: `GCPAuthenticator.get_credentials` (:25-90); consumers `setup_vertex_ai` (:93-135) and `get_genai_client` (:138-172).
**Signature:** `get_credentials(service_account_json: Optional[Dict], credentials_path: Optional[str], scopes: Optional[list]) -> tuple[Credentials, Optional[str]]`.
**Data Shape:** returns `(credentials, project_id)`; project_id may be None (caller must fall back).

### Decisive source
```python
# Method 2: Service account file path
elif credentials_path and os.path.isfile(credentials_path):
    ...
# Method 3: Environment variable path
elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if os.path.isfile(env_path):        # missing file ⇒ falls THROUGH, not an error
        ...

# Method 4: Default credentials (GCE, Cloud Run, etc.)
if not credentials:
    try:
        credentials, project_id = default(scopes=scopes)
    except Exception as e:
        raise ValueError("No valid GCP credentials found. ...")
```

**Flow:** in-memory JSON dict → file path (only if the file EXISTS) → `GOOGLE_APPLICATION_CREDENTIALS` env path (only if THAT file exists) → ADC default → all four fail ⇒ aggregated ValueError enumerating every option. Each earlier method that "doesn't apply" is skipped SILENTLY — there is no warning when a configured path is absent; the ladder simply continues.
**Invariant:** an invalid/unreachable explicitly-configured credential never raises by itself — it demotes to the next method, so the ONLY fatal exit is total failure at rung 4. A port that raises on a missing `credentials_path` breaks metadata-server deployments (where only ADC works); a port that stops after method 3 without trying ADC loses Cloud Run/GCE operation entirely. `setup_vertex_ai` adds the project-id ladder `param → detected → GOOGLE_CLOUD_PROJECT env → ValueError`, and `get_genai_client` short-circuits: explicit `api_key` bypasses service-account auth entirely.
**Probe:** `grep -cF 'elif credentials_path and os.path.isfile(credentials_path)' mem0/utils/gcp_auth.py` (=1); `grep -cF 'if not credentials:' mem0/utils/gcp_auth.py` (=1); `grep -cF 'final_project_id = project_id or detected_project_id or os.getenv("GOOGLE_CLOUD_PROJECT")' mem0/utils/gcp_auth.py` (=1).
**Coverage caveat (scoped):** gcp_auth itself has no dedicated suite; the Vertex consumer's ladder IS tested via `tests/embeddings/test_vertexai_embeddings.py::test_credentials_from_environment` (:118) / `test_missing_credentials` (:127) — state this when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "get_credentials service_account_json GOOGLE_APPLICATION_CREDENTIALS default", limit: 10 });
```

## Verdict
Adopt the four-rung silent-skip ladder with ADC as mandatory final rung and the aggregated error message; adapt scope strings per consumer (`cloud-platform` for Vertex, `generative-language` for GenAI); omit eager validation of configured paths — silence is the designed behavior.
