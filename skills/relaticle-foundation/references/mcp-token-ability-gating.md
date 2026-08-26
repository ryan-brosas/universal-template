<!-- capsule-v2 -->
# Token-ability gating — inline structured errors because the framework stopped catching

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you enforce per-tool OAuth/Sanctum abilities when the MCP framework no longer translates authorization exceptions?

## ChecksTokenAbility dual-token gate
**Path/Symbol:** `app/Mcp/Tools/Concerns/ChecksTokenAbility.php` (whole, 49L); registration-side twins: `shouldRegister()` in `app/Mcp/Prompts/CrmOverviewPrompt.php` (:25-36) and `app/Mcp/Resources/CrmSummaryResource.php` (:31-42).
**Signature:** `denyIfTokenCannot(string $ability): ?Response`
**Data Shape:** Returns `Response::error('Invalid ability provided.')` or null; token types discriminated by class: `PassportAccessToken` (OAuth) vs `PersonalAccessToken` (Sanctum-style).

### Decisive source
```php
// Sanctum's MissingAbilityException is no longer caught by laravel/mcp
// since v0.6.5 (Server.php only catches JsonRpcException and ValidationException),
// so we return the error inline instead of throwing.
if ($token instanceof PassportAccessToken && ! $token->can(Registrar::OAUTH_SCOPE)) {
    return Response::error('Invalid ability provided.');
}
if ($token instanceof PersonalAccessToken && $token->getKey() && ! $token->can($ability)) {
    return Response::error('Invalid ability provided.');
}
```
OAuth asymmetry docblock (:35-38): "OAuth clients can only ever ask for `mcp:use` — it is the single entry in the authorization-server metadata... per-ability grants are not expressible over OAuth. Holding it authorizes the toolset; which team's data those tools reach is bound separately on the token." Null-token bypass is deliberate and enumerated (tests via actingAs; route guard makes session case unreachable). Prompts/resources use `shouldRegister()` to vanish from discovery entirely for read-less tokens.

**Flow:** every tool handler starts with `if (($denied = $this->denyIfTokenCannot('read')) instanceof Response) return $denied;` → OAuth tokens check the single scope constant; personal tokens check the granular ability → null token passes (documented bypasses) → prompts/resources additionally hide themselves pre-discovery.
**Invariant:** Never THROW an ability exception on this framework version — it escapes as an unhandled protocol error. The two token classes need different checks, and the null-token branch must remain explicit, not folded into a default.
**Probe:** `tests/Feature/Mcp/TokenAbilitiesMcpTest.php`, `WhoAmiToolTest.php`, OAuth suite (`OAuthDiscoveryTest`, `OAuthTeamPickerTest`, `OAuthRefreshTokenCascadeTest`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ChecksTokenAbility denyIfTokenCannot shouldRegister OAUTH_SCOPE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt inline-error ability gating with class-differentiated token checks whenever a middleware-style exception path isn't guaranteed. Adapt the two token classes to your auth stack. Omit the specific scope constant. Dedicated direct tests pin all branches.
