<!-- capsule-v2 -->
# Ruby TeamCity service-message factory — how are test events encoded so IDE and buildserver parsers stay in sync?

**Source:** JetBrains installed distribution (proprietary install; Apache-2.0 headered helpers) RubyMine Linux `dist@262.9437.192`; Codebase Memory `jetbrains-rubymine`. **Question:** What is the wire contract for Ruby test events, and which seams let tests fake/mock it deterministically?

## MessageFactory over ##teamcity[...] with mode + mock seams
**Path/Symbol:** `plugins/ruby/rb/testing/patch/common/teamcity/utils/service_message_factory.rb` (`Rake::TeamCity::MessageFactory`, 308L); `.../teamcity/rakerunner_consts.rb:80-128` (mode + debug-option predicates). Companion to leaf capsule teamcity-message-grammar (wire vocabulary): THIS is the Ruby-side producer.
**Signature:** `create_test_failed(name, message, stacktrace, node_id = nil, expected = nil, actual = nil, print_expected_and_actual = true)`; private core `create_message(msg_attrs)`; `replace_escaped_symbols(text)`.
**Data Shape:** attr-hash rendered as `key = 'value'` pairs; nil diagnostic dropped; nil details/errorDetails/locationHint/duration dropped when their mock spec has remove_empty; auto timestamp in Java SimpleDateFormat with GMT offset.

### Decisive source
```ruby
# :107 comparisonFailure upgrade
if expected != nil && actual != nil
  attrs[:type] = 'comparisonFailure'; attrs[:expected] = expected; attrs[:actual] = actual
end
# :215 escape order matters — pipe FIRST
copy_of_text.gsub!(/\|/, "||"); copy_of_text.gsub!(/'/, "|'"); copy_of_text.gsub!(/\n/, "|n")
copy_of_text.gsub!(/\r/, "|r"); copy_of_text.gsub!(/\]/, "|]"); copy_of_text.gsub!(/\[/, "|[")
# UTF-8-guarded unicode ladder :229-232 (ESC |0x001b, NEL |x, LS |l, PS |p)
# rakerunner_consts.rb :84 — TEAMCITY_VERSION non-empty => buildserver mode
def self.is_in_buildserver_mode
  version = ENV[TEAMCITY_VERSION_KEY]
end
```

**Flow:** reporter → MessageFactory.create_* → format_stacktrace_if_needed (buildserver mode folds stacktrace INTO details per TW-6270; IDE mode keeps attributes separate) → create_message escapes values → one flushed stdout line.
**Invariant:** escape pipe before anything else; error vs failure distinguished ONLY by the `error='true'` attribute; enteredTheMatrix heartbeat distinguishes attached-with-zero-tests from never-attached; debug-option substring flags (fake_time/fake_stacktrace/fake_error_msg/fake_location_url in `TEAMCITY_RAKERUNNER_DEBUG_OPTIONS`) swap values for ##PLACEHOLDER## so grammar tests need no clocks.
**Probe:** EXECUTED byte-exact (`ruby -I .../testing/patch/common -e 'require "teamcity/utils/service_message_factory"; …'`):
```
create_test_failed("test_foo","Expected: 1\nActual: 2","app.rb:4","MyTest.test_foo","1","2")
→ ##teamcity[testFailed name = 'test_foo' message = 'Expected: 1|nActual: 2' details = 'app.rb:4'
   nodeId = 'MyTest.test_foo' type = 'comparisonFailure' expected = '1' actual = '2'
   printExpectedAndActual = 'true' timestamp = '2026-08-25T15:14:03.524+0800']
escaping sample input "pipe | quote ' brack [x]" → text = 'pipe || quote |' brack |[x]'
TEAMCITY_VERSION=9.1 … create_test_failed("t","msg","trace_line","N.t") → details = 'msg|n|nStack trace:|ntrace_line' (folded)
TEAMCITY_VERSION=9.1 TEAMCITY_RAKERUNNER_DEBUG_OPTIONS=fake_time … create_test_finished("t",1234,nil,"N.t")
→ duration = '##DURATION##' … timestamp = '##TIME##'
```
Probe defect repaired en route: first attempt used wrong key TEAMCITY_RAKE_RUNNER_DEBUG_OPTIONS — mock silently inert; correct key is RAKERUNNER.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", query: "teamcity utils service message factory create_test_failed", limit: 10 });
```

## Verdict
Adopt: one producer module per language funneling every event through a single escaping+attr-render core; env-keyed mode detection; placeholder-mock seams for deterministic tests. Adapt: timestamp format and fold-workaround to your consumer. Omit: legacy buildserver RPC logger constants (file marks them deprecated). Coverage: no_recorded_issue both files.
