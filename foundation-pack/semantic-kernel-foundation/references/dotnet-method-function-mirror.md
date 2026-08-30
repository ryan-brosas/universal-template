<!-- capsule-v2 -->
# .NET method-function mirror — type-driven reserved params, injected defaults, JSON-deserialize coercion ladder

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Which of the Python plane's method-binding invariants (reserved-parameter injection, argument coercion, result normalization) are language-universal, and where does the .NET twin deliberately diverge?

## KernelFunctionFromMethod parameter marshaling
**Path/Symbol:** `dotnet/src/SemanticKernel.Core/Functions/KernelFunctionFromMethod.cs:KernelFunctionFromMethod.GetParameterMarshalerDelegate` (lines 616–776), with `TryToDeserializeValue` (788–819), `GetReturnValueMarshalerDelegate` (824–1007), `GetMethodDetails` (487–587). Coverage caveat: this file is whole-file parse-partial in the graph — all claims below come from a direct read, not graph constructs.
**Signature:** `private static (Func<KernelFunction, Kernel, KernelArguments, CancellationToken, object?>, KernelParameterMetadata?) GetParameterMarshalerDelegate(MethodInfo method, ParameterInfo parameter, ref bool sawFirstParameter, JsonSerializerOptions? jsonSerializerOptions)`.
**Data Shape:** Each method parameter compiles at construction time into a static accessor delegate plus an optional `KernelParameterMetadata` view; reserved parameters return a null view so they are never advertised in the function metadata.

### Decisive source
```csharp
// Reserved params are TYPE-DRIVEN and never appear in metadata (parameterView == null):
if (type == typeof(KernelFunction)) { return ((func, _, _, _) => func, null); }
if (type == typeof(Kernel))         { return ((_, kernel, _, _) => kernel, null); }
if (type == typeof(KernelArguments)){ return ((_, _, arguments, _) => arguments, null); }
// ... ILoggerFactory, ILogger, IAIServiceSelector, CultureInfo/IFormatProvider, CancellationToken ...
if (parameter.GetCustomAttribute<FromKernelServicesAttribute>() is FromKernelServicesAttribute fromKernelAttr)
{ /* keyed-DI resolve; parameter default fallback; else throw KernelException */ }

object? parameterFunc(KernelFunction _, Kernel kernel, KernelArguments arguments, CancellationToken __)
{
    // 1. Use the value of the variable if it exists.
    if (arguments.TryGetValue(name, out object? value)) { return Process(value); }
    // 2. Otherwise, use the default value if there is one.
    if (parameter.HasDefaultValue) { return parameter.DefaultValue; }
    // 3. Otherwise, fail.
    throw new KernelException($"Missing argument for function parameter '{name}'", ...);

    object? Process(object? value)
    {
        if (type.IsAssignableFrom(value?.GetType())) { return value; }
        if (converter is not null && value is not (JsonElement or JsonDocument or JsonNode))
        { try { return converter(value, kernel.Culture); } catch (Exception e) when (!e.IsCriticalException())
          { throw new ArgumentOutOfRangeException(name, value, e.Message); } }
        if (value is JsonElement element && element.ValueKind == JsonValueKind.String
            && s_jsonStringParsers.TryGetValue(type, out var jsonStringParser))
        { return jsonStringParser(element.GetString()!); }
        if (value is not null && TryToDeserializeValue(value, type, jsonSerializerOptions, out var deserializedValue))
        { return deserializedValue; }
        return value;
    }
}
```

**Flow:** At construction, each parameter is classified: one of eight reserved types (or `FromKernelServicesAttribute`) gets a static accessor and no metadata view; everything else becomes an argument-satisfied parameter whose runtime ladder is (1) look up by name in `KernelArguments` → coerce via `Process`, (2) otherwise INJECT the C# parameter default value, (3) otherwise throw `KernelException("Missing argument for function parameter '{name}'")`. `Process` coerces in order: assignable type → passthrough; culture-aware converter (`GetConverter`, incl. `s_jsonStringParsers` for 12 numeric types) unless the value is already a Json* node; `JsonElement` string → numeric parser; `TryToDeserializeValue` (JsonDocument/JsonNode/JsonElement deserialized directly, any other object via `value.ToString()`, catching ONLY `NotSupportedException` + `JsonException`); else passthrough unchanged. Return marshaling (824–1007): void/Task/ValueTask → empty `FunctionResult`; string variants carry `kernel.Culture`; `FunctionResult` passthrough; Task<T>/ValueTask<T> unwrapped via reflection getters; IAsyncEnumerable<T> stored as-is for later streaming (`InvokeStreamingCoreAsync` 341–379); anything else wrapped; null async results raise `KernelException("Function returned null unexpectedly.")`. Async method names have a trailing "Async" stripped (491–508).
**Invariant:** Reserved parameters are satisfied by TYPE (never by model-supplied arguments) and are invisible in the tool schema; a missing argument with a C# default gets that default INJECTED by the kernel — unlike Python, which omits missing optionals so the method's own default applies and treats metadata defaults as documentation-only; conversion failures surface as `ArgumentOutOfRangeException` naming the parameter, never as raw parse exceptions.
**Probe:** `dotnet/src/SemanticKernel.UnitTests/Functions/KernelFunctionFromMethodTests1.cs::ItSupportsParametersWithDefaultValuesAsync` (948–964), `ItShouldMarshalArgumentsOfValueTypeAsync` (967–990), `ItThrowsWhenItFailsToConvertAnArgumentAsync` (1105–1122), `ItUsesContextCultureForParsingFormattingAsync` (1072–1103), `ItCanReturnAsyncEnumerableTypeAsync` (1217–1255). Caveat: tests were read directly, not executed — the dotnet CLI in this environment fails to load its apphost.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "GetParameterMarshalerDelegate TryToDeserializeValue GetReturnValueMarshalerDelegate FromKernelServicesAttribute", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: type-driven reserved-parameter injection with metadata invisibility, the arguments→default→fail satisfaction ladder, and the deserialize-as-last-resort coercion order (assignable → culture converter → JSON string parse → full deserialization → passthrough). Adapt the default-value policy to your host's semantics — .NET re-injects C# defaults through the kernel while Python defers to the method itself; pick one and keep it consistent between schema and invocation. Omit the reflection-based Task<T>/ValueTask<T> unwrapping details (host-specific) and the AOT/trimming suppression attributes; keep the "null async result is a hard error" rule.
