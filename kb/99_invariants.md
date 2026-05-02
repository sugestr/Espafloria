<!-- v: 10 | updated: 2026-05-02T23:30Z -->
# 99. Invariants — железные правила проекта

**Читать перед любыми изменениями в системе.** Нарушение этих правил создаёт техдолг, ломает бот или теряет данные.

> 📌 **Структура:** 5 жёстких глобальных правил проекта, потом раздел «Odoo 19 gotchas» (поведенческие квирки самого Odoo). Архитектурные истины бизнеса (paper≠fact, marketplace=intermediary и т.д.) — в `01_project.md`. Тех-детали по доменам (POS, букеты, eWallet, бот, миграция) — в файлах 02-08.

---

## 🔧 Жёсткие правила проекта

### 1. CHANGELOG обязателен после правок
После **любого** изменения в базе (своими руками или через API) — запись в `CHANGELOG.md` с датой, автором, что изменили. Одна строка сверху на сессию: `- YYYY-MM-DD — <subject>`. Больше 15 строк — удалить самую старую.

### 2. Архив всех custom Python-скриптов — в репо
Любой `ir.actions.server` или `base.automation` с Python-кодом, работающий на prod Odoo, обязан иметь зеркало `.py` в `kb/add/` с префиксом блока (`NN_`).

**Истина по факту работы — prod Odoo.** Репо — архив/бекап на случай потери БД, плюс git-history и review.

Актуальные пары:
- `add/05_migrate_variant_action.py` ↔ `ir.actions.server id=1145`
- `add/05_migrate_variant_v2.2.py` ↔ `ir.actions.server id=1176`
- `add/03_calculate_in_shop_action.py` ↔ `ir.actions.server id=1150`
- `add/03_review_status_automation.py` ↔ `ir.actions.server id=1146`
- `add/04_bouquet_on_payment_action.py` ↔ `ir.actions.server id=1203`
- `add/04_bouquet_on_dismantle_action.py` ↔ `ir.actions.server id=1209`

### 3. Не мигрировать на Odoo.sh без жёсткой нужды
Сейчас мы на **Odoo Online (SaaS) Custom**. Переход на Odoo.sh — **one-way** (после `custom_addons` обратно нельзя). **Сначала всё что можно — штатно на Online** (Studio + Automated Actions + Server Actions с Python разрешены).

Жёсткие триггеры миграции — только когда хотелка физически невозможна на Online. Сейчас единственный жёсткий драйвер — photo capture в POS UI (требует custom OWL widget). См. [add/04_pos_audit_2026-04-25.md](add/04_pos_audit_2026-04-25.md).

### 4. Перед утверждением поведения Odoo — свериться с docs 19 / community / live-базой
**Не утверждать из памяти/тренировки.** Odoo 19 ≠ 17/18 во многих местах. Сверять:
- [Odoo 19 docs](https://www.odoo.com/documentation/19.0/)
- live Odoo через MCP (`server_info`, `list_models`, проверка полей и API)
- community: [Odoo Forum](https://www.odoo.com/forum), [OCA repos](https://github.com/OCA)

**Подкреплено инцидентами:** state machine POS (нельзя `write({'state':'closed'})` — ломает computed; нужен штатный `action_pos_session_close`); `stock.return.picking` API (нет `location_id` в vals, нужен `.sudo()`); `sale.order.line.discount` перезатирается на create (нужен `.write({'discount':...})` после).

### 5. Сначала штатное Odoo 19 / Apps Store / OCA — потом custom
**Каждый custom field / action / module — осознанная цена поддержки.** Прежде чем писать кастом:
1. Проверить нативные возможности Odoo 19 (Quality, Approvals, Project, Maintenance, Barcode, Cycle Counts, Loyalty, Pricelists и т.п.)
2. [Odoo Apps Store](https://apps.odoo.com/) — особенно фильтр «Compatible with Odoo Online»
3. [OCA](https://github.com/OCA) — если на Odoo.sh (на Online не поедет)
4. Только если ничего нет — custom

**Подкреплено:** аудит 2026-04-25 показал что 7/9 хотелок POS закрываются штатно без миграции на Odoo.sh.

---

## ⚠️ Odoo 19 gotchas

Поведенческие квирки самого Odoo, на которые наступали. Не «инварианты бизнеса», а «не наступай на эти грабли при работе с движком».

### G1. Нет каскадных `write()` в automation rules
Line-level automation — только для **текущей** строки. Document-level — только явной кнопкой / server action. Иначе Odoo висит или рекурсивно триггерит сам себя.

### G2. `When updating field` в automation — узкий список
Watched fields = минимум. Включать только те, изменение которых должно срабатывать. Не включать структурные поля (picking_id, purchase_line_id) и сами вычисляемые (review-статусы) — иначе автокаскад на самого себя.

### G3. `On create` + `After creation delay` — ненадёжны
Odoo может перезаписать значения своей логикой. Delayed actions срабатывают недетерминированно (даже после Cancel/state change). Для reset-логики — **только явная кнопка**, не delay.

### G4. `safe_eval` в server actions / automations: `hasattr` запрещён
- ❌ `hasattr(record, 'field_name')`
- ✅ `'field_name' in record._fields`

### G5. `safe_eval`: many2one record ≠ string
Поля типа `uom.uom`, `product.product`, `res.partner` — это **records**, не строки. У них нет `.strip()`. Использовать `.display_name`, `.name`, или явный `str(...)`.

### G6. archive/restore — писать на template-level, не variant
Odoo каскадирует `template.active` → `variants.active` автоматически. Прямой write в `variant.active` создаёт desync (template.active=True, variant.active=False).

### G7. Studio-поля на template+variant (related) — писать на template для UI
Если Studio-поле существует на обоих уровнях — писать на template. Только так значения гарантированно видны на template form и наследующих views. Variant-only значения могут не пробросить наверх в UI.

### G8. State machines — через штатные actions, не через `write({'state': ...})`
Прямая запись в state ломает computed-поля. Пример: `pos.session.write({'state': 'closed'})` ломает `stop_at` — нужен `action_pos_session_close()`.

### G9. POS config changes требуют closed sessions
Перед update payment methods / warehouse / picking_type — все сессии POS должны быть в state=closed. Включая auto-созданную opening_control после Close Register. Иначе constraint error.

### G10. `stock.return.picking` API (Odoo 19)
- В `vals` нет `location_id` (отличие от 17/18).
- Нужен `.sudo()` если вызывается из POS-user контекста.
- `action_create_returns()` возвращает `dict` с `res_id`, не record.

### G11. `sale.order.line.discount` перезатирается на create (pricelist onchange)
При `create([{..., 'discount': X, ...}])` дисконт теряется из-за pricelist onchange. **Решение:** после create сделать `.write({'discount': X})` на линиях.

---

## Краткая мнемоника

> **CHANGELOG → scripts archive in repo → Online before .sh → check 19 docs/live → ready before custom.**

> **Gotchas: no cascading writes, narrow watched fields, no `On create` delay, no `hasattr` in safe_eval, m2o ≠ string, archive on template, Studio writes template, state via action, POS config needs closed sessions, return_picking has no location_id (Odoo 19), discount needs write-after-create.**

---

## См. также

- [00_index.md](00_index.md) — навигация, глоссарий, статусы
- [01_project.md](01_project.md) — бизнес-цели + архитектурные истины (paper≠fact, marketplace=intermediary, бонусы личные, negative stock=проблема, аналитика после миграции, quarantine no sell, rolling inventory) + roadmap + ideal state
- [02_makecom_bot.md](02_makecom_bot.md) — бот техдок + reconciliation principles
- [03_inventory_pipeline.md](03_inventory_pipeline.md) — приёмка + bill control
- [04_pos_and_roles.md](04_pos_and_roles.md) — POS техдок, букеты (полная архитектура), eWallet (полная архитектура), роли
- [05_catalog.md](05_catalog.md) — миграция каталога v2.2
- [06_infra.md](06_infra.md) — Odoo Online Custom + лимиты
- [07_state_snapshot.md](07_state_snapshot.md) — живой снимок prod
- [08_holded_archive.md](08_holded_archive.md) — бета-миграция Holded + .py исходники
- [CHANGELOG.md](CHANGELOG.md) — история изменений
