---
name: Odoo — всегда методы/actions, не прямые writes
description: Перед update_record на state/qty/audit-поля — искать штатный action/method. Writes в обход логики ломают computed fields, audit trail и смежные эффекты.
type: feedback
originSessionId: 357b0c8b-0dd6-43b6-b89a-91c8b9829a31
---

**Правило:** прежде чем править запись в Odoo через `update_record`/`write`, проверить — есть ли **штатный action/method**, который делает то же с правильными side effects. Если есть — звать его. Прямой write — только когда штатного пути нет.

**Почему это важно:**

1. **State machines** (pos.session, sale.order, stock.picking, mrp.production и т.п.) — штатный action (`action_confirm`, `action_cancel`, `button_validate`, `action_pos_session_closing_control` и т.д.) выставляет все смежные поля и проводки. Прямой write ломает computed fields.
2. **Inventory (stock.quant)** — штатный путь: write `inventory_quantity` + call `action_apply_inventory` → Odoo создаёт `stock.move` с правильными source/dest locations. Прямой write в `quantity` обходит audit trail (нет stock.move, нет истории, отчёты по движениям ломаются).
3. **Смежные эффекты** — многие штатные actions триггерят chatter-сообщения, notifications, автоматизации. Write в обход их пропустит.

**Конкретные кейсы:**
- 22 апреля 2026 в Espafloria force-closed pos.session id=34 через `write({'state': 'closed'})` без `stop_at`. На следующий день Owner не смог открыть POS — `_compute_last_session` пытался `.astimezone()` на `False` и падал с RPC_ERROR. Штатный action закрытия выставил бы `stop_at` сам.
- 23 апреля 2026 при тесте букетов нужно было поднять stock с -12 до 10 — правильный путь был `stock.quant.inventory_quantity=10 + action_apply_inventory`, а я попросил user сделать через UI. Правильный ход — но следующий раз искать метод сначала.

**Как применять:**

1. Перед любым `update_record` на критичное поле — вспомнить: «это data edit или state/audit действие?».
2. Если state/audit — искать в модели метод с префиксом `action_`, `button_`, `do_` или публичный method в source.
3. Если есть — звать через `mcp__odoo__execute_method`. Если в моём MCP такого инструмента **нет** — либо просить user сделать через UI (3 клика), либо создать `ir.actions.server` с кодом и запустить.
4. Прямой write на critical поля — только при отсутствии штатного пути, и только с пониманием, что computed/audit сломается.

**Mental check:** «Если бы эту запись менял живой человек в UI — что бы он нажал?» Если кнопку с именем — её и надо звать.
