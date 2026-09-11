<!-- capsule-v2 -->
# YAML code-insight declarations — how does an IDE encode hard-won type facts about dynamic frameworks as data?

**Source:** JetBrains installed distribution (proprietary install) RubyMine Linux `dist@262.9437.192`; Codebase Memory `jetbrains-rubymine`. **Question:** Which inference facts must be data (not code), and what schema carries them?

## Declarative class/method/member/block type tables per framework
**Path/Symbol:** `plugins/ruby/rb/scripts/{ruby,rails,rspec}_code_insight.yaml` (14L / 101L / 198L); loader named in header comment: org.jetbrains.plugins.ruby.ruby.codeInsight.YamlDynamicExtensionsLoader.loadFromMap.
**Signature:** YAML families: class_types, method_types (with $$SINGLETON$$ receiver marker and variants lists), dynamic_members (instance_methods lists), block_variable_types.
**Data Shape:** values are type strings (:empty, :same_as_receiver, FQNs like ActiveRecord::ConnectionAdapters::AbstractAdapter) or variant arrays; nesting keys mirror class namespaces.

### Decisive source
```yaml
# ruby_code_insight.yaml — semantics vocabulary, not just names
class_types:
  OpenStruct: :empty            # dynamic builder: any method exists
method_types:
  Object: { tap: :same_as_receiver, clone: :same_as_receiver }
block_variable_types:
  Object.tap: :same_as_call
# rails_code_insight.yaml — synthetic member lists with WHY comments
dynamic_members:
  ActiveRecord:
    Associations:
      HasManyAssociation:
        # When calling has_many :items we're invoking Associations::Builder::HasMany...
        instance_methods:
          sum: ActiveRecord::Associations::CollectionProxy
# rspec_code_insight.yaml — mock DSL returns variants of creator objects
RR: { DoubleDefinitions: { Strategies: { StrategyMethods: { stub!: { variants: [...] } } } } }
```

**Flow:** loader ingests map at runtime → resolver consults class_types/method_types/dynamic_members before giving up → block_variable_types binds block params semantically (same_as_receiver/same_as_call).
**Invariant:** these are facts that CANNOT be derived from user sources (metaprogrammed Rails accessors, blank-slate mock DSLs) — hardcoding is the design, comments carry the derivation rationale; special tokens ($$SINGLETON$$, :same_as_receiver) form a closed vocabulary the loader understands.
**Probe:** EXECUTED byte-exact: `ruby -ryaml -e 'YAML.load_file(...)'` — all three parse (psych): ruby keys=[class_types, method_types, block_variable_types]; rails adds dynamic_members(5); rspec carries 2 class_type remaps + variant lists. Coverage no_recorded_issue ×3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", query: "code insight yaml dynamic extensions", limit: 10 });
```

## Verdict
Adopt: move unresolvable-by-analysis type facts into per-framework declarative tables with a closed semantic-token vocabulary and rationale comments. Adapt: table schema to your inference engine's query points. Omit: facts derivable from source analysis (keep data plane minimal).
