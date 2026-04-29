---
name: Все paper PDF подгрузить в pedido attachments
description: Для каждого из 173 Verdnatura pedidos нужен настоящий paper PDF в ir.attachment
type: project
originSessionId: 37b18c39-25eb-4c7f-b45c-7e6b5ce66cd3
---
Новая задача (29-04-2026): для каждого из 173 Verdnatura 2026 pedidos в Odoo нужно прицепить настоящий paper PDF от поставщика в `ir.attachment` (linked to purchase.order).

**Why:** бумага = первичная правда. Когда возникнут сомнения по цене/qty/SKU — owner сможет открыть PDF из карточки pedido в Odoo и сверить. Сейчас PDF лежит в Holded, но мы переезжаем с Holded в Odoo — Odoo должен стать самодостаточным.

**URL pattern:** `https://app.holded.com/box/file?p=purchaseshipments/<mongoId>/deliverynote<fileId>.pdf`. mongoId известен (из jspairs.json), fileId уникален per albaran (нужно вытащить через Holded API endpoint типа `/documents/<id>/files` или подобный — пока не нашёл точный).

**How to apply:**
- При работе с pedido — проверить есть ли PDF в `ir.attachment`. Если нет — попытаться скачать.
- 16 pedidos с PNG-плейсхолдерами в Downloads (10 KB одинаковых) — это НЕ правильные файлы. Перекачать.
- При reconcile — paper PDF в attachment даёт паспорт правды; если PDF не приклеен и нет в Downloads → не реконсилировать.
