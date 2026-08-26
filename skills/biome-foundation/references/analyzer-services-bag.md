<!-- capsule-v2 -->
# Service bag & typed options — how do rules demand services without the scheduler knowing rule names?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a rule needs the semantic model, JSX runtime, or per-rule config — how does a TypeId map make missing services a diagnostic (not a panic) and make service demands choose the execution phase?

## The services seam
**Path/Symbol:** `crates/biome_analyze/src/services.rs` — `ServiceBag` (:37-53), `FromServices` (:29-35), `ServicesDiagnostic` (:7-27), `ExtendedConfigurationProvider` (:65-73); `crates/biome_analyze/src/options.rs` — `RuleOptions(TypeId, Box<dyn Any>, Option<FixKind>)` (:11-34), `AnalyzerRules` FxHashMap<RuleKey, RuleOptions> (:36-54), `AnalyzerOptions::rule_options/rule_fix_kind` (:204-221).
**Signature:** `fn from_services(rule_key: &RuleKey, rule_metadata: &RuleMetadata, services: &ServiceBag) -> Result<Self, ServicesDiagnostic>`; `pub fn get_service<T: 'static>(&self) -> Option<&T>` keyed by `TypeId::of::<T>()`.
**Data Shape:** `services: FxHashMap<TypeId, Box<dyn Any>>` — insert OVERWRITES silently (one instance per type); `RuleContext` stores BOTH `bag: &'a ServiceBag` and the resolved `services: RuleServiceBag<R>` (= `<R::Query as Queryable>::Services`) built eagerly in `new()` via `FromServices::from_services(...)?` (context.rs:48-64), then `Deref`s to it (:220-229) so `ctx.model()` style accessors just work.

### Decisive source
```rust
// context.rs:220-229 — Deref makes the RESOLVED services tuple the rule's view
// of the context; get_service::<T> on the raw bag is the escape hatch:
impl<R> Deref for RuleContext<'_, R> where R: Rule {
    type Target = RuleServiceBag<R>;   // = <R::Query as Queryable>::Services
    fn deref(&self) -> &Self::Target { &self.services }
}
```
```rust
// signals.rs:517 + registry.rs:411 — options materialize as Default when unset:
let options = self.options.rule_options::<R>().unwrap_or_default();
```
**Flow:** services are inserted into the bag during builder/visitor setup (`insert_service`, e.g. SemanticModelBuilder's finish inserts the model in the Syntax phase — analyzer.md pass-1 capsule). When a signal fires, the executor or RuleSignal builds a RuleContext; `from_services` tries to extract each demanded service and on first miss returns `Err(ServicesDiagnostic)` whose message is exactly `Missing services [SemanticModel] for the rule X` (markup, :16-26) — for RuleSignal paths `.ok()?` turns that into "no diagnostic emitted" rather than a crash. Because `type Services: FromServices + Phase`, demanding a phase-carrying service type promotes the whole QUERY to that phase (Phase for () ⇒ Syntax; semantic.rs impls ⇒ Semantic) — the type system is the scheduler. Rule options ride `AnalyzerConfiguration.rules: Rc<AnalyzerRules>` cloned into every `AnalyzerOptions` clone; `rule_options::<R>()` looks up by `RuleKey::rule::<R>()` (group+name &'static strs) and downcasts with a debug_assert TypeId check — release-mode mismatch is UB-adjacent unwrap, so option types must be unique per rule.
**Invariant:** one service instance per concrete type (later insert wins); missing-service is DATA (diagnostic), never panic; options default silently; the Deref target IS the query's service tuple — adding a service to a rule means changing its Query's Services associated type, which also re-phases it.
**Probe:** `crates/biome_analyze/src/syntax.rs` test :188-206 constructs an Analyzer with an empty ServiceBag and default AnalyzerOptions end-to-end; upstream semantic-phase harnesses assert the exact ServicesDiagnostic message when a semantic rule runs syntax-only (analyzer.md probe).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ServiceBag FromServices ServicesDiagnostic RuleContext", limit: 10, fields: ["signature", "name", "file"] });
// ServiceBag.get_service services.rs 48-52; RuleContext.get_service context.rs 215-217 (line-exact)
```

## Verdict
Adopt the TypeId service bag with Result-typed extraction, eager per-signal resolution through FromServices, Options-as-Default lookup keyed by static rule names, and services-as-phase scheduling; adapt the configuration plumbing; omit ExtendedConfigurationProvider unless you must break a configuration-crate cycle. Coverage caveat: pinned by harness tests asserting the exact diagnostic string; no test covers double-insert overwrite.
