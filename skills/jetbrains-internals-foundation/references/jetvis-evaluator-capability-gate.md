<!-- capsule-v2 -->
# JetVis evaluator capability gate — how do you opt a debugger expression engine in only where the host actually provides it?

**Source:** JetBrains Rider installed build `RD-262.8665.400` (`plugins/cidr-debugger-plugin/bin/lldb/helpers/renderers/jb_lldb_jetvis_proxy.py`, 144L whole); Codebase Memory `jetbrains-rider`. **Question:** What is the safe enablement contract for a custom fast-path evaluator that may be absent from some host builds?

## JetvisProxy._ENABLED as the decisive instance
**Path/Symbol:** `jb_lldb_jetvis_proxy.py:JetvisProxy._ENABLED` (:15), evaluate_expression_on_stack_frame (:39-49), initialize_expr_variables_by_names (:51+).
**Signature:** `_ENABLED = hasattr(lldb, "SBJetvisEvaluator") and str_to_bool(os.environ.get("LLDB_USE_JETVIS_EXPRESSION_EVALUATOR", "1"))`; env default ON.
**Data Shape:** evaluation returns SBValue plus a separate SBJetvisWarnings collection walked by index; variables bundle initialized from parallel name/initializer lists.

### Decisive source
```python
class JetvisProxy:
    _ENABLED = hasattr(lldb, "SBJetvisEvaluator") and str_to_bool(os.environ.get("LLDB_USE_JETVIS_EXPRESSION_EVALUATOR", "1"))
...
@classmethod
def evaluate_expression_on_stack_frame(cls, frame: lldb.SBFrame, expression: str) -> lldb.SBValue:
    evaluation_warnings = lldb.SBJetvisWarnings()
    evaluation_result = lldb.SBJetvisEvaluator.EvaluateExpressionOnStackFrame(frame, expression, expression, evaluation_warnings)
    cls._report_warnings(evaluation_warnings)
    if evaluation_result.IsValid() and evaluation_result.GetError().Success():
        static_value: lldb.SBValue = evaluation_result.GetStaticValue()
        static_value.SetPreferDynamicValue(lldb.eDynamicDontRunTarget)
        return static_value
    return evaluation_result
```

**Flow:** at import, capability is detected structurally (does the lldb module expose SBJetvisEvaluator?) AND env must not veto (default '1') → every downstream consumer (natvis_loader passes JetvisProxy.is_enabled() into parsing so JetVis-only intrinsics are skipped when off) branches through one predicate → results flow back with warnings reported separately, static values forced dynamic-capable but without running target code.
**Invariant:** feature-detect precedes env: absence of the symbol disables regardless of env, presence respects the user veto; ONE predicate is the single source of truth consumed even by the PARSER (intrinsics are not registered when disabled), not just by evaluation call sites. Warnings never abort evaluation — they log through RENDER_LOG children. Wrong port: try/except ImportError gating — the evaluator lives INSIDE the already-imported lldb module, so import cannot fail independently.
**Probe:** deterministic content probe GREEN: `grep -n 'hasattr(lldb' jb_lldb_jetvis_proxy.py` → :15 capability line; `grep -rn 'SBJetvisEvaluator\|JetvisProxy.is_enabled' bin/lldb/helpers --include='*.py' -l` lists consumers incl. renderers/jb_lldb_natvis_formatters.py + jb_lldb_top_level_lazy_declarations.py. Live LLDB execution unavailable here — recorded infrastructure block; no fabricated behavioral pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", name_pattern: ".*JetvisProxy.*", limit: 6 });
// -> ...renderers.jb_lldb_jetvis_proxy.JetvisProxy Class 14-144
```

## Verdict
Adopt: hasattr-capability AND env-veto (default-on) evaluated once at import, threaded through BOTH registration and call sites as one predicate. Adapt the symbol/env pair. Cross-reference: `LLDB_USE_JETVIS_EXPRESSION_EVALUATOR` and `LLDB_NATVIS_PRIORITIZE_CPP_BUILTIN_FORMATTERS` are the two shipped knobs of this plane (env census, graph EnvVar nodes).