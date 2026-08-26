<!-- capsule-v2 -->
# YAML entry gate with None-tolerant defaults — how do I validate a declarative config at startup with errors that name the exact fix, then coalesce missing/null fields into safe defaults?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`__main__` :696–741); config schema artifact config.yaml; Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** what is the minimal startup gate between yaml.safe_load and bot construction that catches empty requireds, wrong container SHAPES, and null entries without a validator framework?

## Assert ladder + shape-specific exception + None-filtering resolution
**Path/Symbol:** module tail `if __name__ == '__main__':` (:696–741); graph note: this region is module-level code, anchored by the `config.yaml` Module node (variables :1–37) plus direct source read — check_index_coverage(easyapplybot.py, config.yaml) ⇒ no_recorded_issue/metadata_match.
**Signature:** script-level statements; helpers absent by design — asserts for presence, ONE typed-shape Exception, comprehension ladders for defaults.
**Data Shape:** parameters = yaml dict; uploads must be a MAPPING (YAML list is the canonical user error); output_filename/blacklist/blackListTitles/experience_level resolve through `.get(key, default)`; None entries are filtered, never trusted.

### Decisive source
```python
with open("config.yaml", 'r') as stream:
    try:
        parameters = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise exc

assert len(parameters['positions']) > 0          # presence gates first…
assert len(parameters['locations']) > 0
assert parameters['username'] is not None
assert parameters['password'] is not None
assert parameters['phone_number'] is not None

if 'uploads' in parameters.keys() and type(parameters['uploads']) == list:
    raise Exception("uploads read from the config file appear to be in list format" +
                    " while should be dict. Try removing '-' from line containing" +
                    " filename & path")            # names the EXACT yaml edit

log.info({k: parameters[k] for k in parameters.keys() if k not in ['username', 'password']})  # redact secrets

output_filename = [f for f in parameters.get('output_filename', ['output.csv']) if f is not None]
output_filename = output_filename[0] if len(output_filename) > 0 else 'output.csv'
uploads = {} if parameters.get('uploads', {}) is None else parameters.get('uploads', {})
for key in uploads.keys():
    assert uploads[key] is not None               # null upload PATHS caught too
locations = [l for l in parameters['locations'] if l is not None]
```

**Flow:** parse yaml → assert required keys non-empty/non-null → reject wrong container shape with an error message quoting the YAML edit → log the effective config MINUS credential keys → resolve optional scalars/lists through .get-with-default plus per-entry None filtering → construct bot.
**Invariant:** nothing reaches the constructor that is missing-and-required, wrongly-shaped, or silently-null; every default lives at the GATE (one place) so downstream code sees final values; credentials never enter the startup log line. The shape exception is self-diagnosing like Auto_job_applier's validator ladder but costs six lines — it encodes the single most common real-user mistake (YAML block-list vs mapping for uploads).
**Probe:** repo ships no test suite — coverage caveat recorded. Deterministic probes verified byte-for-byte at HEAD 8471c58: `grep -n "assert \|raise Exception\|parameters.get" easyapplybot.py` ⇒ all sites confined to :704–:739; `grep -n "not in \['username', 'password'\]" easyapplybot.py` ⇒ :716 (redaction line).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", file_pattern: "config.yaml", limit: 15 });
// ⇒ config Module :1-37 + 11 Variables (positions, locations, uploads, output_filename, experience_level …)
```

## Verdict
Adopt gate-then-defaults ordering (presence asserts BEFORE .get defaults), one shape-specific message per known misconfiguration naming the exact edit, secret redaction in the startup echo, and None-filtering comprehensions for list-valued fields; adapt into dataclasses/pydantic once configs exceed ~15 keys; omit bare asserts for anything a user must debug remotely (AssertionError carries no context — swap for raised Exceptions with messages when porting seriously). Contrast: config-validation-ladder (Auto_job_applier) is the full typed-checker framework; this seam is its minimal-expression twin for small bots.