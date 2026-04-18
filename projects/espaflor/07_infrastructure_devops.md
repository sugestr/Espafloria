<!-- v: 1 | updated: 2026-04-18T15:45Z -->
# 07. Infrastructure & DevOps

---

## Платформа

**Odoo.sh Custom** (PaaS, GitHub-integrated hosting)

**URL:** https://espafloriasl.odoo.com

**Тариф:** Custom
- **Нельзя вернуться на Standard** (после Studio customizations + custom fields — one-way migration)
- **Нельзя на SaaS Odoo Online** — там закрытая файловая система, не работают внешние API-интеграции

**Почему выбран Custom:**
- Нужны **внешние API-интеграции** (Make.com XML-RPC)
- Нужен **Odoo Studio** (для кастомных полей `x_studio_*`)
- Нужна возможность ставить сторонние `custom_addons` (в перспективе)
- Мульти-компанейский учёт (в будущем)

---

## Ресурсы

| Ресурс | Выделено | Применение |
|---|---|---|
| HTTP Workers | **1** | Обслуживание пользовательских запросов + API |
| Storage (БД + filestore) | **1 GB** | PostgreSQL + `ir.attachment` (фото, PDF) |
| Staging environments | **1** | Тестирование |
| Production | 1 | Боевая среда |

---

## Критические узкие места

### 🚨 1 Worker = bottleneck для сезонных пиков

**Расчётная capacity:** 1-5 concurrent users

**Сезонные пики цветочного бизнеса:**
- **14 февраля** (Валентинов день)
- **8 марта** (Женский день)
- **1 ноября** (Todos los Santos, Испания)
- **Родительский день** (La Merced, Барселона)

**Риск:**
- Make.com бот = 19 XML-RPC вызовов на один pedido
- Если в пик приходят 5-10 albaran одновременно → 502 Bad Gateway, зависания UI
- POS параллельно → таймауты продаж на кассе

**Митигация (в беклоге):**
- Перед пиковыми сезонами → апгрейд до 2-3 воркеров
- Мониторинг нагрузки Odoo.sh metrics
- Throttling Make.com при обнаружении 502

### 🚨 1 GB Storage = заполнится быстро

**Основные потребители:**

| Источник | Потребление | Темп |
|---|---|---|
| `ir.attachment` (Make.com бот прикрепляет PDF/фото к каждому pedido) | ~1-5 MB/pedido | ~20 MB/день при активной работе |
| Product images (`product.template.image_1920`) | ~100 KB / картинка × 2000 = ~200 MB | одноразово при импорте |
| Chatter messages + logs (`mail.message`) | несколько MB/месяц | постоянно |
| Сгенерированные PDF (invoices, receipts) | ~50 KB каждый | по операциям |

**Реальный пессимистический расчёт:**
- Импорт 2000 картинок: ~200 MB
- Make.com бот на 500 pedido/год (с прикреплениями): ~1-2 GB — уже выход за лимит

**Митигация:**
- Сжимать картинки перед загрузкой (Python-скрипты это делают: 1200×1200 JPEG 82 → ~50-80 KB)
- Периодическая архивация старых attachments
- Apgrade до 2-5 GB storage-пакетов на Odoo.sh

### ⚠️ One-way migration

**Нельзя вернуться** на Standard тариф после:
- Добавления `custom_addons`
- Правок через Odoo Studio
- Custom fields

Вы уже на этом пути → обратного билета нет.

---

## Установленные модули / локализации

Видно из `list_models`:

- **Spanish localization** (`l10n_es.*`)
  - Mod111, Mod115, Mod130, Mod303, Mod347, Mod349, Mod390
  - Libros Registro de IVA (VAT books)
  - `l10n_es_edi_facturae` (электронные инвойсы)
- **SII / AEAT** — см. раздел про compliance
- **Базовые:**
  - Accounting, Purchase, Inventory, Sales
  - Point of Sale
  - Studio
  - Project
  - CRM, Email, Gamification
- **Документооборот:** `documents.*`, `sign.*`
- **AI:** `ai.agent`, `ai.topic`, `ai.composer` (встроенный Odoo AI)

---

## Подключенные MCP / integrations (у Claude проекта)

| Integration | Для чего |
|---|---|
| Gmail | Email-монитоинг бухгалтерских документов (будущее) |
| Google Calendar | Расписание сотрудников (будущее) |
| Google Drive | ETL-файлы, sheets, документы |
| Miro | Планирование (возможно) |
| Make.com | Автоматизация (уже работает бот) |
| Kiwi.com | Не используется для цветочного бизнеса |

---

## Испанский compliance (будущее)

Из PDF `FLOR-gov - Odoo и испанский план счетов` (226 стр, raw research chat):

**Что делает испанская локализация Odoo:**
- ✅ План счетов PGCE PYMEs 2008 (preset)
- ✅ Alternative: PGCE Completo 2008, Entidades sin fines lucrativos
- ✅ Tax setup по стандартным ставкам (4%, 10%, 21%)
- ✅ Автогенерация отчётов: Modelo 303, 347, 349 и др.
- ⚠️ **VeriFactu** (Anti-Fraud Law) — требует отдельных модулей / доработки
- ⚠️ **SII** (Suministro Inmediato de Información AEAT) — отдельно
- ⚠️ Electronic invoicing — отдельные модули

**Локализация установлена в Espafloria**, но некоторые compliance-фичи могут потребовать доработки к дедлайнам AEAT.

📌 **TODO:** оценить, какие Modelo уже автогенерируются корректно, какие нужно донастраивать. См. [09_open_work.md](09_open_work.md).

---

## Рекомендации перед запуском MVP 20 апреля

**Обязательно:**
- [ ] Проверить Storage — сколько свободно (через Odoo.sh admin)
- [ ] Staging окружение должно работать — прогнать там тестовые pedido до prod
- [ ] Backup policy — убедиться что autobackup включен

**Желательно:**
- [ ] Monitoring: 502 / slow requests → alerts на email
- [ ] Настроить user_access_group для флористов (ограничить доступом только к своим модулям)
- [ ] Access log review — кто и когда логинился

**На случай проблем:**
- Odoo.sh → Branches → есть возможность быстрого rollback к предыдущему commit
- Staging → push → Production — стандартный release flow
- PostgreSQL dump — Odoo.sh делает регулярно, можно восстановить за 30 дней

---

## Key URLs

| Что | URL |
|---|---|
| Production Odoo | https://espafloriasl.odoo.com |
| Migration server action (id=1145) | https://espafloriasl.odoo.com/web#id=1145&model=ir.actions.server&view_type=form |
| Review status server action (id=1146) | https://espafloriasl.odoo.com/web#id=1146&model=ir.actions.server&view_type=form |
| Calculate in shop button (id=1150) | https://espafloriasl.odoo.com/web#id=1150&model=ir.actions.server&view_type=form |
| Review automation (id=1) | https://espafloriasl.odoo.com/web#id=1&model=base.automation&view_type=form |
| Карантин категория (id=207) | https://espafloriasl.odoo.com/web#id=207&model=product.category&view_type=form |
| Make.com scenario | (через Make.com UI) |

---

## См. также

- [08_current_state_snapshot.md](08_current_state_snapshot.md) — текущие метрики и состояние
- [09_open_work.md](09_open_work.md) — что ещё нужно дожать по compliance и масштабированию
