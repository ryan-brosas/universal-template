<!-- capsule-v2 -->
# XLS grid-loader fidelity ladder — how does a spreadsheet load as COMPUTED values while preserving blank-row geometry?

**Source:** DataGrip installed distribution `dist@262.9437.163` (proprietary; study/reference only); Codebase Memory `jetbrains-datagrip`. **Question:** What must a spreadsheet importer evaluate, pad, and fall back to so the grid shows what a USER SEES in the workbook rather than raw cell state?

## Graph-selected seam: formula-evaluated, gap-preserving sheet reader
**Path/Symbol:** `plugins/grid-loader-xls/external-extensions/com.intellij.database/data/loaders/XLS.groovy` — `loadXls`:13-20, `produceSheet`:22-36, `extractRow`:38-50, `cellVal`:52-66.
**Signature:** `def produceSheet(sheet, evaluator, dataConsumer)`; `def extractRow(row, evaluator): List<Object>`; `def cellVal(cell)` over evaluated POI `CellValue`.
**Data Shape:** input = first sheet only (`wb.getSheetAt(0)`); every cell passes `evaluator.evaluate(cell)` before typing; rows emit as `Object[]` with `new Object[0]` placeholders for blank gaps.

### Decisive source
```groovy
// XLS.groovy:14-19 — evaluator created ONCE for the whole workbook
def wb = WorkbookFactory.create(new File(path))
def evaluator = wb.getCreationHelper().createFormulaEvaluator();
def sheet = wb.getSheetAt(0)
produceSheet(sheet, evaluator, dataConsumer)
// XLS.groovy:26-33 — blank-row GEOMETRY is preserved with empty placeholder rows
if (!res.isEmpty()) {
  def cur = row.getRowNum()
  while (idx < cur - 1) { dataConsumer.consume(new Object[0]); ++idx }
  idx = cur
  dataConsumer.consume(res.toArray())
}
// XLS.groovy:45-46 + 52-66 — type ladder runs on the EVALUATED value
def v = evaluator.evaluate(cell)
def rv = cellVal(v)
...
switch (cell.getCellType()) {
  case CellType.BOOLEAN: return cell.getBooleanValue()
  case CellType.STRING:  return cell.getStringValue()
  case CellType.NUMERIC: return cell.getNumberValue()
  case CellType.BLANK:   return null
  default:               return cell.formatAsString()   // formulas land here AFTER evaluation
}
```

**Flow:** open workbook → one shared FormulaEvaluator → iterate rows; skip fully-empty extracted rows but COUNT them: gaps between last emitted row and current rowNum are filled with zero-width placeholder rows so downstream row indices match the sheet → per cell: evaluate then classify.
**Invariant:** (1) values are POST-EVALUATION (a FORMULA cell contributes its computed value via the default arm's `formatAsString()` on the evaluated CellValue — never the formula string); (2) blank rows are SIGNAL, not noise — dropping them desynchronizes grid rows from spreadsheet rows; (3) column holes inside a live row null-pad (`while res.size() < cur`), mirroring the JSON loader's sparse discipline.
**Probe:** executed live Retrieve (2026-08-25) `search_graph { query: "cellVal formula evaluator produceSheet", limit: 6 }` → exactly produceSheet 22-36 + cellVal 52-66; file read whole before citing; parse_partial flags (lines 5,39) covered by direct read.
**Coverage caveat:** parse_partial file; source wins over graph.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-datagrip", query: "cellVal formula evaluator produceSheet", limit: 6 });
```
(Live result 2026-08-25: total 2, has_more false.)

## Verdict
Adopt: single shared evaluator pass, computed-value-only ingestion, placeholder-row geometry preservation, evaluate→classify ladder with formatted-string fallback. Adapt the fallback rendering to your host's scalar model. Omit POI API specifics. Complements json-grid-loader-shape-dispatch: together they define the consumer contract (Object[] rows + consumeColumns) every loader script must honor.
