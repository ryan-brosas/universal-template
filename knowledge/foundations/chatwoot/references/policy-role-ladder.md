<!-- capsule-v2 -->
# Policy role ladder — which account actions need administrator versus agent membership, and where are policies mounted?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How is the two-role (agent/administrator) ladder enforced consistently across ~30 resource policies?

## Deny-by-default ApplicationPolicy + role checks in subclasses
**Path/Symbol:** `app/policies/application_policy.rb` (whole file); exemplar `app/policies/account_policy.rb` (lines 2-45); mounting via `Api::BaseController#check_authorization` (`app/controllers/api/base_controller.rb:15-18`).
**Signature:** `ApplicationPolicy.new(user_context, record)` where user_context = `{ user:, account:, account_user:, user_context? }`; `check_authorization(model = controller_name.classify.constantize)` calls pundit `authorize(model)`.
**Data Shape:** roles carried by AccountUser enum `role: { agent: 0, administrator: 1 }`; custom_role_id exists for enterprise granular roles.

### Decisive source
```ruby
class AccountPolicy < ApplicationPolicy
  def show?
    @account_user.administrator? || @account_user.agent?
  end

  def update?
    @account_user.administrator?
  end

  # deny-by-default base:
  class Scope
    def resolve
      scope
    end
  end
end

# base_controller mount point:
def check_authorization(model = nil)
  model ||= controller_name.classify.constantize
  authorize(model)
end

def check_admin_authorization?
  raise Pundit::NotAuthorizedError unless Current.account_user.administrator?
end
```

**Flow:** API request resolves Current.user/account/account_account_user (see api-token-tenant-resolution capsule) → controller action calls check_authorization → Pundit instantiates `<Resource>Policy(user_context, record)` → each action's predicate answers with the role ladder: read-type actions (`show?, cache_keys?, limits?`) open to ANY member; configuration/mutation/billing actions (`update?, subscription?, toggle_deletion?`) administrator-only; base class defaults every predicate to false so an unwritten rule DENIES. Resource ownership policies additionally scope queries through policy Scope classes.
**Invariant:** The ladder has exactly TWO rungs per account on self-host (agent < administrator), and every policy derives from membership rows — there is no global superuser path through the API. Policies never query User.is_admin; they always test the CURRENT account's account_user, keeping multi-tenancy airtight.
**Probe:** `grep -n 'administrator? || @account_user.agent?' app/policies/account_policy.rb` → lines 3/7/11 (three read actions); direct tests under `spec/policies/` pin per-resource ladders.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "AccountPolicy administrator agent authorize", limit: 5 });
```
Resolves `app/policies/*_policy.rb` cluster line-exact.

## Verdict
Adopt deny-by-default policy classes parameterized by (user, tenant-membership) and the two-rung ladder with explicit per-action elevation. Adapt Pundit idioms to your authorization library; keep the membership-row-only rule. Omit enterprise custom_role composition unless porting the commercial tree.
