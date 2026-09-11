<!-- capsule-v2 -->
# SimpleCov coverage plane — how does an IDE hijack coverage capture AND rendering without forking SimpleCov?

**Source:** JetBrains installed distribution (proprietary install) RubyMine Linux `dist@262.9437.192`; Codebase Memory `jetbrains-rubymine`. **Question:** How do you redirect a coverage tool's result storage and report generation to IDE-chosen paths with merge safety?

## Run-side starter + render-side generator over one resultset contract
**Path/Symbol:** `plugins/ruby/simplecov_starter.rb` (78L, run-side); `plugins/ruby/rb/report/simplecov_generator.rb` (42L, render-side).
**Signature:** `SimpleCov::ResultMerger.resultset_path` overridden to ENV/ARGV path; generator argv positions [0]=resultset, [1]=HTML out, [3]=version requirement.
**Data Shape:** ENV: RUBYMINE_SIMPLECOV_COVERAGE_PATH, RUBYMINE_SIMPLECOV_RUN_CONFIGURATION, RUBYMINE_SIMPLECOV_MERGING, indexed RUBYMINE_SIMPLECOV_EXCLUDE_0..n, ENABLE_BRANCH_COVERAGE, ENABLE_FORKED_COVERAGE + message-carrying warning envs.

### Decisive source
```ruby
# simplecov_starter.rb — rbenv gemset runs must not double-instrument (RUBY-17641)
def check_rbenv_gemset; `rbenv which gem`.strip == $0; rescue; false; end
unless check_rbenv_gemset
  require 'simplecov'
  # trick ResultMerger into using the provided output file
  module SimpleCov::ResultMerger
    def self.resultset_path; ENV['RUBYMINE_SIMPLECOV_COVERAGE_PATH']; end
  end
  SimpleCov.track_files "#{Dir.getwd}/**/*.rb"   # include "0% covered" files
  SimpleCov.command_name "#{SimpleCov.project_name}:#{Process.pid.to_s}"  # merge-safe per process
  patterns << pattern[1..-2] if pattern[0] == "/" && pattern[-1] == "/"  # /re/ env syntax

# simplecov_generator.rb — render side
module SimpleCov::ResultMerger
  def self.resultset_path; ARGV[0]; end
end
SimpleCov.merge_timeout(60 * 60 * 24 * 31)   # one month retention
result = SimpleCov::ResultMerger.merged_result
result.format!
```

**Flow:** test boot loads starter → guard skips gemset-managed runs → merger redirected to IDE path → process tags results name:pid → at_exit forces result materialization → later, generator process re-points merger at the same file, merges, renders HTML to ARGV[1].
**Invariant:** command_name MUST embed pid (merge collisions otherwise drop processes); resultset_path is THE single redirection seam on both sides; exclude ladder accepts literal or /slash-delimited regex/; capability checks degrade with env-carried messages instead of failing the run.
**Probe:** Behavioral probe BLOCKED honestly (no simplecov gem in probe env). Deterministic evidence: whole-file reads; both files graph-indexed no_recorded_issue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", query: "simplecov coverage result merger", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", name_pattern: ".*simplecov.*", limit: 10 });
```

## Verdict
Adopt: override the tool's own path-resolution seam (never patch writers); pid-suffixed command names; positional-argv renderer contract. Adapt: exclusion env grammar and warning channels to your host. Omit: rcov legacy constants in runner_settings (dead era).
