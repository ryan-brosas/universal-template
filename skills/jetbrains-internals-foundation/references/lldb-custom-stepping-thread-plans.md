<!-- capsule-v2 -->
# LLDB custom stepping thread plans — why would a debugger replace native step-in/step-over with its own thread plans?

**Source:** JetBrains Rider installed build `RD-262.8665.400` (`plugins/cidr-debugger-plugin/bin/lldb/helpers/jb_lldb_stepping.py`, 450L whole, 12 classes; `stepping/` support package); Codebase Memory `jetbrains-rider`. **Question:** When does stock debugger stepping break on real-world binaries, and what plan structure fixes each case without forking the engine?

## The plan ladder as the decisive instance
**Path/Symbol:** module docstring (:9-17) enumerates the reasons; class ladder :29-443 — StepThroughInstruction, StepOverInstruction(DelegateStep), StepLineBase→StepOverLineBase→{StepOverLine, StepOverLineForce}, {StepInLine, StepInLineForce}, SpecialLinesGuardThreadPlan, NonLocalGotoReturnGuardThreadPlan, NonLocalGotoDispatchGuardThreadPlan, StepIn, StepOver.
**Signature:** plans implement `explains_stop(event: lldb.SBEvent) -> bool` + `should_stop(event) -> bool` over AbstractThreadPlanWithLazyContext.
**Data Shape:** support package stepping/: abstract_scripted_thread_plan, abstract_thread_plan_with_lazy_context (+@with_reset_context decorator), delegate_step, instructions_reader, line_spec, address_range.

### Decisive source
```python
"""
Why do we need custom stepping? This is kind of a mystery.

Here are the known reasons:
- MSVC C++ exceptions: The NonLocalGotoDispatchGuardThreadPlan and NonLocalGotoReturnGuardThreadPlan plans handles C++ exception.
- Incremental linkage: For some reason, the native LLDB StepInto cannot step into a function if the binary is built with
                       the incremental linkage (see https://youtrack.jetbrains.com/issue/CPP-36647).
- Magic line numbers: The SpecialLinesGuardThreadPlan plan handles the magic line numbers
                      (see llvm-project/llvm/include/llvm/DebugInfo/CodeView/Line.h:24).

There may be other unknown use cases. If you find any, please add them to the list!
"""
...
class StepThroughInstruction(AbstractThreadPlanWithLazyContext):
    def explains_stop(self, event: lldb.SBEvent) -> bool:
        return self.thread.GetStopReason() == lldb.eStopReasonTrace

    @with_reset_context
    def should_stop(self, event: lldb.SBEvent) -> bool:
        if self.top_frame.GetPC() == self.start_pc:
            return False
```

**Flow:** each user-visible step maps to a DelegateStep composition: instruction-level plans watch PC movement (should_stop False until PC leaves start_pc); line-level plans read instructions via InstructionsReader to find line boundaries; guard plans (SpecialLines/NonLocalGoto×2) intercept the specific stop-reason cases MSVC/CodeView binaries produce and resume transparently.
**Invariant:** custom plans must ANSWER explains_stop honestly for their case only — multiple scripted plans coexist per thread and the first explainer owns the stop; every plan resets its lazy context between stops (@with_reset_context) because SBThread/plan lifetimes do not persist across stops. Wrong port: keeping state on the plan object across stops — it will act on a stale frame after the next breakpoint.
**Probe:** structural GREEN: `grep -n '^class ' jb_lldb_stepping.py | wc -l` → 12; docstring reason list quoted verbatim above (read directly); stepping/ package inventory (7 files) listed. Behavioral execution requires a live LLDB host process — NOT available in this environment; recorded as infrastructure block per gate rules, no fabricated pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", name_pattern: ".*StepThroughInstruction.*", limit: 4 });
// -> ...jb_lldb_stepping.StepThroughInstruction Class 29-47
```

## Verdict
Adopt: keep an explicit, documented LIST of why each custom plan exists (the docstring pattern), implement plans as stateless-per-stop explainers, compose via delegation. Adapt plan set to your engine's stop reasons. Omit LLDB script binding details unless embedding Python into LLDB.