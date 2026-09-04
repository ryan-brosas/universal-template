<!-- capsule-v2 -->
# DISTINCT-safe current-user-first ordering — how do you pin the acting user to the top of a Filament relationship select without breaking SELECT DISTINCT?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** Postgres rejects ORDER BY expressions missing from a SELECT DISTINCT list (SQLSTATE[42P10]) — how do you order a BelongsToMany picker by "is the current user" first, then alphabetically?

## TeamMemberSelect aliased comparison column + relationship() override
**Path/Symbol:** `app/Filament/Components/Forms/TeamMemberSelect.php` :65 `orderByCurrentUserFirst(Builder $query)`, :92 `relationship(...)`, :40 `currentUserFirst(): Closure`, :30 `IS_CURRENT_USER_ALIAS`.
**Signature:** `currentUserFirst(): Closure(Builder<User>): Builder<User>`; `relationship(string|Closure|null $name, string|Closure|null $titleAttribute, ?Closure $modifyQueryUsing, bool $ignoreRecord): static`.
**Data Shape:** Filament's RelationshipJoiner pre-builds every BelongsToMany query as `->distinct()->select('users.*')`; alias `team_member_select_is_current_user` is namespaced defensively so it cannot collide with a real `users` column.

### Decisive source
```php
if ($query->getQuery()->columns === null) {
    $query->select('users.*');
}

return $query
    ->selectRaw('(users.id = ?) as '.self::IS_CURRENT_USER_ALIAS, [auth()->id()])
    ->orderByDesc(self::IS_CURRENT_USER_ALIAS)
    ->orderBy('users.name');
```
(:67-77). The alias is a pure function of `users.id` — already part of the distinct row (primary key) — so it cannot introduce new distinct combinations: row counts under DISTINCT are unchanged. The defensive re-select covers BelongsTo/HasOne/HasMany where RelationshipJoiner does NOT pre-select; without it selectRaw on a query with no prior select() replaces the result set with only the alias column, since addSelect does not default-populate `*` for raw expressions.

**Flow:** relationship() override wraps any caller modifier: pin first (:102), then run caller's closure through the component's own evaluate() with named `query`/`search` injections (:108-111) — invoking positionally would throw ArgumentCountError for modifiers declaring `?string $search` or Filament's `Get`/`Model` injections. Pin is applied BEFORE the caller modifier, so a caller's orderBy becomes secondary under it. auth()->id() resolves at query-run time, not schema-build time — capturing early pins one user for every subsequent request. Docblock names the deliberate exception: the chat ProposalCard builds an options-array select from TeamMembersContext and does NOT use this component because there is no relationship there.
**Invariant:** Every ORDER BY expression in a SELECT DISTINCT query must appear in the select list; satisfy it by selecting the comparison AS an alias derived from an already-selected column. Component docblocks cite framework internals (Select.php:1151 alphabetical-order fallback applies only when the query carries none; Select.php:1004-1008 named injections).
**Probe:** `tests/Feature/Teams/TeamMembersTest.php` (:21 renders every member; :34 skips membership rows whose user no longer exists). Coverage caveat: ordering behavior itself has no dedicated direct test at this pin — pinned via component source + consumer wiring.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "TeamMemberSelect currentUserFirst orderByCurrentUserFirst relationship", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the aliased-boolean-under-DISTINCT trick and the evaluate()-with-named-injections wrapper for any Filament v4+ component override; adapt label rendering; omit the self-label translation key. Direct tests cover table rendering; SQL-shape correctness rests on cited framework line numbers in-source.
