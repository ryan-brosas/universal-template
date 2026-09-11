<!-- capsule-v2 -->
# Ruby stub & signature versioned planes — what exactly ships as a per-interpreter-version offline API dictionary?

**Source:** JetBrains installed distribution (proprietary install) RubyMine Linux `dist@262.9437.192`; Codebase Memory `jetbrains-rubymine`. **Question:** How are per-version core/stdlib API surfaces packaged, pinned, and kept distinguishable from real code?

## Two parallel data planes: .rb behavior stubs + .rbs typed signatures
**Path/Symbol:** `plugins/ruby/rubystubs/rubystubs{18..40}/` (16 dirs, ~135→125 files each); `plugins/ruby/rubysigs/rubysigs{18..40}/{core,stdlib}/` (16 dirs; core 48→62 .rbs; stdlib 58→61 gem dirs as <gem>/<version>/*.rbs; 3,784 .rbs total); markers `rubysigs*/{rbs-version,ruby-version}`.
**Signature:** n/a (data planes; producer = ruby-stub-generation-pipeline capsule).
**Data Shape:** stubs: underscored class-per-file, doc comments verbatim, empty bodies, CONST = _. sigs: RBS with provenance comments (`# <!-- rdoc-file=array.c -->`); ZERO-BYTE marker files pin snapshot identity by existence.

### Decisive source
```ruby
# rubystubs31/array.rb :454-500 — parseable, body-less, self-documenting
def self.[](*args) end
def initialize(...) end
# rubystubs31/global_variables.rb :4-16 — DATA catalog, intentionally NOT valid code
$! = _
$& = _
# rubysigs31/core/array.rbs :1-2 — RBS with RDoc provenance
# <!-- rdoc-file=array.c -->
# An Array object is an ordered, integer-indexed collection of objects...
```

**Flow:** SDK attach selects the plane matching interpreter version → stubs give navigation/completion shape → .rbs gives types → markers let tooling verify which snapshot loaded.
**Invariant:** every stub file parses under `ruby -c` EXCEPT global_variables.rb in EVERY version (read-only specials `$& $' $~` encoded as unassignable pseudo-assignments — presence signals data-not-code); version identity lives in directory NAME + empty marker files, not file contents.
**Probe:** EXECUTED byte-exact: `ruby -c <file>` census — rubystubs18 134/135 OK, 27 149/150, 31 138/139, 40 124/125; sole failure global_variables.rb everywhere (first census used invalid flag --syntax-check and silently misfired — repaired to -c). Marker emptiness via od -c (zero bytes). Probe env lacks rbs gem → RBS validation BLOCKED, recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", query: "thread main rubystubs", limit: 10 });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-rubymine", paths: ["plugins/ruby/rubystubs/rubystubs31/array.rb", "plugins/ruby/rubysigs/rubysigs31/core/array.rbs"] });
```

## Verdict
Adopt: ship per-version dictionaries as parseable-but-empty code plus a parallel typed layer; pin snapshots by existence-markers; keep one intentional non-parseable catalog file only when encoding unassignable entities. Adapt: version granularity to your release cadence. Omit: regenerating inside the product (generator is dev-time).
