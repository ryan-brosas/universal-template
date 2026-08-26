<!-- capsule-v2 -->
# API token tenant resolution — how does one access token resolve user vs bot identity across accounts?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does a stateless API request become (user, account, account_user) without session cookies, and what happens for suspended accounts?

## Token header → Current.* threadflow
**Path/Symbol:** `app/controllers/concerns/access_token_auth_helper.rb:AccessTokenAuthHelper#authenticate_access_token!` (lines 14-21); `app/controllers/concerns/ensure_current_account_helper.rb#ensure_current_account` (9-21); token creation `app/models/concerns/access_tokenable.rb` (whole file); selection gate `app/controllers/api/base_controller.rb` (lines 3-12).
**Signature:** `authenticate_by_access_token? = request.headers[:api_access_token].present? || request.headers[:HTTP_API_ACCESS_TOKEN].present?`; owner polymorphic (`owner: self`, `dependent: :destroy_async`).
**Data Shape:** AccessToken row with unique `token` string; owner is User or AgentBot; request context lands in `Current.user / Current.account / Current.account_user`.

### Decisive source
```ruby
# base_controller.rb — auth MODE selection by header presence:
before_action :authenticate_access_token!, if: :authenticate_by_access_token?
before_action :validate_bot_access_token!, if: :authenticate_by_access_token?
before_action :authenticate_user!, unless: :authenticate_by_access_token?

# access_token_auth_helper.rb
def authenticate_access_token!
  ensure_access_token
  render_unauthorized('Invalid Access Token') && return if @access_token.blank?

  # NOTE: This ensures that current_user is set and available...
  @resource = @access_token.owner
  Current.user = @resource if allowed_current_user_type?(@resource)
end

# ensure_current_account_helper.rb
def ensure_current_account
  account = Account.find(params[:account_id])
  render_unauthorized('Account is suspended') and return unless account.active?

  if current_user
    account_accessible_for_user?(account)
  elsif @resource.is_a?(AgentBot)
    account_accessible_for_bot?(account)
  else
    render_unauthorized(I18n.t('errors.account.not_authorized'))
  end
  account
end

def account_accessible_for_user?(account)
  @current_account_user = account.account_users.find_by(user_id: current_user.id)
  Current.account_user = @current_account_user
  render_unauthorized(...) unless @current_account_user
end
```

**Flow:** request carries `api_access_token` header → token auth path INSTEAD of Devise session → lookup by exact token → owner must be User or AgentBot to become Current.user → tenant resolution happens LATER and EXPLICITLY from `params[:account_id]`: suspended accounts are rejected first, then the user's membership row (`account_users`) is required and stored as Current.account_user (the role carrier policies consume), or for AgentBots either ownership of the account or an agent_bot_inboxes row in it authorizes. Tokens attach at creation via `after_create :create_access_token` on any AccessTokenable owner.
**Invariant:** The URL's account_id IS the tenant selector — there is no token-to-account binding, so authorization strength comes entirely from the per-account membership check (or bot inbox check) that follows; skipping it would let any valid token read any tenant. Suspended-account rejection precedes membership checks.
**Probe:** `grep -n 'api/v1/accounts/conversations' app/controllers/concerns/access_token_auth_helper.rb` → lines 3-6 (the allowlist map, see bot-endpoint-allowlist capsule); direct tests: `spec/controllers/api/v1/accounts/webhooks/webhook_controller_spec.rb` exercises token-auth'd controllers; shared examples `spec/models/concerns/access_tokenable_shared.rb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "AccessTokenAuthHelper authenticate_access_token Current user", limit: 5 });
```
Rank-1: `validate_bot_access_token! ...access_token_auth_helper.rb 30-35`; `authenticate_access_token!` 14-21.

## Verdict
Adopt explicit path-param tenancy + mandatory per-request membership resolution over ambient state; adopt the suspended-check-first ordering. Adapt Current.* to your request context object. Omit Devise/session duality if your product is API-only.
