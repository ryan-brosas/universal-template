<!-- capsule-v2 -->
# Naming and schema — do identifiers read as relational nouns?

**Source:** sqlstyle.guide §Naming conventions. **Question:** Are table/column names portable, singular, and free of Hungarian prefixes?

## Identifier seam
**Path/Symbol:** tables, columns, views, procedures in migrations and queries.
**Signature:** lowercase snake_case; ≤30 characters; letters/numbers/underscore.
**Data Shape:** semantic suffixes where role needs disambiguation.

### Decisive pattern
```sql
CREATE TABLE staff (
    PRIMARY KEY (staff_num),
    staff_num   INT          NOT NULL,
    first_name  VARCHAR(100) NOT NULL,
    hire_date   TIMESTAMP    NOT NULL,
    pens_in_drawer INT       NOT NULL
);

SELECT first_name
  FROM staff AS s
 WHERE s.hire_date >= '2020-01-01T00:00:00.00000';
```

**Flow:** collective table name → singular column names → snake_case words (`first_name`) → avoid `tbl_`/`sp_` prefixes → PK name reflects entity (`staff_num`, not lone `id`).
**Invariant:** camelCase, `tbl_orders`, and column named same as table fail review.
**Probe:** migration review checklist; grep `tbl_`/`sp_` in SQL diff.

## Alias seam
```sql
SELECT s.first_name AS fn
  FROM staff AS s
  JOIN students AS st
    ON st.mentor_id = s.staff_num;

SELECT SUM(s.monitor_tally) AS monitor_total
  FROM staff AS s;
```

**Flow:** alias relates to object → use acronym from words (`s`, `st`) → always keyword `AS` → computed columns named as schema columns would be.
**Invariant:** `FROM staff s` without `AS` and meaningless alias `x` fail review.
**Probe:** sqlfluff/layout rules for explicit `AS`; alias names meaningful in EXPLAIN output.

## Suffix seam

| Column | Suffix | Example |
|---|---|---|
| Primary key | `_id` or entity `_num` | `mentor_id`, `staff_num` |
| Status flag | `_status` | `publication_status` |
| Count | `_tally` | `monitor_tally` |
| Date | `_date` | `hire_date` |

**Flow:** apply uniform suffixes only when they clarify role — not on every column mechanically.
**Invariant:** ambiguous `status` without domain prefix when multiple statuses exist fails review.
**Probe:** schema diagram readable without opening application code.

## Verdict
snake_case relational names, collective tables, singular columns, explicit AS aliases. Learning note: `sql-style-learning-note.md`.
