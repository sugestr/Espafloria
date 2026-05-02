<!-- v: 9 | updated: 2026-05-02T23:30Z -->
# Espafloria — Knowledge Base

База знаний проекта автоматизации **Espafloria SL** (Barcelona, Spain) на Odoo Online (SaaS) Custom + Make.com.

**Repo:** `sugestr/Espafloria` · **Ветка:** `main` · **Owner:** Andriy
**Prod:** https://espafloriasl.odoo.com

---

## 🎯 Цель

**Умная сеть цветочных магазинов** — база и роботы делают основную работу по контролю сотрудников и структурной целостности бизнеса. Vision и принципы — в [`01_project.md`](01_project.md).

---

## 📚 Структура

```
kb/
├── 00_index.md                      ← навигация + глоссарий + статусы
├── 01_project.md                    ← бизнес + архитектура + roadmap + wishlist
├── 02_makecom_bot.md                ← Make.com Telegram bot (OCR + reconciliation)
├── 03_inventory_pipeline.md         ← приёмка (stock layer, review_status, bill control)
├── 04_pos_and_roles.md              ← POS + букеты + eWallet + роли + CRM
├── 05_catalog.md                    ← каталог + миграция toolkit v2.2
├── 06_infra.md                      ← Odoo Online Custom + лимиты + установленные модули
├── 07_state_snapshot.md             ← живой снимок prod
├── 08_holded_archive.md             ← Holded migration archive + .py исходники
├── 09_pedido.md                     ← purchase orders + reconciliation
├── 99_invariants.md                 ← железные правила + Odoo 19 gotchas
├── README.md                        ← этот файл
├── CHANGELOG.md                     ← rolling лог сессий
│
├── add/                             ← все служебные артефакты с префиксом блока
│   ├── 00_INSTR_kb_cleanup_pass.md
│   ├── 02_prompt_*.txt              ← Make.com bot OpenAI промпты
│   ├── 02_make_line_log_*.txt       ← Make.com line-log шаблоны
│   ├── 03_calculate_in_shop_action.py
│   ├── 03_review_status_automation.py
│   ├── 04_pos_audit_2026-04-25.md
│   ├── 04_bouquet_*_action.py       ← POS bouquet actions
│   ├── 05_migrate_variant_*.py      ← catalog migration toolkit
│   ├── 07_INSTR_wipe_test_transactions.md
│   ├── 08_fetch_holded_images_55.py
│   └── 09_reception_*               ← pedido reconciliation family (algorithm + v1 baseline + action_1217 + audits + handover + INSTRs)
│
└── memory/                           ← auto-memory Claude (не трогать руками)
```

---

## 📋 Workflow

1. **Старт сессии** → читать [`99_invariants.md`](99_invariants.md) (5 правил + 11 Odoo 19 gotchas).
2. **Большая картина** → [`01_project.md`](01_project.md).
3. **Работа по теме** → тематическая глава (02-09).
4. **Артефакты по теме** → `add/NN_*` (префикс блока в имени).
5. **После любого изменения** → запись в [`CHANGELOG.md`](CHANGELOG.md).
6. **git commit/push** — через Desktop Commander (Cowork) либо локальный терминал.

---

## 📝 Версионирование .md

Каждый `.md` начинается с `<!-- v: N | updated: YYYY-MM-DDTHH:MMZ -->`. При значимой правке — bump `v`, запись в CHANGELOG.

---

## 🔗 Внешние ссылки

- **Odoo prod:** https://espafloriasl.odoo.com
- **Make.com сценарий:** «Integration Telegram Bot» (55 модулей, через Make MCP)
- **Google Sheets (ETL products):** [link](https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE)
- **Google Sheets (ETL albaran):** [link](https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58)
- **Paper PDF / data** (level above KB): `../pedido.files/reception_paper/`, `../pedido.files/verdnatura/`

---

## 🔒 Приватность

Приватный репозиторий. Не добавлять в файлы: реальные API keys / tokens / passwords, персональные данные клиентов, полные дампы БД.
