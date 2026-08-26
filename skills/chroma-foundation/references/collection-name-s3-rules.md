<!-- capsule-v2 -->
# Collection name S3 rules — What five conditions must a collection name satisfy and where are they enforced?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Porters cloning the API surface must reproduce create/rename validation exactly — what does check_index_name accept?

## check_index_name
**Path/Symbol:** `chromadb/api/segment.py:check_index_name` (:97-115); called from `create_collection` (:238) and `_modify` (:404).
**Signature:** `check_index_name(index_name: str) -> None`; raises ValueError with a single combined message listing all five rules.
**Data Shape:** Regex gates — length 3..63; `^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$` (alphanumeric ends, middle allows . _ -); no `..` anywhere; IPv4-shaped names rejected.

### Decisive source
```python
if len(index_name) < 3 or len(index_name) > 63:
    raise ValueError(msg)
if not re.match("^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$", index_name):
    raise ValueError(msg)
if ".." in index_name:
    raise ValueError(msg)
if re.match("^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$", index_name):
    raise ValueError(msg)
```

**Flow (live-verified):** accepted `abc`, `ab1`, `a-b_c.d`; rejected `ab` (short), `-abc` (leading hyphen), `192.168.1.1` (IPv4), `a..b` (double dot). Comment states intent: "mimics s3 bucket requirements for naming". Enforced on BOTH create and rename paths before sysdb writes; quota enforcement follows.
**Invariant:** Validation is purely lexical — no unicode folding, no trimming; callers relying on normalization will diverge from upstream behavior.
**Probe:** `/tmp/chroma-p1/probe_battery.py` api.ipv4_reject anchor + api.name_live live matrix over 5 rejected shapes (GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "check_index_name collection name validation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim for API-compatible stores; adapt error text to your i18n; omit telemetry events around it.
