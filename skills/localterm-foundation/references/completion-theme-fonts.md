<!-- capsule-v2 -->
# Completion, theme & fonts — how does typed command-line completion, iTerm2 theme import, and a shared font catalog work?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you resolve completions from a typed command line against a declarative spec, and import/serve theme + font catalogs from one source of truth?

## Completion engine — spec → walker → resolver
**Path/Symbol:** `packages/server/src/completion/spec.ts` (CommandSpec/OptionSpec/PositionalSpec); `walker.ts:resolveCompletionContext` (37–88); `resolver.ts:resolveCandidates/formatCandidates` (34–53 / 57–64); `index.ts` (public surface).
**Signature:** `resolveCompletionContext(spec: CommandSpec, words: readonly string[]): CompletionContext { command, positionalIndex, currentWord, completingOptionValue }`; `resolveCandidates(ctx, source: ValueSource): Promise<string[]>`; `formatCandidates(candidates, prefix): string`.
**Data Shape:** `words[0]` = program name, last element = partial current word (possibly ""); positional values are either static lists or dynamic `ValueSource` names (`sessions/secrets/processes/themes/customThemes`) the CLI backs with loopback HTTP and the daemon backs with in-memory stores — same names, no self-HTTP.

### Decisive source
```ts
// walker — one pass over previously typed tokens:
if (expectingOptionValue) { expectingOptionValue = null; continue; }   // value consumed
if (token.startsWith("--")) { const [flag, inline] = splitFlag(token);
  const option = findOption(current, flag);
  if (option && option.takesValue && inline === undefined) expectingOptionValue = option; }
const subcommand = findSubcommand(current, token);   // descend resets positionalIndex
...
if (currentWord.startsWith("-")) return { ..., completingOptionValue: null }; // flag mode wins
// resolver priority: option-value choices > flags > subcommands@positional-0
// > static positional values > dynamic ValueSource lookup
```

**Flow:** walk tokens tracking deepest command + consumed positionals + pending value-taking options (`--opt=` inline values consume themselves; `--no-pin` negated booleans don't expect values) → resolve candidates by context kind → prefix-filter, dedupe, sort, render one-per-line.
**Invariant:** a current word starting with `-` is ALWAYS flag completion regardless of a pending option-value expectation.
**Probe:** `packages/cli/tests/utils/completion.test.ts` :45 descend resets positional index, :76 marks option-value after a value-taking option, :87 no value expected after `--no-pin`, :93 inline value resumes positionals, :106 flag-completion beats pending option value.

## Theme import — iTerm2 plist + JSON with hex normalization
**Path/Symbol:** `packages/server/src/theme-parser.ts:colorKeysToTheme/normalizeColor/buildFromColors` (5–28 / 35–42 / 56–72); in-repo recursive-descent mini-plist parser (:96+, no XML dependency).
**Signature:** `normalizeColor(value): string | undefined`; `ImportedThemeResult = { theme } | { error }`.
**Data Shape:** maps `Background/Foreground/Cursor/Cursor Text/Selection/Selected Text Color` + `Ansi 0..15 Color` onto xterm's ThemeColors; accepts `{name?, colors:{...}}` OR a bare xterm ITheme object.

### Decisive source
```ts
const normalizeColor = (value: unknown): string | undefined => {
  if (!isHexColor(value)) return undefined;          // /^#[0-9a-fA-F]{3,8}$/
  if (hex.length === 3) return `#${hex[0]}${hex[0]}${hex[1]}${hex[1]}${hex[2]}${hex[2]}`.toLowerCase();
  return `#${hex.slice(0, 6)}`.toLowerCase();        // alpha dropped: xterm colors are opaque
};
// invalid fields are OMITTED so xterm falls back to per-field defaults rather
// than rendering an invalid color string. (:53-55)
```

**Probe:** `packages/server/tests/theme-parser.test.ts` :27 bare colors object accepted, :42 #rgb expanded + alpha dropped, :51 invalid hex field omitted, :72 real .itermcolors plist parsed.

## Font catalog — daemon/browser single source
**Path/Symbol:** `packages/server/src/terminal-fonts.ts:TERMINAL_FONTS/BUILTIN_FONT_IDS/findTerminalFontById` (34–74).
**Signature:** `TerminalFont { id, name, source: "fontsource" | "custom" }`; `findTerminalFontById(id): TerminalFont` falls back to the default (Geist Mono).
**Data Shape:** built-ins are fontsource ids; `"custom"` is a pseudo-id — the BROWSER builds its family string on demand from user input while the daemon stores only id + custom family name (`~/.localterm/fonts.json`).

**Invariant:** the CSS `family` string is a browser-only concern; the shared module lives in the server package so daemon storage/completion/CLI and browser read ONE list (duplicating it desyncs validation).
**Probe:** `tests/fonts-api.test.ts` / `font-store.test.ts` cover PUT validation + persistence; catalog ids verified against `BUILTIN_FONT_IDS`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "resolveCompletionContext|resolveCandidates|formatCandidates|findTerminalFontById", limit: 8 });
```
Graph check this session: resolveCompletionContext resolved at completion/walker.ts 37–88, line-exact vs HEAD.

## Verdict
Adopt the spec/walker/resolver split with option-value tracking and flag-mode precedence, dynamic ValueSource indirection, omit-invalid-fields color normalization (#rgb expansion, alpha drop), and the shared-catalog-with-browser-only-CSS-family rule; adapt the spec vocabulary, theme key map, and font list to host; omit the CLI shell-script emitters unless porting bash/zsh/fish completion scripts. Probes cited from on-disk test files (vite-plus).
