<!-- capsule-v2 -->
# Query patterns and portability — are expressions idiomatic and safe?

**Source:** sqlstyle.guide §Preferred formalisms, §General. **Question:** Do queries prefer standard SQL forms and parameterized execution at the app boundary?

## Expression seam
**Path/Symbol:** WHERE/HAVING/SELECT expressions.
**Signature:** BETWEEN/IN/CASE over repeated OR; ANSI functions when portable.
**Data Shape:** comments for non-obvious logic.

### Decisive pattern
```sql
SELECT CASE postcode
           WHEN 'BN1' THEN 'Brighton'
           WHEN 'EH1' THEN 'Edinburgh'
       END AS city
  FROM office_locations
 WHERE country = 'United Kingdom'
   AND opening_time BETWEEN 8 AND 9
   AND postcode IN ('EH1', 'BN1', 'NN1', 'KW1');
```

**Flow:** `BETWEEN` for ranges → `IN (...)` for discrete sets → `CASE` for derived labels → prefer ANSI keywords/functions over vendor-only equivalents when portable.
**Invariant:** long chains of `OR col = 'x'` fail review when `IN` applies.
**Probe:** sqlfluff passes; dialect-specific functions documented when unavoidable.

## Comments seam
```sql
SELECT file_hash  -- stored ssdeep hash
  FROM file_system
 WHERE file_name = '.vimrc';

/* Updating the file record after writing to the file */
UPDATE file_system
   SET file_modified_date = '1980-02-22 13:19:01.00000',
       file_size = 209732
 WHERE file_name = '.vimrc';
```

**Flow:** `--` line comments for brief notes → `/* */` for blocks → comment non-obvious business rules, not obvious syntax.
**Invariant:** commented-out query blocks left in migrations fail review.
**Probe:** migration review excludes dead SQL.

## Security seam (application boundary)
```sql
-- Application must bind parameters — never concatenate user input:
-- WHERE user_id = :user_id
```

**Flow:** all dynamic values via bound parameters / prepared statements → no string concat of user input in app-generated SQL.
**Invariant:** `"WHERE id = " + userInput` patterns fail review in application code generating SQL.
**Probe:** grep `"SELECT.*\\+"` / f-string SQL in app code; use ORM parameter APIs.

## Verdict
BETWEEN/IN/CASE idioms, ISO dates, ANSI portability, parameterized execution. Learning note: `sql-style-learning-note.md`.
