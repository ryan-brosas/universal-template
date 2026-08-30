<!-- capsule-v2 -->
# Blueprint deferred registration — how do decorators on an unregistered blueprint become app state, and what does re-registration change?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How does the record/replay mechanism work and what exactly is "first_registration" scoped to?

## deferred_functions replay + name/prefix composition
**Path/Symbol:** `src/flask/sansio/blueprints.py:Blueprint.record` (223–230), `.record_once` (232–244), `.register` (273–377), `._merge_blueprint_funcs` (379–410), `.add_url_rule` (412–441), `BlueprintSetupState` (34–116); concrete `src/flask/blueprints.py:18–53` (AppGroup cli).
**Signature:** `record(func: Callable[[BlueprintSetupState], None]) -> None`; `register(app, options) -> None`.
**Data Shape:** `deferred_functions: list[fn(state)]`; setup state carries resolved `name`, `name_prefix`, `url_prefix`, `subdomain`, `url_defaults` (blueprint defaults overridden by register options).

### Decisive source
```python
# add_url_rule on the BLUEPRINT records; it does not touch the app:
self.record(lambda s: s.add_url_rule(rule, endpoint, view_func, ...))
# SetupState composes endpoint + rule at replay time:
self.app.add_url_rule(
    rule,
    f"{self.name_prefix}.{self.name}.{endpoint}".lstrip("."),
    view_func, defaults=defaults, **options)
```
In `register`: duplicate full name ⇒ ValueError distinguishing "this" vs "a different" blueprint at that name; `first_bp_registration = not any(bp is self for bp in app.blueprints.values())`; merge funcs run when first_bp OR first_name; then each deferred runs with a fresh state; nested blueprints recurse with composed prefixes (`state.url_prefix.rstrip("/") + "/" + bp_url_prefix.lstrip("/")`) and subdomains (`child + "." + parent`), passing `bp_options["name_prefix"] = name`.

**Flow:** decorate → record closure → register_blueprint(app) → name-collision check → static route if folder → `_merge_blueprint_funcs` (dotted-key remap of every scope-dicted callback table into app tables; view_functions copied by UNPREFIXED key because endpoints were already prefixed at record time) → replay deferreds → CLI group attach (`None`⇒merge into root, sentinel⇒group named after full bp name, string⇒that name) → recurse into children.
**Invariant:** `_check_setup_finished` freezes the blueprint after its FIRST registration anywhere (AssertionError) — mutating later is inconsistent because replay is not idempotent for non-record_once callbacks; record_once closures guard themselves via `state.first_registration`.
**Probe:** `grep -Fc "'name' may not contain a dot '.' character." src/flask/sansio/blueprints.py` = 1; `grep -Fc 'if state.first_registration:' src/flask/sansio/blueprints.py` = 1; tests `tests/test_blueprints.py::test_nested_blueprint` (:862), `test_nested_callback_order` (:911), `tests/test_blueprints.py::test_register_twice`-family near :242.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "Blueprint register deferred setup state nested", limit: 8 });
```

## Verdict
Adopt record/replay + dotted-name composition and the identity-vs-name double notion of "first". Adapt CLI-group resolution to your CLI. Omit nothing in this module — it is the whole blueprint contract.
