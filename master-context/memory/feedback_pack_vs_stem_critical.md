---
name: При ×N inflation > 2 — проверять pack vs stem ПРЕЖДЕ paper-truth
description: Если Odoo qty значительно больше paper qty (×3+, ×8 etc), проверять paper UD VENTA Paquete + Odoo product_uom — может Holded бухгалтер прав, открыл паки и пересчитал стебли
type: feedback
originSessionId: 6b381e60-7fe7-433a-8816-4f7099a83660
---
**Правило:** при дельте `Odoo_qty / paper_qty > 2` НЕ применять paper-truth слепо. Сначала проверить:

1. **Paper UD VENTA**: содержит ли подстроку "Paquete" (под основной строкой albaran). Если да — paper qty в paquetes, не stems.
2. **Odoo product_uom**: какой unit на purchase.order.line (Tallo/Unidades vs Paquete id=31).
3. **Match check**: если paper UD=Paquete и Odoo unit=stem с ratio совпадающим (Odoo qty ≈ paper qty × stems_per_paq), то **Holded бухгалтер ПРАВ** — он раскрыл паки и пересчитал стебли (валидный recount). Не применяй paper-truth.

**Why:** 29 апреля 2026 г. Agent на pedido 12267946 переписал Odoo qty с 40→5 на SKIMMIA Yuki «по paper-truth», получив SKIMMIA Yuki ×8 «inflation». На самом деле paper говорил 5 paquetes, Odoo бухгалтер забил 40 stems (ratio 8 stems/paq) — это **корректный recount после открытия паков**. Я применил paper-truth → на складе оказалось 5 стеблей вместо 40. Owner поймал ошибку, велел rollback. Это критичная ошибка — handover Pilot 2 lesson о pack→stem я игнорировал.

**How to apply:**
- Перед write на line с ×N delta — обязательно `pdftotext -layout paper.pdf | grep -B1 -A2 "<concepto>"` чтобы увидеть UD VENTA strings.
- Если paper paquete + Odoo stems ratio OK → log «✅ pack/stem OK, Holded прав» + НЕ переписывать qty. Phase A: ставить supplier_sku, supplier_product_name, expected_qty (paper paquetes), price (paper PVP/paq), но **product_qty НЕ менять**.
- Если paper paquete + Odoo qty неверный (stems не совпадают с ratio) — pack-conversion: `update_record(line, {product_uom: 31, product_qty: paper.cant_paq, price_unit: paper.pvp})`.
- Если paper stems + Odoo stems с ×N delta — это реально pereсчёт ошибка, paper-truth wins.
- **>×2 delta** = red flag, всегда verify pack/stem prior.

**Иерархия принятия решения**:
1. UD VENTA Paquete в paper + matching ratio → Holded прав, не трогаем qty (только Phase A на supplier fields)
2. UD VENTA Paquete в paper + mismatching ratio (Odoo qty неверный) → pack-conversion (uom→31)
3. UD VENTA не paquete в paper + Odoo и paper равные → R1 standard match
4. UD VENTA не paquete в paper + delta ×N — реальный пересчёт, paper-truth wins

**Связанные памятки**: handover §3.1 Pilot 2 (uom→Paquete on 4 pack lines), handover §5.7 hypothesis ×2 (исходно был только ×2, но реально включает ×3-×8 при pack/stem confusion).
