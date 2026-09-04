<!-- capsule-v2 -->
# Parser factory & view-field override — how is the right ValueParser chosen, and when does a view field's options beat the column's?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How do type→class dispatch and field-vs-column option precedence work for parsers/formatters?

## valueParserClasses map keyed by EXTRACTED type; createParserOrFormatterArguments prefers field widgetOptions only when non-empty
**Path/Symbol:** `app/common/ValueParser.ts`: `valueParserClasses` (:213–222), `createParserRaw` (:230–235, `extractTypeFromColType`), `createParser` (:244–250), argument builders (:258–294) — override line :270, reference-option injection :285–291.
**Signature:** `createParserRaw(type, widgetOpts, docSettings): ValueParser`; `createParser(docData, colRef, fieldRef?)`.
**Data Shape:** Ref types get EXTRA synthetic options: `visibleColId/visibleColType/visibleColWidgetOpts/tableData` merged into widgetOpts.

### Decisive source
```ts
export const valueParserClasses = {
  Numeric: NumericParser, Int: NumericParser,
  Date: DateParser, DateTime: DateTimeParser,
  ChoiceList: ChoiceListParser,
  Ref: ReferenceParser, RefList: ReferenceListParser,
  Attachments: ReferenceListParser,
};
// createParserRaw: cls = valueParserClasses[extractTypeFromColType(type)] || IdentityParser
...
let fieldOrCol = col;
if (fieldRef) {
  const field = fieldsTable.getRecord(fieldRef);
  fieldOrCol = field?.widgetOptions ? field : col;      // ONLY a non-empty field string wins
}
...
if (isFullReferencingType(type)) {
  widgetOpts.visibleColId = vcol?.colId || "id";
  widgetOpts.visibleColType = vcol?.type;
  widgetOpts.visibleColWidgetOpts = safeJsonParse(vcol?.widgetOptions || "", {});
  widgetOpts.tableData = docData.getTable(getReferencedTableId(type)!);
}
```

**Flow:** `extractTypeFromColType("Ref:Table1")` → `"Ref"` (suffix stripped) → class lookup → unknown/Text types get IdentityParser (the parse-nothing default that callers short-circuit on). View-field options override column options ONLY when the field row carries a truthy widgetOptions JSON — otherwise formatting/paste would disagree between views sharing a column. For reference types the VISIBLE column's identity+type+options are injected so pasted display-values resolve through the same machinery used to render them.
**Invariant:** Int shares NumericParser (both parse via NumberParse). Attachments share ReferenceListParser (attachment entries ARE references to the _grist_Attachments table — visibleColId defaults to id). The `field?.widgetOptions ?` guard is falsy-aware: empty-string options fall back to the COLUMN, preventing a blanked field from wiping real options.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && sed -n "269,271p" app/common/ValueParser.ts && grep -n "Attachments: ReferenceListParser" app/common/ValueParser.ts'` → override ternary and the attachment alias.
Direct tests: factory behavior exercised via paste suites; anchor `grep -rn "createParserRaw" app/ --include=*.ts` shows NumericGuesser consuming it (:121 of ValueGuesser).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"createParserRaw valueParserClasses extractTypeFromColType","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the extracted-type registry + falsy-guard override + visible-column injection; adapt the class set to your type system; omit IdentityParser at your peril — callers rely on instanceof to skip work.
