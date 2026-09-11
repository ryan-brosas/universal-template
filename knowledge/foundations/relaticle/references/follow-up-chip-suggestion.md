<!-- capsule-v2 -->
# Deterministic follow-up chips — tool-call-driven suggestions that never follow a write turn

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How do you suggest "what to ask next" after an agent turn without spending a second LLM call — and how do you keep suggestions from appearing right after a proposed mutation?

## Suggestion engine over raw tool results
**Path/Symbol:** `packages/Chat/src/Services/FollowUpService.php` (`MAX_CHIPS` :9, `suggest` :15-54, `normalizeToolName` :56-71, per-tool tables `forCompanyList` :77 / `forPeopleList` :101 / `forOpportunityList` :124 / `forTaskList` :135 / `forCompanyShow` :147 / `forPersonShow` :162 / `forOpportunityShow` :174 / `forTaskShow` :186 / `forCrmSummary` :197, result extraction `firstResultName` :211 / `firstNestedCompanyName` :226 / `resultName` :251 / `extractItems` :267 / `decodeIfJson` :286 / `pickName` :297); `packages/Chat/src/Jobs/ProcessChatMessage.php` (`broadcastFollowUps` :671-695, `broadcastSafely` :697-704); `packages/Chat/src/Events/FollowUpsSuggested.php` (whole, 45L).
**Signature:** `suggest(array $toolCalls): array<int, array{label: string, prompt: string}>` where each call is `{name: string, result?: mixed}`; output capped at 3 chips.
**Data Shape:** tool names arrive as PascalCase class basenames ("ListCompaniesTool") or snake_case; results are JSON strings or arrays, optionally wrapped in `data`, list-shaped or single-record-shaped; display name = first non-empty of `name` then `title`, nested under `company` for people lists.

### Decisive source
```php
// A write turn ends on a pending-action card, not on suggestions: if ANY
// tool call in the turn is a write, no chips at all.
foreach ($toolCalls as $call) {
    $normalized = $this->normalizeToolName($call['name']);
    if (str_starts_with($normalized, 'create_')
        || str_starts_with($normalized, 'update_')
        || str_starts_with($normalized, 'delete_')) {
        return [];
    }
}
$last = array_last($toolCalls);   // chips come from the LAST read tool only
```
```php
// PascalCase basenames → canonical snake_case keys, with an alias table for
// historical naming drift. Already-snake names pass through.
$withoutSuffix = preg_replace('/Tool$/', '', $name) ?? $name;
$snake = preg_replace('/(?<!^)([A-Z])/', '_$1', $withoutSuffix) ?? $withoutSuffix;
$snake = strtolower($snake);

return match ($snake) {
    'list_persons' => 'list_people',
    'list_peoples' => 'list_people',
    default => $snake,
};
```
```php
// Delivery is fire-and-forget: a dropped broadcast is telemetry, not an error.
private function broadcastSafely(object $event): void
{
    try {
        broadcast($event);
    } catch (Throwable $e) {
        ChatTelemetry::breadcrumb('broadcast.dropped', ['event' => $event::class, 'reason' => $e->getMessage()]);
    }
}
```

**Flow:** turn finishes → `broadcastFollowUps` maps the streamed response's tool results to `{name,result}` pairs → `suggest()` suppresses entirely on any write call → otherwise the last read tool selects a per-tool chip table (list tools personalize from the first result's name — "Details for Acme"; show tools offer relation drill-downs; unknown tools yield none) → up to 3 chips broadcast as `FollowUpsSuggested` on the private conversation channel → the client renders them under the assistant bubble and clicking one writes the prompt into the editor and sends it as a new user message.
**Invariant:** Suggestions are 100% deterministic — no model call, so they cost nothing and cannot hallucinate. Write turns never get chips (the approval card owns that UI slot). Undecodable or empty results degrade to fewer chips, never to an error. Broadcast failure is caught and breadcrumbed, never fatal to the turn.
**Probe:** `tests/Browser/Chat/FollowUpChipTest.php` — chips arriving over the `.follow_ups` broadcast render below the bubble and clicking sends the prompt as a user message; the test docblock pins WHY the chip handler must write into the TipTap editor rather than the Alpine input mirror (an empty mounted editor returns '' which short-circuits the fallback).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "FollowUpService suggest normalizeToolName FollowUpsSuggested broadcastFollowUps", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deterministic post-turn suggestion tables keyed on the last read tool when your agent has a stable read-tool vocabulary — zero-cost, testable, and safe by construction. Adopt the write-turn suppression rule whenever a turn can end in a pending human approval. Adapt the PascalCase→snake_case normalization + alias table to your tool naming scheme; keep per-tool tables small and let unknown tools return nothing. Omit Reverb channel specifics and the TipTap editor mechanics. Coverage caveat: Codebase Memory MCP was not connected this pass; evidence is direct source+test reads at the pinned HEAD.
