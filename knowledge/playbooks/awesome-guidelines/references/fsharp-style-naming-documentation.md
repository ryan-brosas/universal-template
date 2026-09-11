<!-- capsule-v2 -->
# Naming and documentation — does the public surface follow .NET conventions?

**Source:** Microsoft F# component design guidelines §Naming, General. **Question:** Will F# and C# consumers recognize names and get IntelliSense?

## Naming seam
**Path/Symbol:** public types, members, modules in library `.fs` files.
**Signature:** PascalCase types/methods; camelCase parameters; XML `///` docs.
**Data Shape:** `.fsi` optional for frozen APIs.

### Decisive pattern
```fsharp
/// A point in polar coordinates.
type RadialPoint(angle: float, radius: float) =

    /// Angle from the x-axis, in radians.
    member _.Angle = angle

    /// Distance from the origin.
    member _.Radius = radius

    /// Scale radius by FACTOR.
    member _.Stretch(factor: float) =
        RadialPoint(angle, radius * factor)
```

**Flow:** follow .NET Library Design Guidelines table → PascalCase for types, union cases, methods, properties → camelCase parameters → avoid abbreviations in public components → PascalCase generic params (`T`, `Key`, `Value`) → add `///` XML on every public type/member → when API stabilizes, add `.fsi` to lock public surface and separate docs from implementation.
**Invariant:** `pCoord`, case-only name collisions, or undocumented public API on NuGet libraries fails review.
**Probe:** Fantomas + dotnet build XML doc warnings; `.fsi` diff when present.

## Module naming seam
**Flow:** F#-facing — camelCase module functions when keyword-like (`List.map` style) or PascalCase when consumed from C# → vanilla .NET libraries — types in namespaces, not public module values.
**Invariant:** public utility `module` with camelCase helpers in a cross-language NuGet package fails review.
**Probe:** reflect public API from C# stub consumer; grep `^module` in public namespace files.

## Verdict
.NET naming, XML docs, optional `.fsi` for stable libraries. Learning note: `fsharp-style-learning-note.md`.
