---
name: Always consult latest Odoo 19 docs
description: Don't rely on training-data knowledge of Odoo 16/17/18 when user is on 19 — flows differ, my memory is stale
type: feedback
originSessionId: a29e76e0-f17f-4cf3-8710-935d7e4539b3
---
Before making claims about how Odoo 19 handles POS/stock/Settle/SO flows, **always verify via**:
1. Live base via MCP (actual current behavior on prod)
2. Existing code snapshots in master-context/ (our actions may already handle the edge case)
3. **Odoo 19 official docs** (doc.odoo.com/19, help.odoo.com, odoo forum for the 19 version)

**Why:** My training knowledge is Odoo 16/17/18-centric. Odoo 19 has changed POS internals notably (stock moves timing, Settle/SO linkage, order reference handling). User caught me in this session asserting a double-stock bug in Settle+ordinary payment flow — the flow actually works fine out of the box, I just had stale model of Settle from older versions.

**How to apply:**
- Never say "this will cause X problem" about POS/SO/stock without a verification step first.
- If I suspect an Odoo quirk — fetch the Odoo 19 doc page, read the actual code on the server (ir.actions.server or model methods), or run a test query.
- When the user says "we already discussed this", trust that and re-verify rather than re-asserting the old claim.
- Odoo changes POS internals almost every major release. Treat POS behavior as version-specific.
