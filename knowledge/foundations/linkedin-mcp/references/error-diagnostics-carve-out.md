<!-- capsule-v2 -->
# Error-class diagnostics carve-out — which errors deserve incident diagnostics and which deserve only their correction?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How should a tool-error handler separate "reportable defect" from "caller-correctable input"?

## Subclass-ordered ladder; correction-bearing types bypass issue diagnostics
**Path/Symbol:** `linkedin_mcp_server/error_handler.py` — InvalidReferenceError arm (:260), catch-all ordering; sibling redaction/proxy arms upstream in the same chain.
**Signature:** handler takes the domain exception + MCP `ctx`, converts to `ToolError(str(exception))`; every arm re-raises as ToolError with the user-facing message.
**Data Shape:** Domain exceptions carry their own remediation text (`InvalidReferenceError` embeds the exact correction, e.g. 'Pass the /company/ slug, for example "microsoft"').

### Decisive source
```text
    elif isinstance(exception, InvalidReferenceError):
        # Ahead of the catch-all, which it subclasses. No issue diagnostics: a
        # reference the caller can correct is not a bug worth reporting, and an
        # issue template appended to it buries the correction it already names.
        logger.info("Invalid reference%s: %s", ctx, exception)
        raise ToolError(str(exception)) from exception

Design rule extracted: message decoration is a FUNCTION OF ERROR CLASS, not a
global policy. Two failure vocabularies share one transport:
- Defect-shaped failures (unexpected states, internal errors) → append issue
  diagnostics/template so users can report them.
- Input-shaped failures (validation with embedded remediation) → pass the
  message through VERBATIM at info level. Appending boilerplate buries exactly
  the instruction the user needs.

The isinstance order is load-bearing: InvalidReferenceError subclasses the
generic LinkedInMCPError, so the specific arm must precede the catch-all or it
is unreachable and every validation slip gets incident scaffolding.

Consistent with the codebase's wider logging discipline (drivers/browser.py,
daemon_owner.py): anything that reaches an issue report or a pasted log is
redacted first (redact_proxy_credentials), while correction text is meant to be
read by the caller NOW and carries nothing sensitive.
```

**Flow:** tool raises domain error → handler walks class-specific arms (specific before general) → defect classes gain diagnostics; correctable-input classes log info and surface the bare correction via ToolError.
**Invariant:** A subclass-specific arm must appear before any arm matching its ancestor, and error-message enrichment must never bury caller-actionable text under report templates.
**Probe:** `grep -c 'InvalidReferenceError' linkedin_mcp_server/error_handler.py` → 2; direct tests: `tests/test_error_handler.py::test_invalid_reference_surfaces_the_correction_verbatim` (:227), `test_invalid_reference_skips_issue_diagnostics` (:243).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "_start_login_if_needed go_auth_quiescent superseded", limit: 5 });
```

## Verdict
Adopt class-keyed error decoration with verbatim passthrough for self-descriptive validation errors in any MCP/CLI error boundary. Adapt your taxonomy of defect-vs-input failures. Omit this repo's specific exception tree.
