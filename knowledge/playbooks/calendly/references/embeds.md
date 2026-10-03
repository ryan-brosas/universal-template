# Embeds, prefill and browser events

Use an embed when Calendly should render and run the booking flow. Obtain a
`scheduling_url` from the relevant user/event-type response; do not pass an API
resource URI to the widget or infer a private event type from a public slug.

## Choose and initialize the widget

The official widget script is documented at
`https://assets.calendly.com/assets/external/widget.js`. Some older examples use
`https://calendly.com/assets/external/widget.js`; check the current installation
instructions and the site's content-security policy rather than loading both.

- Inline: `Calendly.initInlineWidget({url, parentElement, prefill, utm})`.
- Popup: `Calendly.initPopupWidget({url})` from the intended user interaction.
- Badge: `Calendly.initBadgeWidget({url, text, color, textColor, branding})`.

Load the script once on the client and initialize after both it and the target
container are ready. Use the documented stylesheet where the chosen widget
requires it. In an SPA, avoid duplicate widgets/listeners across navigation and
clean up owned containers/listeners; do not invent an undocumented destroy API.
Confirm container sizing, keyboard/focus behavior, mobile layout and the actual
booking flow in the browser. An inserted iframe alone is not a successful test.

## Prefill and tracking

Use `prefill.name` or `firstName`/`lastName`, `email`, and `customAnswers` keys
`a1` through `a10`. Match the event type's actual questions and name mode. Prefill
is a convenience, not trusted identity or evidence of consent.

The widget `utm` object uses `utmCampaign`, `utmSource`, `utmMedium`, `utmContent`
and `utmTerm`; URLs/API payloads use their documented snake-case forms. UTM
values have a 255-character limit and can be picked up from the parent page's
query string. Keep secrets and sensitive personal data out of URLs and tracking
fields even though the FAQ suggests arbitrary custom values.

For compact layouts, profile/team links use `hide_landing_page_details=1`;
event-type links use `hide_event_type_details=1`. Apply the option for the right
page type. Treat prefill and visibility options as content choices, not ways to
bypass booking requirements.

## Validate parent-window messages

Documented `window.postMessage` events include:

- `calendly.profile_page_viewed`
- `calendly.event_type_viewed`
- `calendly.date_and_time_selected`
- `calendly.event_scheduled`
- `calendly.page_height`

The guide's prefix-only event check is not sufficient for production. Before
analytics, UI updates or resizing, validate an exact expected Calendly origin,
`event.source` against the relevant iframe/window, and the message/payload
shape. A string that merely starts with `calendly.` proves nothing. For height
messages, validate a finite, sensible pixel value before applying it.

`calendly.event_scheduled` carries scheduled-event and invitee URIs. Use it for
UX or analytics; reconcile durable booking state with authenticated API reads
or [verified webhooks](webhooks.md). It is not authoritative evidence of payment,
identity, cancellation or a successful server-side CRM update.

Test a real embed event and reject forged origin/source/payload cases. Verify
that client-only success cannot unlock server-side benefits or duplicate
business actions already processed by the webhook.

## Sources

- [Embed setup](https://developer.calendly.com/api-docs/overview/embedding/getting-started.md),
  [recipes](https://developer.calendly.com/api-docs/overview/embedding/recipes.md).
- [Parent-window events](https://developer.calendly.com/api-docs/overview/embedding/notifying-the-parent-window.md),
  [API-derived scheduling pages](https://developer.calendly.com/docs/api-guides/how-to-display-the-scheduling-page-for-users-of-your-app.md).
