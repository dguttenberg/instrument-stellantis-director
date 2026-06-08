# Lessons

Format:
## [Date] — [Pattern name]
**What happened:** ...
**Why it happened:** ...
**Rule:** ...

---

## 2026-06-07 — Don't derive structured fields by string-splitting
**What happened:** product_catalog trim view derived `nameplate` via `specific_trim_request.split(" - ")[0]`, yielding "D28H91" (the SKU) instead of "Ram 1500". The director faithfully rendered the wrong nameplate into the Substance row.
**Why it happened:** treated a display string as a parseable source of a distinct field; the data model had no explicit nameplate per trim.
**Rule:** Give every output field an explicit source in the data; never reverse-engineer one field from another's formatting. Add a regression test asserting the resolved value, not just "a value present."

## 2026-06-07 — Fake clients miss API message-contract bugs
**What happened:** the director's corrective-retry appended a bare user text after an assistant `tool_use` block; the live API 400'd ("tool_use without tool_result"). Offline fake-client tests passed because they never validate message structure.
**Why it happened:** the fake always returned valid output on the first call, so the retry path was never exercised, and even when exercised the fake doesn't enforce the API's tool_use/tool_result pairing.
**Rule:** When a retry/multi-turn path builds messages, add an offline test that drives the failure branch and asserts the constructed message shape (roles + block types), since the live API contract won't be checked by a mock.
