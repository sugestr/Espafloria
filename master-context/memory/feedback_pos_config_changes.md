---
name: POS config changes требуют closed sessions
description: Перед изменением pos.payment.method, pos.config.payment_method_ids, warehouse_id, picking_type_id — убедиться что по этому config НЕТ открытых и opening_control сессий
type: feedback
originSessionId: a29e76e0-f17f-4cf3-8710-935d7e4539b3
---
Перед любым изменением payment methods / warehouse / picking_type / attached methods на `pos.config` или `pos.payment.method` — **все** сессии этого config должны быть в state `closed`. Odoo 19 специально блокирует write'ы с ошибкой «закройте открытые сессии».

**Важный нюанс:** после закрытия сессии Odoo 19 **автоматом** создаёт следующую в state `opening_control` (для удобства следующей смены). Эта «предоткрытая» сессия считается активной для целей блокировки конфига. Она называется «/», owner = тот, кто последним открыл POS UI.

**Как применять:**
1. Закрыть все open sessions через штатный Close (UI или action_pos_session_closing_control).
2. Поискать дополнительно `pos.session.state in ('opened', 'opening_control')` — найти oстатки.
3. Cancel/close opening_control через backend (POS → Sessions → Cancel) либо full cycle через POS UI (Open → 0 cash → Close).
4. Потом делать изменения config'а.

**Связано с инвариантами:** §45 (POS cache refreshes после config changes), §17 (automation timing — cache/delays ненадёжны).

**Контекст случая:** 23 апреля 2026 после теста 1.1 в POS Plaza/00023 — закрыли смену, появилась session 38 в opening_control. Update имени pos.payment.method id=6 отклонён с ошибкой «Please close open sessions».

## Required fields для pos.payment.method (23 апр 2026 доп)

При создании нового `pos.payment.method` через MCP `create_record` — поля не required для API, но **форма в UI требует** их при первом открытии. Обязательно выставить:

- **`outstanding_account_id`** — required в UI. Для technical методов (Bouquet Internal и т.п.) — тот же account что `journal_id.default_account_id`, обычно `555000 Items pending application` (id=368 у Espafloria). Для реальных bank/card method'ов — transit account (572xxx). Для cash — cash transit (570xxx).
- **`journal_id`** — required везде. Тип journal'а = 'bank' обычно, даже для cash методов.

**Почему через create_record можно без этих полей:** Odoo API принимает create без validation этих полей (no `required=True` на field definition, валидация через `attrs` на form view). Но как только user открывает форму — constraint срабатывает и требует заполнить.

**Проверка после create:** всегда после создания нового `pos.payment.method` через MCP выставлять `outstanding_account_id` явным update'ом, чтобы form была валидной сразу.