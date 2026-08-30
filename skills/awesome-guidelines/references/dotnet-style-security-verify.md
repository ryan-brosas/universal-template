<!-- capsule-v2 -->
# Security and verification — is the library free of legacy sandbox APIs and analyzer-clean?

**Source:** Secure coding guidelines for .NET; FDG digest FxCop/CLS. **Question:** Do new components avoid deprecated trust models and validate untrusted input?

## Security seam
**Path/Symbol:** .NET libraries, interop wrappers, apps accepting external input.
**Signature:** no CAS/APTCA/partial trust; no binary formatters/Remoting; explicit resource checks.
**Data Shape:** process/container isolation; demand/assert on resource gateways.

### Decisive pattern
```csharp
// Library exposing file access — demand before use, clear errors
public sealed class SafeFileStore
{
    public void Write(string path, ReadOnlySpan<byte> content)
    {
        ArgumentException.ThrowIfNullOrEmpty(path);
        if (path.Contains("..", StringComparison.Ordinal))
            throw new ArgumentException("Path traversal rejected.", nameof(path));
        // demand/check OS permissions, then write
    }
}
```

**Flow:** do not use Code Access Security, partial trust, `AllowPartiallyTrustedCallers`, .NET Remoting, DCOM, or binary formatters in new code → rely on OS/process/container isolation for untrusted code boundaries → treat security-neutral library code as callable by potentially malicious callers — validate untrusted Internet/external input → for native interop wrappers, avoid granting unmanaged code rights to all callers; scope elevation to wrapper with verification → when library exposes protected resources (files, network, unmanaged), demand appropriate permissions before operations → application-only code may be simpler but still harden external input paths → mark assemblies `[CLSCompliant(true)]` when shipping reusable libraries → run Roslyn analyzers / FxCop-style rules on public API (naming, design, security) in CI.
**Invariant:** BinaryFormatter usage, APTCA on new library, or unvalidated path/input from external source fails security review.
**Probe:** banned API grep (`BinaryFormatter`, `AllowPartiallyTrustedCallers`); analyzer/security audit CI; CLS attribute on library projects.

## Verify seam
**Flow:** `dotnet build` with analyzers; optional `dotnet format`; unit tests on security-sensitive paths.
**Invariant:** analyzer warning suppression on new public API without documented rationale fails verify gate.
**Probe:** CI analyzer/treat-warnings-as-errors output on changed projects.

## Verdict
Modern isolation over CAS, no legacy serializers/remoting, input validation, CLS + analyzers on libraries. Learning note: `dotnet-style-learning-note.md`.
