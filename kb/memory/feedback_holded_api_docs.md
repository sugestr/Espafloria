---
name: Always consult latest Holded API docs
description: Don't rely on training-data knowledge of Holded API — verify endpoints, payload shapes, and auth headers against current Holded developer docs before asserting behavior
type: feedback
originSessionId: 37b18c39-25eb-4c7f-b45c-7e6b5ce66cd3
---
Before making claims about how Holded API handles albaranes / facturas / products / attachments / contacts, **always verify via**:
1. Holded official developer docs (https://developers.holded.com or current equivalent)
2. The actual MCP tool definitions of the Holded connector once it's loaded (read tool descriptions and parameter schemas, don't guess)
3. A small test call against a known record before bulk processing

**Why:** Holded is a Spanish ERP that the user is migrating away from. My training knowledge of Holded is sparse and likely stale. Endpoint paths, response shapes, attachment access patterns, and rate limits change. The user explicitly asked me to apply the same "verify before assert" discipline to Holded that I apply to Odoo 19.

**How to apply:**
- Never say "Holded API endpoint X returns Y" without checking the docs or running a test call.
- When the Holded MCP connector becomes available — re-read its tool definitions in full before designing any batch flow on top of it.
- Pay particular attention to: how attachments (PDF albaran files) are exposed, how albaran lines are paginated, how product codigo_de_fabricacion field is named, how vendor identification works.
- For our Espafloria reconciliation task: validate Holded → Odoo data shape mapping on 1-2 records before bulk.

**Context:** This rule extends the same discipline as `feedback_odoo_version_docs.md` to the Holded platform. Both platforms in this project (Odoo 19 + Holded) require docs-first, memory-skeptical workflow.
