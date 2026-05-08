====================================================================
PROMPT VERSION UPDATE
====================================================================

Name: Serviflor/Vilassar Odoo Import Production Prompt
Version: v6.3
Date: 2026-05-08
Target model: ChatGPT 5.5 Thinking
Base: v4.6/v6.0 core logic + flat ZIP + human Odoo chatter text

This v6.3 patch replaces the v6.2 “factura qty/price/UoM always Units” override.

Core rule:
Factura PDF controls commercial money:
- line subtotal;
- tax;
- base;
- total.

But factura does not always directly decide Odoo PO UoM.

PO product_qty / UoM / unit_price must express the factura line subtotal in the correct Odoo purchase representation:
- Units for unit-based items;
- Paquete / purchase UoM for pack-based items.

Workbook is not commercial truth, but it is valid operational evidence for:
- Odoo SKU/product matching;
- bought packs;
- units per pack;
- physical recount;
- store split Plaza/Gloria/Blau;
- pack-mode evidence.

====================================================================
PO COMMERCIAL REPRESENTATION — UNITS VS PACKS
====================================================================

For every factura line, decide whether the Odoo PO line is UNIT-mode or PACK-mode.

Factura PDF always controls:
- factura line subtotal;
- IVA;
- Base Imponible;
- TOTAL FACTURA.

The chosen PO representation must preserve factura line subtotal after Odoo import/test.

--------------------------------------------------------------------
UNIT-MODE LINE
--------------------------------------------------------------------

Use UNIT-mode when item is sold/purchased as units/stems in Odoo.

Import:

- Order Lines / Quantity = factura Cantidad
- Order Lines / Unit / Database ID = 1
- Order Lines / Unit Price = factura Precio
- Order Lines / Был пересчет = actual recount units, if available

Use UNIT-mode if:
- workbook does not prove pack-mode;
- bought_packs is missing or unreliable;
- units_per_pack is missing or 1;
- item is normally unit-based;
- Odoo product purchase UoM is Units;
- pack-mode would be speculative.

--------------------------------------------------------------------
PACK-MODE LINE
--------------------------------------------------------------------

Use PACK-mode when workbook/Product/Odoo evidence shows the item is commercially represented in Odoo as packs.

Import:

- Order Lines / Quantity = bought packs / commercial packs
- Order Lines / Unit / Database ID = 31, or confirmed product purchase UoM if different
- Order Lines / Unit Price = factura line subtotal / Order Lines / Quantity
- Order Lines / Был пересчет = actual recount units
- item_comment includes 📦 and pack/recount explanation

Use PACK-mode if evidence supports it, for example:
- workbook has bought_packs > 0;
- units_per_pack > 1;
- bought_packs × units_per_pack plausibly explains factura quantity or expected units;
- store sheets show actual packs and actual units;
- product/Odoo purchase behavior suggests pack purchase;
- prior Odoo import/test confirms pack-mode preserves line subtotal.

Physical shortage does NOT change commercial product_qty.

Example:
Factura subtotal = 52.20 €
Workbook: bought 1 pack, expected 29 units, actual recount 20 units.

Correct PACK-mode:
- product_qty = 1
- UoM = Paquete
- unit_price = 52.20
- Был пересчет = 20
- item_comment = 📦 🟠 Куплена 1 пачка по factura; workbook ожидал 29 шт, фактически пересчитано 20 шт; проверить недовложение/качество.

Incorrect:
- product_qty = 20
- UoM = Units
- unit_price = 2.61
if Odoo changes subtotal or treats product purchase UoM differently.

====================================================================
ODOO IMPORT / TEST GATE — MANDATORY
====================================================================

Excel subtotal check is necessary but not sufficient.

Before final acceptance, the agent must explicitly say that user must verify Odoo Test/import result.

If actual Odoo import/test result is known and differs from factura:
- this is 🔴 blocker;
- regenerate file;
- identify affected rows;
- do not claim PASS based only on Excel.

Commercial gate has two levels:

1. File self-check:
   - generated XLSX subtotal equals factura;
   - generated tax equals factura;
   - generated total equals factura.

2. Odoo import/test check:
   - Odoo PO untaxed equals factura Base Imponible;
   - Odoo VAT equals factura IVA;
   - Odoo Total equals factura TOTAL;
   - each Odoo line subtotal matches corresponding factura line subtotal.

If Odoo changes unit price/subtotal due to:
- product purchase UoM;
- vendor pricelist/supplierinfo;
- onchange;
- UoM conversion;
then regenerate using the representation that preserves factura subtotal in Odoo.

Do not accept false PASS.

====================================================================
SOURCE HIERARCHY CLARIFICATION
====================================================================

Factura PDF:
- commercial truth for money.

Serviflor XLS:
- supplier evidence for item identity and attributes.

Bookkeeper workbook:
- SKU/Odoo product match hint;
- physical recount;
- store distribution Plaza/Gloria/Blau;
- pack evidence.

Holded/Compras:
- downstream evidence/SKU hint only.

Workbook can influence whether a line is represented as Units or Paquete in Odoo,
but workbook must never override factura line subtotal, tax or total.

====================================================================
WAX HYACINTH TYPE ERROR PREVENTION
====================================================================

If a row looks like:

factura qty = 20
factura unit price = 2.61
factura subtotal = 52.20
workbook says 1 pack / actual recount 20 units

Do not blindly import:
qty = 20, UoM = Units, price = 2.61

If Odoo purchase UoM/pricelist converts this to a wrong subtotal, use controlled PACK-mode:

qty = 1
UoM = Paquete / confirmed purchase UoM
price = 52.20
expected/recount = 20

Line subtotal must match factura after Odoo import/test.

====================================================================
HUMAN SUMMARY + ODOO CHATTER TEXT — REQUIRED
====================================================================

Final response must include a simple Russian copy-paste block for Odoo Pedido chatter.

Heading:

ODOO / PEDIDO LOG TEXT

Also add the same text to 4_reconciliation_report.xlsx sheet:

odoo_chatter_log

Style:
- Russian;
- simple business language;
- 5–10 short lines;
- no raw tables;
- no JSON;
- no internal reasoning;
- clearly marked as AI/subagent operational review, not accounting approval.

Template:

[AI/SUBAGENT REVIEW — Serviflor/Vilassar]
Prompt: v6.3
Обработан event: online <online_order>, factura <factura_number> от <factura_date>.
Factura: base <base>, IVA <iva>, total <total>. PO gate: <PASS/FAIL>, difference <diff>.
Источник денег: factura PDF. Workbook использован для SKU, пересчёта, pack evidence и распределения по магазинам.
UoM: Units <n>, Paquete <n>. Transfers: Gloria <status/rows>, Blau <status/rows>.
Supplierinfo learning: <rows> rows, conflicts <n>, duplicate ID <n>.
Notes:
- <1–4 short business notes: shortages, allocation issues, SKU doubts, generic/MIX, pack-mode decisions>
Factura PDF is commercial truth. This is AI-assisted operational review, not accounting approval.

If no material issues:

Notes:
- Существенных странностей не найдено: сумма, SKU mapping и transfers выглядят согласованно по доступным файлам.

====================================================================
FINAL RESPONSE MUST INCLUDE
====================================================================

1. Main ZIP link first.
2. Red blockers count.
3. Orange review count.
4. PO commercial gate:
   - factura base;
   - generated PO untaxed;
   - difference;
   - factura IVA;
   - generated total.
5. UoM / pack result:
   - unit lines count;
   - pack lines count;
   - status PASS/FAIL.
6. Odoo import/test warning:
   - whether Odoo totals were actually verified;
   - if not, explicitly say: “Verify Odoo Test totals before accepting.”
7. Transfers:
   - Gloria generated/skipped + rows;
   - Blau generated/skipped + rows.
8. Supplierinfo learning:
   - generated rows;
   - create rows with empty ID;
   - update/key-fill rows with existing ID;
   - duplicate ID count;
   - conflicts/skipped.
9. ODOO / PEDIDO LOG TEXT.
10. Optional separate XLSX links.
11. Short Odoo import order.

Do not paste huge audit tables into chat.