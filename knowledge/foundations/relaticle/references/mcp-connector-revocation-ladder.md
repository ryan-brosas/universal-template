<!-- capsule-v2 -->
# Connector revocation — kill both token generations or the refresh token resurrects access

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you implement "revoke this AI connector" so the client cannot mint a fresh token from its long-lived refresh grant?

## RevokeOAuthConnector + ManageOAuthConnectors projection
**Path/Symbol:** `app/Actions/Mcp/RevokeOAuthConnector.php` (whole, 42L): `execute()` (:19-41); UI `app/Livewire/App/AccessTokens/ManageOAuthConnectors.php` (whole, 99L): `table()` (:26-92); cascade proof `tests/Feature/Mcp/OAuthRefreshTokenCascadeTest.php` (whole, 55L); revocation suite `tests/Feature/Mcp/OAuthConnectorRevocationTest.php`.
**Signature:** `RevokeOAuthConnector::execute(User $user, string $clientId): int` (returns access-token revoke count).
**Data Shape:** Mutates three Passport tables in one transaction: `oauth_refresh_tokens.revoked` (by access_token_id set), `oauth_auth_codes.revoked` (by user+client), `oauth_access_tokens.revoked` (by id set). Empty token set → 0, silent no-op.

### Decisive source
```php
// Passport hands out a long-lived refresh token alongside each access token, so
// revoking the access token alone would let the client mint a fresh one. Both sides
// plus any unredeemed auth code go in the same transaction.
DB::table('oauth_refresh_tokens')
    ->whereIn('access_token_id', $tokenIds)
    ->update(['revoked' => true]);
DB::table('oauth_auth_codes')
    ->where('user_id', $user->getKey())
    ->where('client_id', $clientId)
    ->update(['revoked' => true]);
return DB::table('oauth_access_tokens')
    ->whereIn('id', $tokenIds)
    ->update(['revoked' => true]);
```
The connector LIST is a projection of the token tables, never a separate registry: clients qualify only via a whereIn subselect over the user's live (non-revoked, unexpired) access tokens; the consent-bound team is surfaced by a correlated latest-token subselect (`bound_team_id`); an active-token count badge completes the row.

**Flow:** confirmed danger action in the Filament table → `execute()` in one DB transaction: refresh tokens first (kill the resurrection path), then unredeemed auth codes (kill the re-consent path), then access tokens → notification. Complementary DB-level invariant: deleting an `oauth_access_tokens` row cascades its refresh token (FK on delete), pinned by the cascade test.
**Invariant:** Refresh tokens MUST be revoked in the same transaction as access tokens — access-only revocation is a no-op against a client holding a refresh grant; the connector list must derive from live tokens so a fully revoked client disappears without a registry delete.
**Probe:** `tests/Feature/Mcp/OAuthConnectorRevocationTest.php` (Livewire revoke action), `tests/Feature/Mcp/OAuthRefreshTokenCascadeTest.php` (refresh dies with its access token).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "RevokeOAuthConnector ManageOAuthConnectors oauth_refresh_tokens revoked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt transactional three-table revocation (refresh + auth codes + access) and token-table-derived connector lists for any OAuth resource server exposing "connected apps" management. Adapt table names to your OAuth stack. Omit the Filament UI specifics. Direct tests pin both the action and the DB cascade.
