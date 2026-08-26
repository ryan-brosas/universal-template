<!-- capsule-v2 -->
# Prompt-only console login flow — how do you run an interactive key-entry login when there is no browser/OAuth dance to automate?

**Source:** pi-bailian MIT `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory `pi-bailian`. **Question:** What does a `login` callback look like for a service where the user must fetch a key from a web console themselves?

## Region-parameterized manual login seam
**Path/Symbol:** `src/index.ts:loginBailian` (:69-108), `loginBailianCN` (:113-115).
**Signature:** `async function loginBailian(callbacks: OAuthLoginCallbacks, region: "intl" | "cn" = "intl"): Promise<OAuthCredentials>`.
**Data Shape:** `region` selects the console URL (`intl` → modelstudio.console.alibabacloud.com, `cn` → bailian.console.aliyun.com); `callbacks.onPrompt({message})` resolves to the pasted key string.

### Decisive source
```ts
  const consoleUrl =
    region === "intl"
      ? "https://modelstudio.console.alibabacloud.com/"
      : "https://bailian.console.aliyun.com/";

  // Show instructions only - do NOT auto-open browser
  const instructions = `
Bailian Coding Plan API Key Setup
=================================
...
`.trim();

  // Use onPrompt with the full instructions - this displays text without opening browser
  const apiKey = await callbacks.onPrompt({
    message: `${instructions}\n\nEnter your Bailian Coding Plan API key (starts with 'sk-sp-'): `,
  });

  // Validate the key
  const validation = validateApiKey(apiKey);
  if (!validation.valid) {
    throw new Error(validation.error || "Invalid API key");
  }
```

**Flow:** pick console URL by region → render numbered setup instructions + key-format hint through one `onPrompt` call → validate → throw on failure (login aborts; nothing persisted) → return credentials on success.
**Invariant:** fail-closed — an invalid key THROWS before any credential object is constructed or stored; instructions are display-only (the extension never opens a browser itself). The CN variant is pure delegation: `return loginBailian(callbacks, "cn")`.
**Probe:** `test/exports.test.ts` pins the default-export surface the host calls into; behavior anchors are direct source lines :73-99 (runner BLOCKED this pass: no node_modules — deterministic line-pinned evidence per Gate-5 fallback).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", query: "interactive login prompt instructions console region", limit: 5, fields: ["signature", "lines"] });
```
Executed live at pin: returned `loginBailian` (69-108) and `loginBailianCN` (113-115) — total 2, has_more false. Both seams retrieved exactly.

## Verdict
Adopt the single-prompt instruction-plus-entry pattern and the throw-on-invalid boundary for any console-key service. Adapt the instruction copy, URLs, and prompt count to your provider. Omit browser automation entirely — its absence is the point of this seam.
