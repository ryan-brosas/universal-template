<!-- capsule-v2 -->
# SQLite SQL fragment composition — how do you build dynamic WHERE clauses from parameterized fragments without breaking `?` bind order?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** When a query is assembled at runtime (optional filters, stop predicates, cursor bounds), how do you keep text order and bind-parameter order aligned after composing nested parameterized fragments?

## Template tag with nested-query inlining; joiner preserves param order
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/sql.ts:sql` (:38–53), `joinSqlFragments` (:56–66), `SqlQuery` (:6–36).
**Signature:** `` sql(strings: TemplateStringsArray, ...values: (unknown | SqlQuery)[]): SqlQuery ``; `joinSqlFragments(fragments: readonly SqlQuery[], separator: string): SqlQuery`.
**Data Shape:** a `SqlQuery` is just `{ queryText, params }`. Interpolating a plain value appends one `?` and one param; interpolating a nested `SqlQuery` inlines its text AND splices its params in position. `exec` refuses any query carrying params.

### Decisive source
```ts
for (let index = 0; index < values.length; index++) {
	const value = values[index];
	if (value instanceof SqlQuery) {
		queryText += value.queryText;
		params.push(...value.params);
	} else {
		queryText += "?";
		params.push(value);
	}
	queryText += strings[index + 1] ?? "";
}
return new SqlQuery(queryText, params);
```
```ts
// joinSqlFragments — trusted fragment joiner used for WHERE clause lists
for (let index = 0; index < fragments.length; index++) {
	if (index > 0) queryText += separator;
	const fragment = fragments[index]!;
	queryText += fragment.queryText;
	params.push(...fragment.params);
}
```

**Flow:** callers build predicate lists as arrays of `SqlQuery` fragments (e.g. `queryCachedBranchRows` builds `stopPredicates` then `joinSqlFragments(stopPredicates, " OR ")`, and `predicates` joined with `" AND "`), embed the composed fragment in a larger `sql` template alongside plain-value interpolations (`LIMIT ${query.limit}`), and execute via `run/get/all/iterate` which spread params positionally into `db.prepare(text).run(...)`. The whole backend's parameterized-SQL safety rests on one invariant: after any composition, the Nth `?` in the final text corresponds to the Nth element of the final params array.
**Invariant:** text order == bind order, preserved through arbitrary nesting. A fragment that carries params must never be stringified with its values pre-substituted, and a composed fragment must never be re-bound as a single `?` (SQLite has no bind-by-reference). `exec` stays parameter-free by construction (DDL path).
**Probe:** `test/sql.test.ts` — "composes SQLite queries without renumbering parameters" builds `joinSqlFragments([sql\`kind = ${"message"}\`, sql\`active = ${1}\`], " AND ")`, embeds it in `sql\`SELECT id FROM entries WHERE ${filters} LIMIT ${10}\``, and asserts the row set — the LIMIT param lands AFTER both filter params only if splice order is correct. Second case pins plain positional binding through `get`/`all`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(joinSqlFragments|SqlQuery).*", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the two-rule composition kernel (plain value ⇒ `?` + push; nested query ⇒ inline text + splice params) plus the exec-refuses-params guard. Adapt to your driver's placeholder style (`$name`, `:name`) by changing only the leaf `run/get/all` methods. Omit any "safe string interpolation" escape hatch — the moment a fragment can carry raw substituted values, the bind-order invariant is unprovable. Caveat: MCP graph was not connected this pass; anchors verified by direct read at pin `4af9d21d`, and the exact sql.test.ts scenario was re-executed deterministically against node:sqlite (probe P2 GREEN: composed text `…WHERE kind = ? AND active = ? LIMIT ?` with params `["message",1,10]`; exec-with-params refused).
