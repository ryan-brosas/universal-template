<!-- capsule-v2 -->
# bundler-collect-rewrite — How do you bundle an entry file's import graph without a real bundler?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What is the module-collection + specifier-rewrite pipeline that turns `import`-bearing scripts into one self-contained source?

## collect-and-rewrite seam
**Path/Symbol:** `lib/quickbeam/js/bundler.ex:bundle_file/2` (:10-25), `do_collect/4` (:36-51), `rewrite_and_resolve/3` (:64-83), `resolve_and_track/3` (:85-102); gate in `lib/quickbeam/script.ex:has_imports?/2` (:27-32).
**Signature:** `OXC.rewrite_specifiers(source, filename, (specifier -> :keep | {:rewrite, path} | throw))`; resolution via PackageResolver with extension ladder `[".ts",".tsx",".js",".jsx",".mjs",".cjs",".json"]`.
**Data Shape:** Output = ordered list of `{relative_label, rewritten_source}` fed to `OXC.bundle(files, entry:)`; labels are project-root-relative with "/" separators.
**Trigger:** Script.read bundles ONLY when OXC finds at least one import specifier; bare `.ts` gets transform only — the cond order is imports-first.

### Decisive source
```elixir
defp rewrite_and_resolve(source, importer, project_root) do
  Process.put(:bundler_resolved, [])                       # per-file tracking channel
  result = OXC.rewrite_specifiers(source, Path.basename(importer), fn specifier ->
    resolve_and_track(specifier, from_dir, project_root)
  end)
  resolved_paths = Process.delete(:bundler_resolved) || []
  case result do
    {:ok, rewritten} -> {:ok, rewritten, Enum.reverse(resolved_paths)}
    {:error, errors} -> {:error, {:parse_error, importer, errors}}
  end
catch
  {:error, _} = error -> Process.delete(:bundler_resolved); error   # abort whole DFS
end

# inside resolve callback:
{:builtin, _} -> :keep                                   # node builtins stay external
{:ok, resolved_path} ->
  Process.put(:bundler_resolved, [resolved_path | ...]) # record for traversal
  if PackageResolver.relative?(specifier), do: :keep,
  else: {:rewrite, relative_import_path(...)}            # package → relative path
:error -> throw({:error, {:module_not_found, specifier, "could not resolve"}})
```

**Flow:** read entry → detect imports (AST-level, not regex) → DFS: for each file rewrite specifiers while RECORDING resolved paths in the process dictionary → recurse into recorded deps with a seen-map cutting cycles → reverse-collected list → OXC.bundle.
**Invariant:** (1) The process-dictionary channel exists because the rewrite callback is single-return — it can't both rewrite and return a path; porters must replicate BOTH effects or lose dependency edges. (2) Unresolvable specifiers abort via throw through the catch — a missing module fails the WHOLE bundle, never silently. (3) Relative specifiers keep their form (`:keep`) because their targets are already being collected by label; only bare/package specifiers get rewritten to root-relative paths. (4) project_root = longest common prefix of entry and node_modules dir (shared_segments) — labels are stable regardless of absolute install location. (5) seen-map makes diamond imports dedupe naturally.
**Probe:** `grep -c 'bundler_resolved' lib/quickbeam/js/bundler.ex` → 4.
**Probe:** `grep -c 'import_specifiers' lib/quickbeam/script.ex` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "collect modules rewrite specifiers resolve track", limit: 10 });
```

## Verdict
Adopt AST-gated bundling with callback-side-channel dependency recording and fail-fast aborts; adapt to your transpiler's rewrite API; omit npm-style conditions beyond default unless needed. Coverage: bundler.ex/script.ex no_recorded_issue+metadata_match; direct test test/js/package_resolver_test.exs pins resolution at the pin.
