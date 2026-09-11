<!-- capsule-v2 -->
# Ruby stdlib stub generation pipeline — how do you regenerate an offline API surface for a dynamic language from its C sources?

**Source:** JetBrains installed distribution (proprietary install) RubyMine Linux `dist@262.9437.192`; Codebase Memory `jetbrains-rubymine`. **Question:** What pipeline turns ruby interpreter sources into parseable offline stubs, and where does it degrade gracefully?

## Forked-RDoc generator with call-seq parameter extraction
**Path/Symbol:** `plugins/ruby/rb/stubsgen/gen_stubs.rb` (43L entry), `our_rdoc.rb` (152L), `rb_generator.rb` (247L emitter), `call_seq/call_seq_def_parser.rb` (235L), `options.rb`, `settings.rb`; vendored gems `stubsgen/gems/gems/rdoc-{3.9.4,6.0.2}`.
**Signature:** `RDoc::RDoc#document(argv)` reopened; `Generators::RBGenerator.for(options)`; `params_from_call_seq(method)` / `_params_from_call_seq(method_name, call_seq_string)`.
**Data Shape:** output = one underscored `.rb` per top-level class/module; constants emitted as `CONST = _`; methods one-line `def [self.]name(params); end`; degradation ladder (*several_variants) → patched C params → (*smth).

### Decisive source
```ruby
# gen_stubs.rb :3-9 — dual vendored rdoc by target ruby era
rdoc_version = if RUBY_VERSION < '2.3.0' then '3.9.4' else '6.0.2' end
$:.unshift(File.expand_path("./gems/gems/rdoc-#{rdoc_version}/lib", File.dirname(__FILE__)))
# our_rdoc.rb :32 — only C core sources (+ root prelude *.rb minus golf_prelude)
file_list << rel_file_name.sub(/^\.\//, '') if rel_file_name =~ /\.c/
# options.rb :9-13 — plug custom generator into RDoc's registry
def parse(argv)
  old_parse argv
  @op_dir = $DIRECTORY; @generator_name = 'rb'
end
# rb_generator.rb :136 — placeholder constant body
@file << "#{constant.name} = _\n"
```

**Flow:** CLI (-d source dir, -o out, -s version id) → pick rdoc twin → RDoc parses .c + prelude → RBGenerator walks unique top-level classes/modules → emits comments, superclass (unless Object), includes, constants-as-underscore, private-partitioned methods, alias lines → call-seq prose parsed into parameter lists with operator hacks ([] []= backtick).
**Invariant:** stubs are PARSEABLE Ruby with EMPTY bodies (offline resolution surface only, zero behavior); unknown/multi signatures collapse down a visible ladder rather than lying; the generator itself is shipped so the data plane is REGENERABLE, not frozen artifacts.
**Probe:** EXECUTED byte-exact (`ruby -I .../stubsgen/call_seq -e 'require "call_seq_def_parser"; puts _params_from_call_seq(...)'`): sub two-variant → `(*several_variants)`; `[]` operator → ` i`; block-form each → empty string; no-match → `(...)`. Full regeneration BLOCKED in probe env (needs ruby source tree + old rubies) — recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", name_pattern: ".*(gen_stubs|rb_generator|our_rdoc|call_seq_def_parser).*", limit: 12 });
```

## Verdict
Adopt: ship the generator beside generated data; derive parameters from documentation call-seqs first with C prototypes as fallback; make every ambiguity a named sentinel. Adapt: rdoc version split points to your language's doc-tool history. Omit: rdoc HTML machinery beyond what the custom generator consumes.
