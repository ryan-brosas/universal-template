<!-- capsule-v2 -->
# Assistant env-option ladder — which env vars configure the AI assistant, and what makes it "present"?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are ASSISTANT_* / OPENAI_API_KEY settings read, and how does a deployment enable or echo-stub the assistant?

## appSettings two-source reads with censoring; apiKey==="test" selects EchoAssistant; no key AND no endpoint ⇒ assistant absent
**Path/Symbol:** `app/server/lib/Assistant.ts`: `getAssistantV1Options` (:14–49, envVar array :19, preferredEnvVar :20), `getAssistantV2Options` (:51–71); `app/server/lib/configureOpenAIAssistantV1.ts` (:5–14) — test gate :9.
**Signature:** `configureOpenAIAssistantV1(): AssistantV1 | undefined` (undefined = feature off).
**Data Shape:** Options: `{apiKey?, completionEndpoint?, model?, longerContextModel?, maxTokens?}` (+v2: `maxToolCalls, structuredOutput`).

### Decisive source
```ts
// getAssistantV1Options — every flag via appSettings.section("assistant")
const apiKey = appSettings.section("assistant").flag("apiKey").readString({
  envVar: ["ASSISTANT_API_KEY", "OPENAI_API_KEY"],   // fallback chain
  preferredEnvVar: "ASSISTANT_API_KEY",
  censor: true,                                      // never logged
});
...
export function configureOpenAIAssistantV1(): AssistantV1 | undefined {
  const options = getAssistantV1Options();
  if (!options.apiKey && !options.completionEndpoint) {
    return undefined;                                // feature OFF
  } else if (options.apiKey === "test") {
    return new EchoAssistantV1();                    // self-test stub: echoes input
  } else {
    return new OpenAIAssistantV1(options);
  }
}
```

**Flow:** settings resolution (env → config file) per flag → presence check on key OR endpoint (a keyless local LLM endpoint is legal) → `"test"` magic value swaps in EchoAssistant so suites run without network. V2 options spread V1's and add tool-loop limits.
**Invariant:** The constructor double-checks (`!this._apiKey && !_options.completionEndpoint` throws) but the FACTORY decides absence — callers treat undefined as "don't mount routes". `censor:true` keeps the key out of AppSettings dumps (ties into the api-result-pruning discipline). Default model/longer-context defaults apply ONLY when no custom endpoint was set (:76–80) — custom-endpoint deployments must name their own model.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "ASSISTANT_API_KEY\|preferredEnvVar" app/server/lib/Assistant.ts | head -3 && grep -n "options.apiKey === \"test\"" app/server/lib/configureOpenAIAssistantV1.ts'` → :19/:20 and :9.
Direct tests: `test/server/lib/OpenAIAssistantV1.ts` before-hook drives this exact factory with env vars (:36–47).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getAssistantV1Options appSettings apiKey EchoAssistant","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the undefined-means-off factory contract + magic-test-value pattern + censored reads; adapt setting names; omit the v2 flags if your host ships only formula assistance.
