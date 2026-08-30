<!-- capsule-v2 -->
# Kanban board over EAV columns — left-joined column value, atomic moveCard, date-string badges

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you run a kanban board whose columns are custom-field option values (polymorphic EAV rows) instead of table columns, and keep position + column moves atomic?

## Board query with the column value joined in
**Path/Symbol:** `app/Filament/Resources/OpportunityResource/Pages/OpportunitiesBoard.php` (`board(Board $board)` :52-199, `moveCard(...)` :214-246, `formatCloseDateBadge` :273-290, `stageCustomField` :292-299, `stages()` :301-317, `canAccess` :319-323); twin `app/Filament/Resources/TaskResource/Pages/TasksBoard.php` (`formatDueDateBadge` :256-269); position source `spatie/eloquent-sortable` `order_column` + Flowforge `positionIdentifier`.
**Signature:** `moveCard(string $cardId, string $targetColumnId, ?string $afterCardId = null, ?string $beforeCardId = null): void` — overrides the Flowforge default because the column identifier is not a real column.
**Data Shape:** board query = `Opportunity::query()->leftJoin('custom_field_values as cfv', fn (JoinClause $join) => $join->on('opportunities.id','=','cfv.entity_id')->where('cfv.custom_field_id','=',$stageField->getKey()))->select('opportunities.*', "cfv.{$valueColumn}")`; board wiring `->columnIdentifier($valueColumn)->positionIdentifier('order_column')`. Columns derive from `$field->options->map(...)` with per-option color from `$option->settings->color` only when `$field->settings->enable_option_colors`.

### Decisive source
```php
DB::transaction(function () use ($card, $board, $targetColumnId, $newPosition): void {
    $columnIdentifier = $board->getColumnIdentifierAttribute();
    $columnValue = $this->resolveStatusValue($card, $columnIdentifier, $targetColumnId);
    $positionIdentifier = $board->getPositionIdentifierAttribute();

    $card->update([$positionIdentifier => $newPosition]);

    /** @var Opportunity $card */
    $card->saveCustomFieldValue(self::stageCustomField(), $columnValue);
});
```
`$newPosition = $this->calculatePositionBetweenCards($afterCardId, $beforeCardId, $targetColumnId)` (decimal midpoint between neighbors). Create-in-column mirrors it: create through the team relation, then `saveCustomFieldValue(stageField, $columnId)` + `$opportunity->order_column = (float) $this->getBoardPositionInColumn($columnId)` + `saveQuietly()` (quiet so observers don't fire on the position stamp). `canAccess()` returns false unless the stage/status custom field exists — the whole page is gated on the EAV column being bootstrapped.

**Two calendar-badge disciplines (both test-pinned, opposite directions):** the TASKS board stores a datetime and converts it into the viewer's zone before comparing (`$date = Date::parse($state)->setTimezone(FilamentTimezone::get())` then `isPast()/isToday()/isTomorrow()`), because a late-evening UTC due date buckets a day early for viewers far east. The OPPORTUNITIES board stores a plain calendar date at midnight UTC and must NOT convert it — a negative-offset zone walks it back past midnight and the card reads a day early — so both the date and the viewer's "today" are compared as date STRINGS:
```php
$date = Date::parse($state);
$viewerToday = Date::now(FilamentTimezone::get())->startOfDay();

$closesOn = $date->toDateString();
$today = $viewerToday->toDateString();
$tomorrow = $viewerToday->copy()->addDay()->toDateString();

return match (true) {
    $closesOn < $today => $date->format('M j').' (Overdue)',
    $closesOn === $today => 'Closes Today',
    $closesOn === $tomorrow => 'Closes Tomorrow',
    default => $date->format('M j'),
};
```

**Flow:** board render (left-joined column value on every row) → drag → moveCard → decimal position between neighbors → one transaction updates order_column AND the EAV column value → `kanban-card-moved` event dispatched only after commit.
**Invariant:** Position and column change atomically or not at all; the board query must carry the column value or the columnIdentifier cannot resolve; a datetime value converts to the viewer zone, a date value never does — compare dates as strings.
**Probe:** `tests/Feature/Filament/App/Pages/OpportunitiesBoardTest.php` — records land in the right columns; other teams' records excluded; `moveCard` updates the stored custom-field value and dispatches `kanban-card-moved`; Tokyo 23:00 UTC sees "Closes Today" for midnight-UTC 19th; Los Angeles 16:00 UTC does NOT see "Overdue" for the same date. `tests/Feature/Filament/App/Pages/TasksBoardTest.php` pins the datetime twin.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "moveCard columnIdentifier positionIdentifier saveCustomFieldValue calculatePositionBetweenCards toDateString", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the left-join-the-column-value board query and the transactional position+column move for any kanban whose grouping key lives in an EAV table. Adopt the date-string comparison for plain calendar dates and the zone-conversion for datetimes — the two failure modes are mirror images and each needs its own rule. Adapt the decimal-position service and Flowforge wiring to your board library. Omit the legacy-board 301 redirects and view switcher (product surface). Companion to `my-tasks-calendar-severity.md` (the datetime-side of the calendar rule) and `custom-field-batch-plane.md` (the EAV storage being joined).
