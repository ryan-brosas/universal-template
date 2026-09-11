<!-- capsule-v2 -->
# Query layout — is SQL formatted for keyword scanning?

**Source:** sqlstyle.guide §Query syntax (reserved words, white space, indentation). **Question:** Can a reader scan keywords down a aligned “river”?

## Keyword seam
**Path/Symbol:** SELECT/INSERT/UPDATE/DELETE queries.
**Signature:** uppercase reserved words; spaces around operators and commas.
**Data Shape:** one major clause per line group; river alignment.

### Decisive pattern
```sql
SELECT a.title,
       a.release_date,
       a.recording_date
  FROM albums AS a
 WHERE a.title = 'Charcoal Lane'
    OR a.title = 'The New Danger';
```

**Flow:** uppercase `SELECT`/`FROM`/`WHERE`/`JOIN`/`GROUP BY` → keywords right-aligned in column → values/columns left-aligned → space around `=`, after `,`, around string literals.
**Invariant:** lowercase keywords and single-line 120-char queries with no breaks fail review on non-trivial SQL.
**Probe:** sqlfluff capitalisation + layout rules; visual river check in review.

## JOIN seam
```sql
SELECT r.last_name
  FROM riders AS r
       INNER JOIN bikes AS b
       ON r.bike_vin_num = b.vin_num
          AND b.engine_tally > 2
       INNER JOIN crew AS c
       ON r.crew_chief_last_name = c.last_name
          AND c.chief = 'Y';
```

**Flow:** join type indented past river → `ON` under join → additional `AND` aligned under `ON` conditions.
**Invariant:** comma-style implicit joins in new code fail review unless dialect-required legacy.
**Probe:** formatter output stable when column list changes (river preserves scan).

## Subquery seam
```sql
SELECT r.last_name,
       (SELECT MAX(YEAR(championship_date))
          FROM champions AS c
         WHERE c.last_name = r.last_name
           AND c.confirmed = 'Y') AS last_championship_year
  FROM riders AS r
 WHERE r.last_name IN
       (SELECT c.last_name
          FROM champions AS c
         WHERE YEAR(championship_date) > '2008'
           AND c.confirmed = 'Y');
```

**Flow:** subqueries follow same river rules → closing paren aligned with opening when nested deeply.
**Invariant:** inline subquery without indentation fails review on multi-line form.
**Probe:** sqlfluff structure pass; nested depth ≤ team limit or refactor to CTE (project convention).

## Verdict
Uppercase keywords, river alignment, disciplined JOIN/subquery indent. Learning note: `sql-style-learning-note.md`.
