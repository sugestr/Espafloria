---
name: Espafloria Odoo partner IDs
description: Конкретные partner_id для Verdnatura и системных партнёров — чтобы не путать с другими записями
type: project
originSessionId: 37b18c39-25eb-4c7f-b45c-7e6b5ce66cd3
---
Live-проверенные partner_id в espafloriasl.odoo.com:

- **42** — VERDNATURA LEVANTE SL (vat B97367486, supplier_rank=1) — основной поставщик цветов
- **56** — 🤖 Claude AI Reconciliation (anti-fraud system user, нужен в supplierinfo author и mail.message author_id)
- **53** — 🌹 Букет на витрину (TECH_PARTNER для anonymous SO букетов)

**Why:** в моих ранних сессиях контекст ошибочно говорил partner_id=23 для Verdnatura. На самом деле 23 — рандомная запись «Washington State Department of Social and Health Services», у неё 0 supplierinfo. Все 406 supplierinfo для Verdnatura прицеплены к 42.

**How to apply:** при работе с Verdnatura supplierinfo / pedido / purchase order — всегда partner_id=42. Перед массовой записью верифицировать через `mcp__odoo__search_records` model=res.partner domain=[["name","ilike","verdnatura"]].
