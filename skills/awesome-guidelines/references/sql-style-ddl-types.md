<!-- capsule-v2 -->
# DDL, types, and constraints — is schema portable and validated?

**Source:** sqlstyle.guide §Create syntax. **Question:** Are types standard, keys explicit, and constraints readable?

## CREATE TABLE seam
**Path/Symbol:** migration DDL files.
**Signature:** PRIMARY KEY declared first; 4-space column indent; constraints under columns.
**Data Shape:** portable ANSI types; ISO 8601 timestamps.

### Decisive pattern
```sql
CREATE TABLE staff (
    PRIMARY KEY (staff_num),
    staff_num      INT(5)       NOT NULL,
    first_name     VARCHAR(100) NOT NULL,
    pens_in_drawer INT(2)       NOT NULL,
                   CONSTRAINT pens_in_drawer_range
                   CHECK (pens_in_drawer BETWEEN 1 AND 99)
);
```

**Flow:** `PRIMARY KEY` immediately after open paren → column defs indented 4 spaces → column-level constraints aligned under name → table-level constraints at end when multi-column.
**Invariant:** unnamed ambiguous constraints and missing keys on entity tables fail review.
**Probe:** migration applies cleanly; ER diagram shows keys.

## Types seam
```sql
amount_due    NUMERIC(12, 2) NOT NULL,
opened_at     TIMESTAMP      NOT NULL,  -- ISO 8601 values
is_active     BOOLEAN        NOT NULL
```

**Flow:** prefer `NUMERIC`/`DECIMAL` for money → ISO 8601 date/time strings or TIMESTAMP → avoid vendor-only types when portable alternative exists → default value same type as column, before `NOT NULL`.
**Invariant:** `FLOAT`/`REAL` for currency and INTEGER default on DECIMAL column fail review.
**Probe:** grep float money columns; sample values ISO-formatted.

## Designs to avoid seam
**Flow:** no EAV attribute tables for relational data → no split value/unit columns → no OOP inheritance table sprawl → avoid `UNION` across split tables when single table suffices.
**Invariant:** new EAV or `entity_attribute_value` pattern without documented exception fails review.
**Probe:** schema review questions “can this be a column or normalized table instead?”

## Verdict
Explicit keys, portable types, aligned constraints, reject EAV/split-value hacks. Learning note: `sql-style-learning-note.md`.
