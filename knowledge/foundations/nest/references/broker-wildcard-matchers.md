<!-- capsule-v2 -->
# Broker wildcard matcher family — how do AMQP/MQTT wildcards map onto normalized flat handler routes at dispatch time, and where does each broker need extra wiring?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** When the registry is a flat map of canonical routes but the broker delivers topics with its own wildcard grammar (`*`/`#` for RMQ, `+`/`#` for MQTT), how do you match without corrupting exact-match semantics?

## Same segment-walk skeleton, two grammars
**Path/Symbol:** `packages/microservices/server/server-rmq.ts:ServerRMQ.matchRmqPattern` (457-489), `getHandlerByPattern` (402-423), `initializeWildcardHandlersIfExist` (437-455), exchange wiring in `setupChannel` (236-273); `packages/microservices/server/server-mqtt.ts:ServerMqtt.matchMqttPattern` (206-236), `getHandlerByPattern` (238-251), `removeHandlerKeySharedPrefix` (253-257); constants `packages/microservices/constants.ts` (14-16, 24-26): MQTT `'/'`,`'+'`,`'#'`; RMQ `'.'`,`'*'`,`'#'`.
**Signature:** `matchRmqPattern(pattern: string, routingKey: string): boolean`; `matchMqttPattern(pattern: string, topic: string)`; `removeHandlerKeySharedPrefix(handlerKey: string): string`.
**Data Shape:** RMQ keeps a SEPARATE `wildcardHandlers = Map<string, MessageHandler>` (string patterns containing `*` or `#`, populated lazily once); MQTT scans the main map directly.

### Decisive source
```ts
// RMQ — whole-segment wildcard comparison:
private matchRmqPattern(pattern: string, routingKey: string): boolean {
  if (!routingKey) return pattern === RMQ_WILDCARD_ALL;            // empty key matches ONLY '#'
  const patternSegments = pattern.split(RMQ_SEPARATOR);
  const routingKeySegments = routingKey.split(RMQ_SEPARATOR);
  const lastIndex = patternSegments.length - 1;
  for (const [i, currentPattern] of patternSegments.entries()) {
    const currentRoutingKey = routingKeySegments[i];
    if (!currentRoutingKey && !currentPattern) continue;
    if (!currentRoutingKey && currentPattern !== RMQ_WILDCARD_ALL) return false;
    if (currentPattern === RMQ_WILDCARD_ALL) return i === lastIndex;   // '#' must TERMINATE
    if (currentPattern !== RMQ_WILDCARD_SINGLE && currentPattern !== currentRoutingKey) return false;
  }
  return patternSegmentsLength === routingKeySegmentsLength;
}

// MQTT — first-CHARACTER wildcard test + shared-subscription prefix strip:
if (patternChar === MQTT_WILDCARD_ALL) return i === lastIndex;          // segment[0] === '#'
if (patternChar !== MQTT_WILDCARD_SINGLE && currentPattern !== currentTopic) return false;  // '+' prefix
public removeHandlerKeySharedPrefix(handlerKey: string) {
  return handlerKey && handlerKey.startsWith('$share')
    ? handlerKey.split('/').slice(2).join('/')      // '$share/<group>/rest' → 'rest'
    : handlerKey;
}
```

**Flow (both):** lookup normalizes the incoming route first (exact canonical hit wins — wildcards are a FALLBACK, never a shadow); then linear scan. RMQ scans only the lazily-built `wildcardHandlers` side map; MQTT scans every registered key after stripping `$share/<group>/`. RMQ additionally wires wildcards at BROKER level when `options.wildcards`: asserts a topic exchange (named by `exchange` or the queue name), binds the queue to EVERY registered handler key as a routing key (plus `routingKey` binding, `''` for fanout), THEN initializes the wildcard map — broker filtering and app matching stay in lockstep.
**Invariant:** `#` matches only as the FINAL pattern segment in both grammars (`root/#/grandchild` never matches — spec-pinned); exhausted incoming keys match only `#` at that position; final lengths must be equal unless `#`-terminated; an empty routing key matches ONLY bare `#`. Grammar difference to respect: MQTT tests just `segment[0]`, so ANY segment starting with `#`/`+` acts as a wildcard; RMQ requires the WHOLE segment to equal `*`/`#`.
**Probe:** `packages/microservices/test/server/server-rmq.spec.ts` matchRmqPattern blocks (exact incl. `$`-prefixed keys, `user.*` vs depth mismatch, terminal-only `#`, `'#'` vs `''`, `$exchange.*.routing.#`) + nack pins (no handler + `!noAck` → `channel.nack(msg,false,false)` AND `{id,status:'error',err:NO_MESSAGE_HANDLER}` reply) ; `packages/microservices/test/server/server-mqtt.spec.ts` matchMqttPattern true/false tables + per-handler `extras.qos` merge pin (`{qos:2, nl:true, rap:false}` preserves global options).
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", name_pattern: "matchRmqPattern|matchMqttPattern|removeHandlerKeySharedPrefix", fields: ["lines"], limit: 10 });
// live @ pin: matchMqttPattern 206-236, removeHandlerKeySharedPrefix 253-257, matchRmqPattern 457-489
```

## Verdict
Adopt "exact-normalized match FIRST, wildcard scan second" verbatim so literal handlers always outrank patterns; adopt the terminal-only-`#` segment walk as the shared skeleton and specialize only the wildcard-test rule per grammar (whole-segment vs first-char). Adapt the RMQ dual-wiring lesson (bind broker routing keys from registry keys AND keep an app-side matcher) to any broker whose server-side filter cannot express your full pattern language; port `$share/<group>/` stripping if you adopt MQTT5 shared subscriptions. Omit RMQ's separate side-map only if your registry is small enough that scanning all keys is fine — but then preserve the lazy-init-once guard.
