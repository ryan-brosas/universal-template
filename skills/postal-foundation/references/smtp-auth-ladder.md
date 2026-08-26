<!-- capsule-v2 -->
# SMTP AUTH ladder — how do you authenticate API-style credentials over PLAIN/LOGIN/CRAM-MD5 where the username is an org/server path?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** How are the three AUTH verbs implemented so each resolves to the same credential grant, including a challenge-response variant that never sees the plaintext key?

## Client#auth_plain / auth_login / auth_cram_md5 / authenticate
**Path/Symbol:** `app/lib/smtp_server/client.rb:SMTPServer::Client` (`auth_plain` :182–207, `auth_login` :209–231, `auth_cram_md5` :244–284, `authenticate` :233–242; `CRAM_MD5_DIGEST` constant :9).
**Signature:** all return `"235 Granted for <org>/<server>" | "535 …"`; CRAM-MD5 returns the Base64 challenge first and installs a one-shot `@proc` for the response.
**Data Shape:** identity = `org_permlink[/\/_]server_permalink`; secret = `Credential(key:, type: "SMTP")`; CRAM-MD5 response = `username + " " + HMAC-SHA1(credential.key, challenge)`.

### Decisive source
```ruby
def auth_cram_md5(data)
  challenge = "<#{Digest::SHA1.hexdigest(Time.now.to_i.to_s + rand(100_000).to_s)[0, 20]}@#{...smtp_hostname}>"
  handler = proc do |idata|
    @proc = nil                                   # one-shot: next line goes back to command dispatch
    username, password = Base64.decode64(idata).split(" ", 2)
    org_permlink, server_permalink = username.split(/[\/_]/, 2)
    server = ::Server.includes(:organization).where(organizations: { permalink: org_permlink },
                                                    permalink: server_permalink).first
    return "535 Denied" if server.nil?            # (via next inside proc → handler return)
    server.credentials.where(type: "SMTP").each do |credential|
      correct = OpenSSL::HMAC.hexdigest(CRAM_MD5_DIGEST, credential.key, challenge)
      next unless password == correct             # timing-insensitive compare is acceptable here only because
      @credential = credential; @credential.use   # keys are high-entropy server-side secrets — pin this decision
      return "235 Granted for #{credential.server.organization.permalink}/#{credential.server.permalink}"
    end
    "535 Denied"
  end
  @proc = handler
  "334 " + Base64.encode64(challenge).gsub(/[\r\n]/, "")
end

def authenticate(password)                        # shared tail for PLAIN/LOGIN
  if @credential = Credential.where(type: "SMTP", key: password).first
    @credential.use; "235 Granted for #{@credential.server.organization.permalink}/#{@credential.server.permalink}"
  else ... "535 Invalid credential" end
end
```

**Flow:** PLAIN decodes `authzid\0authcid\0password` and calls `authenticate`; LOGIN issues two `334` prompts (username then password) via the same proc mechanism; CRAM-MD5 issues one challenge and verifies by recomputing the HMAC per candidate credential of the named server. On success every path sets `@credential` and marks it used (`credential.use`) so later `RCPT TO` classifies as outgoing.
**Invariant:** the username namespace is hierarchical (`org/server`, `/` or `_` separator) and resolved BEFORE any secret comparison — no cross-org oracle; the plaintext key never appears in a challenge; `@proc` is cleared on its first invocation so AUTH cannot be replayed as a body-mode continuation.
**Probe:** `spec/lib/smtp_server/client/auth_spec.rb` (:1–138); rcpt_to_spec.rb:108–124 pins the downstream effect (`AUTH PLAIN` then RCPT TO ⇒ `[:credential, …]` recipient).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "postal", qualified_name: "postal.app.lib.smtp_server.client.SMTPServer.Client.auth_cram_md5" });
```

## Verdict
Adopt the resolve-identity-then-verify-secret ordering, the one-shot proc per AUTH exchange, and uniform `235 Granted for org/server` grants feeding a session-wide credential. Adapt the username grammar to your tenancy model. Omit the non-constant-time comparison only after re-pinning the high-entropy-key assumption in your host.
