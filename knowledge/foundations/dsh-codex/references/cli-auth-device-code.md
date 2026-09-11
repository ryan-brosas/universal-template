<!-- capsule-v2 -->
# CLI auth modes — browser/device-code selection with safe notification

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should a credential CLI select browser versus device-code OAuth, reject unsafe mode combinations, and render provider events without leaking stored credentials?

## answerPrompt, notify, and bin.run auth-mode boundary
**Path/Symbol:** src/bin.ts:54-73 notify; src/bin.ts:76-92 answerPrompt; src/bin.ts:147-169 and 243-259 run; src/bin.ts:24-44 openBrowser (launcher decisive excerpt added by the pass-11 refactor — the invariant was previously claimed but this range was uncited).
**Signature:** answerPrompt(prompt: AuthPrompt, deviceCode: boolean, question): Promise<string>; notify(event: AuthEvent, useBrowser: boolean): void; run(argv: readonly string[]): Promise<number>; openBrowser(rawUrl: string): void.
**Data Shape:** --device-code changes the selected provider prompt id from browser to device_code; auth_url and device_code events render URLs/codes, while free-form prompts forward AbortSignal. --json is forbidden for login and device-code because interactive auth is not the secret-free JSON status surface.

### Decisive source
~~~ts
/** Open one trusted HTTPS URL with the platform browser, best effort. */
function openBrowser(rawUrl: string): void {
  const url = new URL(rawUrl)
  if (url.protocol !== 'https:') throw new Error(`refusing to open non-HTTPS authorization URL from ${url.host}`)
  const command = process.platform === 'win32'
    ? { file: 'rundll32.exe', args: ['url.dll,FileProtocolHandler', url.href] }
    : process.platform === 'darwin'
      ? { file: 'open', args: [url.href] }
      : { file: 'xdg-open', args: [url.href] }
  try {
    const child = spawn(command.file, command.args, {
      detached: true,
      stdio: 'ignore',
      windowsHide: true,
    })
    child.on('error', () => {})
    child.unref()
  } catch {
    // The printed URL remains the manual fallback.
  }
}

if (prompt.type === 'select') {
  const wanted = deviceCode ? 'device_code' : 'browser'
  if (!prompt.options.some(option => option.id === wanted)) {
    throw new Error('OpenAI Codex login did not offer the requested method')
  }
  return wanted
}

const deviceCode = optionFlags.includes('--device-code')
if (unknown.length > 0 || (deviceCode && action !== 'login')
  || (jsonOutput && (action === 'login' || action === 'logout' || deviceCode))) {
  return 1
}

case 'login': {
  try {
    await loginOpenAICodex({
      prompt: prompt => answerPrompt(prompt, deviceCode, question),
      notify: event => notify(event, true),
    })
  } finally { readline.close() }
}
~~~

**Flow:** parse CLI mode flags, reject device-code outside login and JSON combined with interactive auth, answer the provider select prompt with the requested method or fail if unavailable, forward cancellation, print browser/device-code events and best-effort open only HTTPS URLs, close readline on every path, and prefix a bounded redacted error.
**Invariant:** the CLI never silently falls back from a requested auth method; interactive auth is not emitted as JSON; provider cancellation reaches terminal questioning; browser opening rejects non-HTTPS URLs; readline cleanup is unconditional and stored tokens are not printed.
**Probe:** tests/bin.spec.ts:64-86 (CLI help and stable error prefix), plus tests/bin.spec.ts:227-242 (unsupported device-code/JSON combinations reject with the consistent prefix). Direct source ranges 54-92 and 147-259 were read; successful provider device-code rendering is not directly tested.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.bin\\.(answerPrompt|notify|run|openBrowser)$', limit: 10, fields: ['signature', 'name', 'file'] });
~~~
Executed live against project `dsh-codex` during the pass-11 refactor: total 4, has_more false. The TUI-side twin (`src/tui.ts:115-135`, headless detection + boolean outcome) is owned by `tui-headless-browser-launch.md`; this capsule owns the CLI launcher only.

## Verdict
Adopt explicit auth-mode selection, provider-offered-method validation, signal forwarding, and unconditional interactive cleanup. Adapt event names, browser launcher, and CLI option vocabulary; omit exposing device-code prompts through browser Web OAuth routes, which consume only an HTTPS authorization challenge. Coverage: src/bin.ts and tests/bin.spec.ts are no_recorded_issue with metadata_match; successful device-code rendering remains a stated caveat.
