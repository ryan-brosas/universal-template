<!-- capsule-v2 -->
# .NET interop — does the vanilla public API feel native to C#?

**Source:** Microsoft guidelines §libraries for other .NET Languages; Appendix RadialPoint. **Question:** Would a C# consumer see `Func`, `IEnumerable`, TryGetValue—not F# artifacts?

## Interop seam
**Path/Symbol:** public types intended for any .NET language (NuGet, SDK).
**Signature:** namespaces + classes; `Func`/`Action`; `IEnumerable<T>`; `Task<T>`.
**Data Shape:** null guards at boundary; overloads not option args.

### Decisive pattern
```fsharp
namespace Fabrikam.Analytics

open System

type MetricsService() =
    member _.TryGetMetric(name: string, value: byref<float>) =
        match lookup name with
        | Some v ->
            value <- v
            true
        | None -> false

    member _.ComputeAsync(input: seq<int>, transform: Func<int, int>) =
        input
        |> Seq.map (fun x -> transform.Invoke x)
        |> Seq.sum
        |> Async.singleton
        |> Async.StartAsTask

    static member Add(x: int, y: int) = x + y

    static member Add(x: int, y: int, z: int) = x + y + z
```

**Flow:** public files use `namespace` only — no public F# modules → utility APIs as `[<AbstractClass; Sealed>]` static classes → replace F# function types with `Func`/`Action` in public members → return `seq<T>`/`IEnumerable<T>` not `list` → expose async as `Task` via `Async.StartAsTask` with optional `CancellationToken` → use TryGetValue bool+`byref` instead of `option` returns → use overloads instead of optional parameters → avoid tuple returns and currying → check null at boundary (`nullArg`, F# 9 `| null`) → hide unions with private cases + static factory members → decorate extension methods with `[<Extension>]` and host in static class → apply `[<CompiledName("Create")>]` only when F# naming must differ for .NET.
**Invariant:** public `list<'T>`, `option` in signature, curried member, naked DU cases, or `FSharpFunc` in C# view fails interop review.
**Probe:** build C# consumer snippet; ildasm/reflect public signatures; Fantomas + `dotnet build`.

## Event seam
```fsharp
type Sensor() =
    let ev = Event<EventHandler<SensorEventArgs>>()

    [<CLIEvent>]
    member _.ReadingChanged = ev.Publish
```

**Flow:** `[<CLIEvent>]` on `DelegateEvent<EventHandler<_>>`, not bare `Event<_>`.
**Invariant:** F# `Event<'T>` without CLIEvent on vanilla API fails review.
**Probe:** C# `+=` subscription compile test.

## Verdict
Namespace/class façade, BCL types, TryGetValue, Task, null-safe boundaries. Learning note: `fsharp-style-learning-note.md`.
