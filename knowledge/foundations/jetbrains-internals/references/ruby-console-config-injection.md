<!-- capsule-v2 -->
# IRB/Pry console config injection — how does an IDE reshape interactive REPLs it does not own?

**Source:** JetBrains installed distribution (proprietary install) RubyMine Linux `dist@262.9437.192`; Codebase Memory `jetbrains-rubymine`. **Question:** How do you force uniform prompts/IO behavior onto irb AND pry from outside, including inside Rails app boot?

## Config-file reopen layer + Railtie activation + bundler parity guard
**Path/Symbol:** `plugins/ruby/rb/consoles/{common_config,irb_config,pry_config,rails_config}.rb`; wrappers `consoles/exec/{irb,pry}`; sidecar `pry_prompt_descr.txt`. Graph: search_graph name_pattern ".*(irb_config|pry_config|rails_config|common_config).*" line-resolves all.
**Signature:** `IRB.setup(ap_path)` aliased post-hook; `Pry#initialize(options = {})` reopened; `RubyMine::Railtie < Rails::Railtie` initializer 'rubymine.configure_consoles'.
**Data Shape:** RM prompt = `{ PROMPT_I:'>>', PROMPT_S/C/N:'?>', RETURN:'=> %s\n' }`; Pry procs ['>>', '?>'] named 'RM'; descriptor sidecar is one human-readable line ("Simple {>>|?>} prompt for Pry Run Configurations").

### Decisive source
```ruby
# common_config.rb — load-path parity when user ran bundle exec
require 'bundler/setup' if (ENV['RUBYOPT'] || '').include?('bundler/setup')

# irb_config.rb :8-18 — alias-chain setup, then flatten the REPL
def setup(ap_path)
  orig_setup ap_path
  conf[:PROMPT][:RM] = { PROMPT_I: '>>', PROMPT_S: '?>', PROMPT_C: '?>', PROMPT_N: '?>', RETURN: "=> %s\n" }
  conf[:PROMPT_MODE] = :RM
  conf[:AUTO_INDENT] = conf[:USE_COLORIZE] = conf[:USE_MULTILINE] = false
  conf[:ECHO_ON_ASSIGNMENT] = true; conf[:USE_PAGER] = conf[:USE_AUTOCOMPLETE] = false
end
# irb_config.rb :21-33 — EOF tolerance only where needed (version-gated prepend)
def eof?
  if !IRB.const_defined?(:VERSION) || Gem::Version.new(IRB::VERSION) < Gem::Version.new("1.3.0")
    false # ignore EOF — keeps piped stdio REPL alive
  else super end
end
# pry_config.rb :12-24 — bypass captured globals by duping real FDs
output = IO.open(STDOUT.to_i, 'w'); output.sync = true
input  = IO.open(STDIN.to_i); input.echo = false if input.isatty
# rails_config.rb — activation inside Rails boot, pry optional
initializer 'rubymine.configure_consoles' do
  require_relative 'irb_config'
  begin; require_relative 'pry_config'; rescue LoadError => _; end
end
```

**Flow:** IDE launches exec/irb (IRB.start __FILE__) or exec/pry ($0='pry' rename + Pry::CLI.start) with config preloaded → common_config mirrors bundler → configs reopen library classes BEFORE first prompt → under Rails, railtie initializer applies the same configs during app boot instead.
**Invariant:** never replace the REPL binary — reopen its setup/init seam; disable every TUI affordance (color/pager/auto-indent/completions) because the IDE renders; dup raw FDs so IDE piping survives library $stdout capture; feature-detect version branches (Prompt.respond_to?(:new); IRB<1.3.0 EOF mixin).
**Probe:** Behavioral irb probe BLOCKED honestly (probe env lacks the irb gem; ruby itself warns irb leaves default gems in Ruby 4.0). Deterministic evidence: full-file reads above; extension-less exec/irb+exec/pry are index not_tracked → cited from direct reads; consoles/*.rb all no_recorded_issue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", name_pattern: ".*(irb_config|pry_config|rails_config|common_config).*", limit: 10 });
```

## Verdict
Adopt: reopen-the-seam + FD duplication + respond_to? version gates + sidecar human-readable prompt descriptor; railtie-style activation for framework contexts with optional-dependency swallow. Adapt: prompt glyphs/modes to your host UI contract. Omit: specific IRB/Pry internals once versions move past the gates shown.
