<!-- v: 1 | updated: 2026-04-25T00:00Z -->
# 06. Инфраструктура и платформа

**Что в файле:** платформа Odoo (тариф, лимиты, ограничения), установленные модули, MCP-интеграции у Claude, испанский compliance, рекомендации по нагрузке.

---

## 1. Платформа

**Odoo Online (SaaS) Custom** (НЕ Odoo.sh).

**URL:** https://espafloriasl.odoo.com

**Что значит «Online (SaaS) Custom»:**
- ✅ Studio — кастомные поля `x_studio_*` разрешены.
- ✅ Automated Actions с Python — разрешены.
- ✅ Server Actions с Python кодом — разрешены (отсюда работают наши actions 1145, 1146, 1150, 1176, 1203, 1209).
- ❌ **`custom_addons` НЕ разрешены** — нельзя положить свой модуль на сервер.
- ❌ **OCA модули в большинстве — НЕ работают** (большинство OCA содержит Python код в `custom_addons`).
- ✅ **Apps Store с фильтром «Compatible with Odoo Online»** — работают (только те, что без Python `custom_addons`, чисто Studio-XML).

### 1.1. Почему НЕ Odoo.sh

**Переход — one-way.** После установки `custom_addons` обратно на Online нельзя. См. [99 §3](99_invariants.md).

**Когда мигрировать оправдано** — только когда хотелка физически невозможна на Online:
- **Photo capture в POS UI** — единственный жёсткий драйвер сейчас (требует custom OWL widget).
- Tasks-in-POS-UI badge — мягкий драйвер (есть workaround через backend Activities).
- OCA `base_tier_validation` для multi-уровневых approvals.

**Сейчас 7/9 хотелок POS закрываются штатно на Online** (см. [POS_AUDIT_2026-04-25.md](../POS_AUDIT_2026-04-25.md)).

### 1.2. Откуда путаница

В прежних версиях knowledge base 07_infrastructure_devops.md ошибочно писал «Odoo.sh Custom». Это было неправильно. Источник правды — **Odoo Online (SaaS) Custom**. Подтверждено через факт что нельзя ставить custom_addons.

---

## 2. Ресурсы (приблизительно)

| Ресурс | Что есть | Применение |
|---|---|---|
| HTTP Workers | 1 | Обслуживание UI + API |
| Storage (БД + filestore) | ~1 GB | PostgreSQL + `ir.attachment` (фото, PDF) |
| Staging environments | 1 | Тестирование |
| Лицензии (internal users) | 3 | Используется 2 (Andriy + POS Terminal), 1 резерв под бухгалтера |

---

## 3. Узкие места

### 3.1. 1 Worker = bottleneck для сезонных пиков

**Расчётная capacity:** 1-5 concurrent users.

**Сезонные пики цветочного бизнеса:**
- 14 февраля (Валентинов день).
- 8 марта (Женский день).
- 1 ноября (Todos los Santos, Испания).
- Родительский день (La Merced, Барселона).

**Риск:**
- Make.com бот = 19 XML-RPC вызовов на один pedido.
- В пик 5-10 albaran одновременно → 502 Bad Gateway, зависания UI.
- POS параллельно → таймауты продаж на кассе.

**Митигация:** перед сезонными пиками апгрейдить до 2-3 Workers; мониторить нагрузку.

### 3.2. Storage заполнится

**Основные потребители:**

| Источник | Потребление | Темп |
|---|---|---|
| `ir.attachment` (Make.com бот прикрепляет PDF/фото к каждому pedido) | ~1-5 MB/pedido | ~20 MB/день при активной работе |
| Product images | ~100 KB / картинка × 2000 = ~200 MB | одноразово при импорте |
| Chatter messages + logs | несколько MB/месяц | постоянно |
| Сгенерированные PDF (invoices, receipts) | ~50 KB каждый | по операциям |

**Реальный пессимистический расчёт:** 200 MB images + 1-2 GB attachments/год → выход за лимит.

**Митигация:**
- Сжимать картинки перед загрузкой (1200×1200 JPEG quality 82 → ~50-80 KB) — см. [08_holded_archive.md](08_holded_archive.md).
- Периодическая архивация старых attachments.
- Apgrade до 2-5 GB storage-пакетов.

---

## 4. Установленные модули

**Ядро:**
- Spanish localization `l10n_es.*` (включая Libros Registro IVA, `l10n_es_edi_facturae`).
- Accounting, Purchase, Inventory, Sales, Point of Sale.
- Studio.
- SII / AEAT-связанные модули (входят в локализацию).

**POS-специфичные:**
- `pos_hr` — PIN-логин сотрудников в POS.
- `pos_loyalty` — интеграция с Loyalty.
- `pos_discount` — POS-side скидочный модуль.
- `loyalty` — base модуль.
- `sale_loyalty`, `website_sale_loyalty` — для будущего.

**HR:**
- `hr_attendance` — check-in/check-out через Kiosk Mode.
- `base_geolocalize` — dependency для hr_attendance.

**Дополнительно:**
- Project (для `project.task`).
- CRM, Email, Gamification.
- `documents.*`, `sign.*`.
- Встроенный Odoo AI (`ai.agent`, `ai.topic`, `ai.composer`).

> ℹ️ Точный список — через `ir.module.module` по запросу. Модули могут добавляться/удаляться между сессиями.

---

## 5. MCP-интеграции (у Claude)

| Integration | Для чего | Статус |
|---|---|---|
| **GitHub MCP** | Source of truth для базы знаний (`sugestr/Espafloria`) | 🟢 активно |
| **Odoo MCP** | XML-RPC прямые операции в prod (hot-fix полей, automations, bulk) | 🟢 активно |
| **Make.com MCP** | Управление scenario / blueprint бота | 🟡 по задаче |
| Gmail | Email-мониторинг бухгалтерских документов | 🔴 будущее |
| Google Calendar | Расписание сотрудников | 🔴 будущее |
| Google Drive | ETL-файлы, sheets, документы | 🟡 по задаче |
| Miro | Планирование / диаграммы | 🟡 опционально |

**Правило:** в начале сессии Claude через `tool_search` подгружает нужные MCP по ключевым словам, не полагаясь на статический список.

---

## 6. Испанский compliance

**Что делает локализация Odoo `l10n_es`:**
- ✅ План счетов PGCE PYMEs 2008 (preset).
- ✅ Tax setup по стандартным ставкам (4%, 10%, 21%).
- ✅ Автогенерация Modelo 303, 347, 349 и др.
- ⚠️ **VeriFactu** (Anti-Fraud Law) — требует отдельных модулей / доработки.
- ⚠️ **SII** (Suministro Inmediato AEAT) — отдельно.
- ⚠️ Electronic invoicing (Factura-E / UBL) — отдельные модули.

См. [01_project § 9.6 Бухгалтерия](01_project.md) для статуса.

---

## 7. Рекомендации перед массовыми операциями / сезонами

**Перед массовой миграцией / импортом:**
- Проверить Storage свободен (через Odoo.sh admin / billing).
- Staging окружение — прогнать тестовые pedido до prod.
- Backup verify — autobackup включен, recovery протестирован.

**Перед сезонными пиками:**
- Apgrade Workers до 2-3.
- Monitoring 502 / slow requests → alerts на email.
- Throttling Make.com при обнаружении 502.

**На случай проблем:**
- Backup ежедневный (Odoo делает регулярно), recovery за 30 дней.
- PostgreSQL dump доступен в Odoo settings.

---

## 8. Key URLs

| Что | URL |
|---|---|
| Production | https://espafloriasl.odoo.com |
| Migration UI trigger (1145) | https://espafloriasl.odoo.com/web#id=1145&model=ir.actions.server&view_type=form |
| Migration execute v2.2 (1176) | https://espafloriasl.odoo.com/web#id=1176&model=ir.actions.server&view_type=form |
| Calculate in shop button (1150) | https://espafloriasl.odoo.com/web#id=1150&model=ir.actions.server&view_type=form |
| Review automation (1146) | https://espafloriasl.odoo.com/web#id=1146&model=ir.actions.server&view_type=form |
| Bouquet on payment (1203) | https://espafloriasl.odoo.com/web#id=1203&model=ir.actions.server&view_type=form |
| Bouquet on dismantle (1209) | https://espafloriasl.odoo.com/web#id=1209&model=ir.actions.server&view_type=form |
| Карантин категория (207) | https://espafloriasl.odoo.com/web#id=207&model=product.category&view_type=form |

---

## См. также

- [01_project.md § 9.7](01_project.md) — статусы по инфраструктуре.
- [99_invariants.md § 3](99_invariants.md) — правило «не мигрировать на Odoo.sh без жёсткой нужды».
- [02_makecom_bot.md](02_makecom_bot.md) — 19 XML-RPC вызовов на pedido (нагрузка от бота).
- [POS_AUDIT_2026-04-25.md](../POS_AUDIT_2026-04-25.md) — детальный анализ что закрывается на Online vs требует Odoo.sh.
