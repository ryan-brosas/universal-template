<!-- capsule-v2 -->
# Editor markdown normalizer — why do stored bodies carry backslash line breaks, and when are they stripped?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How do you keep a rich-text editor's markdown dialect from leaking into machine-consumed payloads?

## Projection-only content rewrite
**Path/Symbol:** `app/services/messages/webhook_content_normalizer.rb:Messages::WebhookContentNormalizer.normalize` (whole file, 11 lines); call sites `app/models/message.rb#webhook_push_event_data` (lines 172-177).
**Signature:** `normalize(text) -> text.gsub(/\\\r?\n/, "\n").sub(/(\r?\n)+\z/, '')`.
**Data Shape:** input = stored CommonMark-ish source from the TipTap/ProseMirror dashboard editor; output = consumer-facing plain text.

### Decisive source
```ruby
# Strips CommonMark hard line breaks from stored markdown source (backslash before newline).
# ProseMirror / the dashboard editor emits this form so soft breaks survive as markdown;
# webhook consumers expect plain newlines without a visible backslash (e.g. WhatsApp gateways).
# Also strips trailing newlines introduced by TipTap/ProseMirror trailing paragraph nodes.
class Messages::WebhookContentNormalizer
  def self.normalize(text)
    return text if text.blank?

    text.gsub(/\\\r?\n/, "\n").sub(/(\r?\n)+\z/, '')
  end
end
```

**Flow:** editor saves message with hard breaks serialized as backslash+newline (CommonMark's only portable hard-break that survives round-trips through markdown) → STORED AS-IS in message.content → the WEBHOOK/API projection (`webhook_push_event_data`) runs both `content` and `processed_message_content` through normalize → consumers (WhatsApp gateways, customer integrations) receive clean `\n` breaks with no trailing newline noise. Dashboard rendering uses the raw stored form.
**Invariant:** Normalization is PROJECTION-ONLY: the stored canonical body keeps editor semantics so re-editing round-trips faithfully; stripping at write time would corrupt re-editing. Both transforms are ordered — inner hard-breaks first, THEN trailing-newline trim anchored at end-of-string. Blank-safe (returns input unchanged).
**Probe:** `grep -n 'text.gsub' app/services/messages/webhook_content_normalizer.rb` → line 9; direct test `spec/services/messages/webhook_content_normalizer_spec.rb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "WebhookContentNormalizer normalize hard line break", limit: 5 });
```
Resolves `Messages::WebhookContentNormalizer.normalize` line-exact in `app/services/messages/webhook_content_normalizer.rb`.

## Verdict
Adopt store-editor-canonical / normalize-at-projection for any rich-text field with machine consumers; adopt the two-step (hard-break unfold, then tail trim) ordering. Adapt regex to your editor's serialization quirks. Omit the WhatsApp-specific motivation if your consumers are generic JSON clients.
