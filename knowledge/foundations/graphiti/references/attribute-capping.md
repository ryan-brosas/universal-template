<!-- capsule-v2 -->
# Attribute capping — defend against LLM schema-description bleed

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does an extraction pipeline cap string/list attributes so the LLM can't dump multi-paragraph reasoning into a free-form field?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/attribute_utils.py` (254 lines): `cap_string_attributes` (:141-186+), `_resolve_default_max_length` (:62), `_field_max_length` (:83), `_check_value_against_cap` (:105), `apply_capped_attributes` (:220).
**Signature:** `cap_string_attributes(response, model, *, default_max_length, ...)` — drops string/list-of-string attributes whose value exceeds a length cap; returns `(kept, dropped)`.
**Data Shape:** for string fields the cap is the value length; for list fields enforced per-item + aggregate (`max_len * LIST_TOTAL_LENGTH_MULTIPLIER`); cap precedence = explicit `max_length` on the Pydantic Field wins, else resolved default (`GRAPHITI_ATTRIBUTE_MAX_LENGTH` env var, else `default_max_length`).

### Decisive source
```ts
def cap_string_attributes(response, model, *, default_max_length=..., ...):
    # Drop string (or list-of-string) attributes whose value exceeds a length cap.
    # Defends against meta-thinking / schema-description bleed where the LLM dumps
    # multi-paragraph reasoning into a free-form attribute field.
    # Cap precedence: explicit max_length on the Pydantic Field wins; else resolved default.
    # Required-field exception: if a field is REQUIRED and over-cap, the value is
    #   retained (with a warning) rather than dropped — dropping a required field
    #   would fail the subsequent model(**capped) validation.
```

**Flow:** for each field, resolve the cap (explicit Field max_length, else env/default) → check value against the cap (string length or list aggregate) → if over-cap and not required, drop the field; if required, retain with a warning. Returns `(kept, dropped)`.
**Invariant:** over-cap fields are dropped (defending against schema-description bleed); a REQUIRED over-cap field is retained (dropping it would fail validation); logging uses `entity_uuid` not name (no PII).
**Probe:** `tests/` attribute tests (over-cap string dropped; list aggregate capped; required over-cap retained; explicit Field max_length precedence).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "cap_string_attributes attribute cap max_length bleed required", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the attribute-capping guard (drop over-cap string/list fields, retain required over-cap, cap precedence); adapt the default cap and list multiplier to host.
