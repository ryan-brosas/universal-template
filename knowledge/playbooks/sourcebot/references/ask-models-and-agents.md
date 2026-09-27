# Ask, model providers, connectors and review agents

Ask searches/navigates indexed code to produce answers with citations and code
snippets. Keep research scoping and freshness rules in
[the canonical workflow](../../cross-repo-source/README.md). Configuration here
supplies capabilities; it does not grant permission for external tool writes.

## Model selection and data flow

At least one `models` entry is required. `provider` and `model` are required in
each variant; `openai-compatible` also requires `baseUrl`. The installed schema
rejects unsupported fields. Use `displayName`, supported `temperature`/`headers`
and provider-specific controls deliberately; discover configured models rather
than guessing IDs. Headers and compatible-provider `queryParams` can use
strings or secret references. Check the destination before sending private code.

For explicit MCP Ask selection, preserve the discovered model identity, including
`displayName` when present. In v5.1.13,
[`getLanguageModelKey`](https://github.com/sourcebot-dev/sourcebot/blob/v5.1.13/packages/web/src/features/chat/utils.ts#L505-L512)
uses provider, model **and display name**. Sending only provider/model can report
“not configured” even though discovery lists it; the complete identity succeeded
in a live check. Diagnose this caller mismatch before changing credentials or
provider configuration.

| Provider identifier | Setup / diagnostic distinction |
| --- | --- |
| `amazon-bedrock` | AWS access key, secret, session token and region can resolve from standard AWS environment variables; check runtime identity/region. |
| `anthropic` | `token` uses `x-api-key`; `authToken` uses `Authorization: Bearer`. Do not interchange them. |
| `azure` | `model` is the Azure deployment name. Supply `resourceName` or `baseUrl`; the latter wins. `apiVersion` defaults to `preview` in the reviewed schema. |
| `deepseek` | Token can resolve from `DEEPSEEK_API_KEY`; verify the model and endpoint supported by the deployment. |
| `google-generative-ai` | Token can resolve from `GOOGLE_GENERATIVE_AI_API_KEY`. Gemini 3 uses `thinkingLevel`; Gemini 2.5 uses `thinkingBudget`. |
| `google-vertex` | Project/region/application credentials must be available to the runtime; an explicit credentials value is a mounted file path. |
| `google-vertex-anthropic` | Use this separate variant for Anthropic models on Vertex, not `google-vertex`. |
| `mistral` | Token can resolve from `MISTRAL_API_KEY`. |
| `openai` | Token can resolve from `OPENAI_API_KEY`; inspect reasoning controls for the selected model. |
| `openai-compatible` | Chat Completions-compatible endpoint, including self-hosted Ollama/llama.cpp; required `baseUrl`, optional token/query parameters. |
| `openrouter` | Token can resolve from `OPENROUTER_API_KEY`; use the provider's actual model ID. |
| `xai` | Token can resolve from `XAI_API_KEY`. |

OpenAI/Azure document `reasoningEffort` default `medium` and `reasoningSummary`
default `auto` (`detailed`/`none` alternatives). Gemini `thinkingLevel` is
`minimal|low|medium|high`; `thinkingBudget=-1` selects dynamic budgeting for
supported models. These are provider/model-specific controls, not universal
fields to add to every entry.

For llama.cpp's “tools param requires --jinja flag” error, configure `--jinja`.
For leaked reasoning XML, inspect the compatible provider's `reasoningTag`
(default `think`). For errors only while streaming, distinguish model failures
from a proxy/load-balancer long-lived-connection timeout; the Ask guide suggests
a sufficiently long timeout such as five minutes. Client/MCP deadlines are a
separate boundary. Image limits and optional user-email headers are in
[operations](configuration-and-operations.md).

## Outgoing Ask connectors versus incoming Sourcebot MCP

These are opposite directions. [Sourcebot MCP](setup-and-access.md) lets an
external agent read Sourcebot. Ask **connectors** let Sourcebot call another
MCP server, potentially performing external writes.

An Owner adds a connector URL in Settings → Workspace → Ask Sourcebot. Dynamic
OAuth client registration is attempted when supported; otherwise supply a
registered client ID/secret securely. Select discovered/custom scopes carefully.
`offline_access` is preselected when offered for refresh; omitting it can force
reauthentication or prevent authorization. **Changing scopes makes all users
reauthenticate.**

Tool policy is independent: Allowed, Needs Approval or Blocked. Policy changes
apply immediately without reauthentication. Read-only hints drive grouping;
without a hint a tool is treated as write/delete. Do not weaken approvals merely
to finish an investigation. Members connect in Settings → Account → Ask Sourcebot,
inspect tools and toggle connectors per chat. Approval-requiring calls pause for
consent. Calls use the connected user's permissions, not organization-wide access.
Verify identity, scopes, selected connector and an authorized harmless tool call.

## Chat visibility and native skills

Private is owner-only even with the link. Public means anyone with the link;
anonymous viewing depends on instance policy, and viewers may duplicate the chat.
Inviting named organization members to a private chat requires the documented
Enterprise entitlement; invitees can view messages/citations, not edit, send,
delete or invite others. Remove access through Share. Never use public visibility
as shorthand for “team-only.”

Reusable Ask instructions, imports, personal/shared catalogs and repository sync
are covered in [native skills](native-skills.md). They are not this local skill.

## Experimental code-review agent

Agents are experimental and may change outside major releases. Review setup is
an external integration with write effects, not an automatic follow-on to reading
these docs. Choose the model: `REVIEW_AGENT_MODEL` is a configured model's
**`displayName`**, not provider/model ID; unset selects the first configured model.

| Host | Required integration |
| --- | --- |
| GitHub | Installed GitHub App; reachable `/api/webhook`; pull-request and issue-comment events; Pull requests and Issues Read & Write, Contents Read. Set `GITHUB_REVIEW_AGENT_APP_ID`, `GITHUB_REVIEW_AGENT_APP_WEBHOOK_SECRET`, and container-readable `GITHUB_REVIEW_AGENT_APP_PRIVATE_KEY_PATH`. |
| GitLab | PAT or project token with `api` scope; Merge request and Comments webhook events to `/api/webhook`. Set `GITLAB_REVIEW_AGENT_WEBHOOK_SECRET`, `GITLAB_REVIEW_AGENT_TOKEN`, optional `GITLAB_REVIEW_AGENT_HOST` (default `gitlab.com`). |

The feature guide calls the GitHub identifier a client ID while the environment
reference calls it App ID; verify the installed integration rather than assuming
those provider identifiers are interchangeable. The general environment page
also lists `OPENAI_API_KEY` / `REVIEW_AGENT_API_KEY`, whereas the newer feature
guide selects configured models. Follow the release-specific feature contract.

`REVIEW_AGENT_AUTO_REVIEW_ENABLED=false` disables automatic new/updated PR/MR
reviews. An authorized `/review` comment triggers manually;
`REVIEW_AGENT_REVIEW_COMMAND` changes the command without its leading slash.
The Agents card confirms configuration, not successful review delivery. Verify
webhook delivery and one approved test PR/MR review before broad auto-review.

`REVIEW_AGENT_LOGGING_ENABLED` writes prompts/responses under the documented
review-agent cache path. The general environment page says default `true`, but
the feature guide says unset: set it explicitly according to data policy and
verify actual logging. These logs can contain private code and model responses.

## Official sources

- [Ask](https://docs.sourcebot.dev/docs/features/ask/ask-sourcebot.md), [models and schema](https://docs.sourcebot.dev/docs/configuration/language-model-providers.md)
- [Connectors](https://docs.sourcebot.dev/docs/features/ask/connectors.md), [sharing](https://docs.sourcebot.dev/docs/features/ask/chat-sharing.md), [skills](https://docs.sourcebot.dev/docs/features/ask/skills.md)
- [Agents](https://docs.sourcebot.dev/docs/features/agents/agents.md), [review agent](https://docs.sourcebot.dev/docs/features/agents/review-agent.md), [environment reference](https://docs.sourcebot.dev/docs/configuration/environment-variables.md)
