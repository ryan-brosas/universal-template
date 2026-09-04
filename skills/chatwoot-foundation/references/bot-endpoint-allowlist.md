<!-- capsule-v2 -->
# Bot endpoint allowlist — which endpoints may a bot token call, and where is that enforced?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How do you let an automation bot act through the same API as a human agent without handing it the whole surface?

## Static controller/action allowlist after token auth
**Path/Symbol:** `app/controllers/concerns/access_token_auth_helper.rb:AccessTokenAuthHelper` (lines 2-7 constant, 30-35 enforcement).
**Signature:** `validate_bot_access_token!` runs as a SECOND before_action whenever token auth was used; `agent_bot_accessible? = BOT_ACCESSIBLE_ENDPOINTS.fetch(params[:controller], []).include?(params[:action])`.
**Data Shape:** hash of controller path strings → array of action name strings; frozen constant.

### Decisive source
```ruby
BOT_ACCESSIBLE_ENDPOINTS = {
  'api/v1/accounts/conversations' => %w[show toggle_status toggle_typing_status toggle_priority create update custom_attributes],
  'api/v1/accounts/conversations/messages' => ['create'],
  'api/v1/accounts/conversations/assignments' => ['create'],
  'api/v1/accounts/conversations/labels' => %w[index create]
}.freeze

def validate_bot_access_token!
  return if Current.user.is_a?(User)
  return if @resource.is_a?(AgentBot) && agent_bot_accessible?

  render_unauthorized('Access to this endpoint is not authorized for bots')
end
```

**Flow:** every token-authenticated request passes TWO gates in order: authenticate (token exists, owner becomes identity) then validate (if identity is NOT a User, i.e. an AgentBot, the controller/action pair must appear verbatim in the map) → humans skip the second gate entirely (`return if Current.user.is_a?(User)`). Bots therefore get: read one conversation, toggle status/typing/priority, create/update conversations + custom attributes, post messages, assign, manage labels — and nothing else (no contacts, no inbox admin, no reports, no webhooks management).
**Invariant:** Enforcement is centralized at the AUTH layer, keyed on Rails routing strings (`params[:controller]` is the full namespaced path), so adding a controller action does NOT silently expose it to bots; new bot capability requires an explicit constant edit. The order matters: this check runs before tenant resolution, failing fast with a distinct message.
**Probe:** `grep -n 'BOT_ACCESSIBLE_ENDPOINTS = {' app/controllers/concerns/access_token_auth_helper.rb` → line 2; direct test coverage via `spec/controllers/api/v1/accounts/` bot-token suites exercising both allowed and rejected surfaces.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "AccessTokenAuthHelper validate_bot_access_token BOT_ACCESSIBLE_ENDPOINTS", limit: 5 });
```
Rank-1: `validate_bot_access_token! ...access_token_auth_helper.rb 30-35`.

## Verdict
Adopt identity-class-based endpoint allowlisting enforced centrally at auth (not scattered per-controller). Adapt the map format to your framework's route identity; keep it a frozen literal reviewed in PRs. Omit Chatwoot's specific action list unless porting its conversation surface.
