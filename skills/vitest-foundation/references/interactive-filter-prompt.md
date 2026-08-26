<!-- capsule-v2 -->
# Interactive filter prompt — how do you build a single-keypress terminal prompt that redraws one screen region and restores raw-mode state safely?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** What is the minimal correct readline/keypress/ANSI protocol for an interactive "type to filter, arrows to select" CLI prompt (used for `vitest related/p` filename filtering)?

## WatchFilter keypress state machine
**Path/Symbol:** `packages/vitest/src/node/watch-filter.ts:WatchFilter` — constructor raw-mode (:30–47), `filter()` (:49–64), `filterHandler` switch (:66–132), ANSI redraw `eraseAndPrint` (:205–219), cursor restore (:232–236).
**Signature:** `public async filter(filterFunc: (keyword: string) => Promise<T[] | T[]>): Promise<string | undefined>`; internal handler `(str: string, key: {name, sequence, ctrl, meta}) => void`.
**Data Shape:** state = `currentKeyword?: string`, `results: FilterItem[]` (string or `{key}` object), `selectionIndex: number` (-1 = none). Constants: `MAX_RESULT_COUNT = 10`, `SELECTION_MAX_INDEX = 7`. Resolves the typed keyword, selected item's `.key`, or `undefined` on Ctrl-C/Escape.

### Decisive source
```ts
// lifecycle: raw mode ON in constructor, OFF in finally
this.filterRL = readline.createInterface({ input: this.stdin, escapeCodeTimeout: 50 })
readline.emitKeypressEvents(this.stdin, this.filterRL)
if (this.stdin.isTTY) this.stdin.setRawMode(true)
...
try { return await resultPromise } finally { this.close() }   // close(): rl.close + removeListener + setRawMode(false)

// backspace keeps >=1 char semantics: length>1 slices, else clears to undefined
case key.sequence === '\x7F':
  if (this.currentKeyword && this.currentKeyword?.length > 1) this.currentKeyword = this.currentKeyword?.slice(0, -1)
  else this.currentKeyword = undefined

// every keypress ends with re-query + full redraw
if (this.currentKeyword) this.results = await filterFunc(this.currentKeyword)
this.render()

// windowed rendering when results exceed MAX_RESULT_COUNT
const offset = this.selectionIndex > SELECTION_MAX_INDEX ? this.selectionIndex - SELECTION_MAX_INDEX : 0
const displayResults = this.results.slice(offset, MAX_RESULT_COUNT + offset)
...
// eraseAndPrint counts WRAPPED rows so multi-line output erases correctly:
rows += 1 + Math.floor(Math.max(stripVTControlCharacters(line).length - 1, 0) / columns)
this.write(`${ESC}1G`)      // col 1
this.write(`${ESC}J`)       // erase down
this.write(str)
this.write(`${ESC}${rows - 1}A`)  // up N lines
```

**Flow:** `filter()` prints `? <message> › <keyword>` → attaches keypress handler → loop: Backspace/Ctrl-C/Escape/Enter/Up/Down/printable → update keyword or selection or resolve promise → await `filterFunc(keyword)` → redraw windowed list with `›` cursor (green selected / dim rest + "...and N more") → restore cursor column to end of keyword. Enter resolves selection-or-keyword (`selection.key || currentKeyword || ''`).
**Invariant:** raw mode is restored in a `finally`, and the keypress listener is removed by name — leaking either corrupts every later prompt in the process. The redraw must strip VT codes before measuring line width (wrapped-row math) or long patterns leave ghost text. Selection index wraps at BOTH ends (-1 sentinel = no selection; down clamps at last result). Non-TTY stdin skips `setRawMode` entirely (CI safety).
**Probe:** `test/e2e/test/watch/stdin.test.ts` drives the same keystroke protocol through `runInlineTests` + `vitest.write(...)` (`p` → "Input filename pattern" → typed pattern → "Pattern matches N results"); the rename scenario in `file-watching.test.ts` (:210–223) exercises filter-after-delete ("Pattern matches no results").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "WatchFilter filterHandler", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the keypress state machine, finally-guaranteed raw-mode restore, and wrapped-row erase math for any interactive CLI picker. Adapt prompt styling/colors and the async filter source. Omit the object-result `{key}` form if you only need strings.
