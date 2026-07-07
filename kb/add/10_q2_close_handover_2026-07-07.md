<!-- v: 1 | updated: 2026-07-07T00:00Z -->

# Q2 2026 close — handover snapshot 2026-07-07

Handover для next session (свежая модель). Owner target: сдать Modelo 303 Q2 + 111 + 115 до 20 июля 2026 (осталось 13 дней). Правильный отчёт в налоговую > идеальная бухгалтерия.

---

## 0. Приоритет и роли

- **Источник правды по доходам** — Holded (там продолжают регистрироваться продажи POS + факт).
- **Источник правды по расходам** — банк BBVA (был не reconciliated с 1 апреля, бухгалтер бросил книги).
- **Восстановление расходов** — vendor bills в Odoo из facts перешедших через `purchases@espafloriasl.odoo.com` intake alias.
- **Reconciliation** — 19 auto rec.models по BBVA journal id=23, ручное post + Bank Matching widget.

---

## 1. Что сделано в мае-июне 2026

### 1.1. Setup (одноразовое)

- BBVA online sync через Salt Edge (IBAN ES97 0182 0721 3602 0189 4059) — journal `BBVA Account` id=23 default account 572001.
- 4-я касса «Administradora Efectivo» id=25 (CSH1), не привязанa к POS.
- 327 suppliers из Holded импортированы в `res.partner`. Fincas Finurba создан вручную (в Holded не было — CIF B61393393).
- **19 reconciliation models** (`account.reconcile.model`) — auto-recognize partner по concepto banking pattern.

### 1.2. Bulk-forward факт (2026-05-13)

- Проход 1: **35 emails** за Q2 window (2026-04-01..2026-05-12), скрипт searched по standard vendors.
- Проход 2 (после fix пропуска Glories): **+4 emails** для category B (Fincas Finurba, Odoo).
- Q1 sweep (2026-05-13): **+43 emails** issued Jan-Mar но relevant Q2 payments (annual subs, backdated services).
- Total: **82 emails forwarded**, **86 PDF attachments**.
- Log: `pedido.files/q2-forward-log.json` (полный audit trail).
- PDF-хранилище: `pedido.files/q2-forward-pdfs/` (86 файлов, идентификация NN_vendor_ref.pdf).

### 1.3. Odoo drafts result (после AI extract)

- **~89 draft in_invoice** (в основном Q2 window, часть Q1 relevant). Extract state: mostly `done`.
- **2 posted** и полностью paid:
  - `BILL/2026/04/0001` id=1864 (ANECBLAU water refacturación FAC/2026/021, 15,43€)
  - `BILL/2026/05/0001` id=1865 (Cdad. Prop. C.C. Glories май 2026/1000000198, 4 709,77€) — **paid**, matched с stmt line 1821 (2026-05-06 -4709,77€)
- **1 fixed but not posted**: id=1903 Glories апрель (2026/1000000159, 4 709,77€) — вручную установил tax_ids `[8, 137]` (`21% S` + `19% WH lease`), amount_untaxed=4617,42 + amount_tax=92,35 = amount_total=4709,77. Ждёт post → auto-match с stmt line 1677 (2026-04-08 -4709,77€).
- **2 duplicates deleted**: id=1887 (F-0425/2026 duplicate of #1866), id=1885 (ZC/F/26/126 duplicate of #1884). Gentalia в почте 24 апр и 29 апр прислала одну и ту же factura K-02 дважды.

### 1.4. Bank statement lines Q2 (BBVA journal 23)

- Total lines в Q2 window: **237** (from 2026-04-01 to end of imported feed).
- Reconciled: **3** (Glories май #1821, Rillo май #1840, ingreso 30/04 #1781).
- Orphan outflows (amount<0, not reconciled): **~40 строк с partner_id распознан rec.model'ом, но не привязан к bill**, плюс **~15 генерических без partner** (bank fees, salary bulk).

---

## 2. Аудит contabilidad (сделан 2026-07-07)

Прошёлся по всем draft invoice lines (103 lines / ~85 bills). AI extract даёт систематические ошибки. Ниже — план batch fix для next session.

### 2.1. Критические — блокируют post

| Проблема | Bills | Fix |
|---|---|---|
| Odoo subscription on `572004 Customer Account` | #1905 (81,31€ apr) + #1906 (191,66€ may) | account → `629 Otros servicios` (software) |
| Glories rentals tax = `[26]` 2% intra-community | 7 bills: #1907 (Q4 2025) + #1908..#1912 (Feb 2026) + #1913 (Mar 2026) | tax → `[8, 137]` (21% S + 19% WH lease); Glories является национальным landlord, IVA + retención IRPF |
| Fincas Finurba «Cod» без partner | #1893 (May 2044€) + #1904 (Apr 2044€) | partner → Fincas Finurba SL, tax → `[8, 137]`, account → `621` |
| Glovo 6 bills с partner=Espafloria (наша компания) | #1897, #1898, #1899, #1878, #1879, #1880 (+ #1870, #1871 Q1) | создать/найти `Glovoapp Spain Platform SL` (CIF ESB66362906), reassign, tax → `[8]`, account → `629` |
| Movistar/Telefónica без partner | #1873, #1874, #1901, #1902, #1881 (+ #1926, #1927, #1929, #1930, #1932, #1933, #1934) | по CIF в PDF: Telefónica España SA (fija 108€), Telefónica Móviles (37,50€), Xfera Móviles SAU (Masmóvil #62 уже есть) |
| Iván Balbastre 3 bills без partner | #1891 (apr 234,74€), #1940 (Q1), #1942, #1944 | создать `Iván Balbastre Riba` autónomo (NIF 46725879E), account → `624 Transportes`, decision про retención см. § 2.4 |

### 2.2. Массовые — не блокеры, но нужны для правильного Modelo 303

| Проблема | Кол-во lines | Fix |
|---|---|---|
| Tax `[7]` 21% G (goods) на услугах | ~40 lines | `[7]` → `[8]` 21% S для всех: Movistar/Telefónica/Xfera/Prosegur/Iván/El Rengle/Odoo/Lunaweb/Glovo commissions |
| Tax `[15]` 10% EX S (import) на испанских supplier'ах | ~10 lines | `[15]` → `[68]` 10% G (national goods) для Verdnatura big lines / Serviflor summary / Reigmat / Cabify — Verdnatura+Serviflor+Reigmat часть на 10% (растения), часть на 21% (accessories) — при необходимости split |
| Tax `[26]` 2% EU G непонятного назначения | ~9 lines (Glories + 2 Fincas) | заменить на правильный per-vendor |
| Account `600 Merchandise` на не-товарных vendors | ~25 lines | по classifier: Movistar/Telefónica/Xfera/Odoo/Holded/Prosegur/Lunaweb → 629; Iván/Cabify → 624; El Rengle → 623; Glories/Anec Blau/Fincas → 621; refact ANECBLAU water → 628; Rillo/IKEA → 602 |

### 2.3. Правильные (не трогать)

- Verdnatura/Serviflor/Mercat de Flor/Reigmat главные lines на `600 Mercaderías` — товар для перепродажи, correct.
- LE RETAIL ANEC BLAU (Gentalia) rentals на `621 Leases` с `[8]` — correct (SLU, retención не нужна).
- Cdad. Prop. C.C. Glories rentals на `621 Leases` — account correct, но tax поправить (см. 2.1).

### 2.4. Vendor-specific решения (утверждены owner'ом 2026-07-07)

- **El Rengle Consultors SLU** — retención НЕ нужна. Юр.лицо, PDF показал empty I.R.P.F. field. Tax = `[8]` 21% S, account = `623`.
- **Iván Balbastre Riba** — autónomo (NIF 46725879E, physical person). В PDF retención не выставлена. В банке платили full amount (без удержания). **Owner verdict 2026-07-07: вариант A — PDF-truth от vendor'а**. Что vendor выставил в своей factura — то и учитываем. Iván не показал retención → мы не удерживаем. Tax = `[8]` 21% S, account = `624 Transportes`. Юридический риск (по закону Espafloria обязана удерживать 15% independent of vendor's invoice, Modelo 111 gap) — между Iván'ом и его asesor. Наша позиция для Q2: paper-truth. **Общий принцип для всех autónomos**: сверяемся с PDF vendor'а, если retención не выставлена — не удерживаем.
- **Glovoapp** — двойные отношения (delivery + marketplace). Account = `629 Otros servicios`, без split. Split только если owner потом захочет отдельный P&L view.

---

## 3. Что делать в next session

Порядок операций:

### Приоритет 1 — batch fix contabilidad (через MCP, ~30 мин)

1. Fix Odoo subscription accounts (#1905, #1906) → `629`.
2. Fix 7 Glories draft bills → tax `[8, 137]`, retención pattern.
3. Fix 2 Fincas Finurba draft bills → partner + tax `[8, 137]` + account `621`.
4. Create/find Glovoapp Spain Platform SL partner (CIF ESB66362906), reassign 6+ Glovo drafts, tax `[8]`, account `629`.
5. Assign partners to Movistar/Telefónica/Iván/Mercat/Reigmat/Cabify draft bills (по PDF CIF).
6. Batch update `[7]` → `[8]` для всех service lines (~40 bills). Bulk через `mcp__odoo__update_records`.
7. Batch fix `[15]` → `[68]` для испанских supplier'ов с split при необходимости.
8. Batch fix accounts (`600` → `629/624/623/621/628/602`) по vendor category.

Инструмент: `mcp__odoo__update_record` / `update_records`. Все fixes перед post, чтобы reset_to_draft не понадобился.

### Приоритет 2 — post bills + Bank Matching pass (~1 час)

1. Post каждый fixed draft bill (`action_post` через MCP не доступен → user делает Confirm вручную через UI batch view, ~30 мин).
2. Прогонка Bank Matching widget: `Accounting → BBVA Account → Bank Matching` фильтр Not Reconciled.
3. После post partner-recognized rec.models должны автоматически match'ить 60-70% orphan статus lines по partner+amount.
4. Остальные — вручную клик Reconcile N.

### Приоритет 3 — sales side reconciliation (**новое требование** owner 2026-07-07)

Обнаружено что **Holded НЕ сматчивает POS TPV с реальными поступлениями BBVA** — есть риск что не все продажи Q2 корректно зарегистрированы в Holded.

Правило от owner (2026-07-07):
> «Если мы не знаем ТОЧНО что именно продали, но знаем сумму и понимаем что это цветы — списываем как "неизвестный цветок". Инвентаризацией исправим складские остатки в момент запуска Odoo как основной системы учёта.»

Метод:
1. Pull BBVA `LIQUIDACION REMESA DE COMERCIOS` (concepto=«LIQUIDACION REMESA DE COMERCIOS», N=958 lines Q2 sum ≈ +210 187€) — это acquirer settlements по TPV.
2. Pull Holded salesreceipts Q2 с разбивкой по shop (Gloria TPV / Anek Blau TPV / Plaza Molina TPV — Holded desc labels).
3. Compare acquirer settlements totals vs Holded TPV totals за Q2.
4. Если Holded totals < acquirer totals → **delta = неучтённые продажи**. Создать в Holded один salesreceipt per shop per месяц на сумму дельты, description = `«Cesta desconocida — inventario a regularizar»`, IVA 10% (растения по Spain reduced rate).
5. Отметить эти recovery-tickets tag'ом `inventory-fixup` для последующей регуляризации при запуске Odoo POS.

**Гейтинг**: Holded salesreceipts pull ограничен 500 per page, Q2 covers ~5 месяцев × ~200-400 tickets/day = **~30-60k tickets**. Нужна пагинация с датным фильтром на клиенте (Holded не поддерживает server-side date filter).

Sub-agent job: paginated pull `list_documents(salesreceipt, page=1..12)`, отфильтровать date>=2026-04-01, aggregate by month × shop, отчитаться totals.

### Приоритет 4 — draft Modelo 303/111/115 (~2 часа)

- **Modelo 303**: `Accounting → Reporting → Tax Report → Q2 2026`. Проверить cassilas: IVA repercutido base+cuota, IVA soportado base+cuota, saldo. Compare с Holded's IVA collected.
- **Modelo 111**: retenciones IRPF профессионалы за Q2 (если Iván идёт с retención — decision B; если без — Modelo 111 empty).
- **Modelo 115**: retenciones alquileres — Glories 3 месяца (Q2 apr+may+jun) + Anec Blau 3 (Gentalia F-04xx) + Fincas 3 месяца × 19% base. Total ≈ (Glories 4617,42 × 3 + Anec Blau 3499 × 3 + Fincas base × 3) × 0,19.
- Draft отчёты, sanity check суммы, отправить owner для одобрения перед tramite онлайн.

### Приоритет 5 — cleanup

- Zombie draft bills с amount=0 и partner=false (bulk delete через `mcp__odoo__delete_records`, model=account.move, filter state=draft AND amount_total=0).
- Draft bills с подозрительными round numbers (10€ x2, 45€ x2, 200€ x4 apr+may) — user, скорее всего, создал вручную для tests; надо разобрать (delete или дописать).

---

## 4. Открытые вопросы для owner (до продолжения)

1. ~~Iván retención A/B/C~~ — **решено: A (PDF-truth)** 2026-07-07.
2. **Holded pagination — pull all 12 pages salesreceipts?** — да, для sales reconciliation обязательно.
3. **Modelo 111 filing** — если пустой (нет retención Ivan/prof), нужно ли всё равно submit пустую? — asesor обычно да, спросить.
4. **BBVA sync**: state=connected, expiring=2026-11-08, но statement lines feed остановился на 2026-05-18. Нужен ручной Fetch Transactions из UI (`Dashboard → BBVA → кнопка Synchronize`) или CAMT.053 upload за 15.05-30.06. Без этого нельзя закрыть Q2 (июнь пустой в системе).

---

## 5. Feedback rules зафиксированные в этой сессии

Записаны в `memory/` (не в CLAUDE.md, потому что это workflow-level guidance, не hard invariants):

- **Paper-truth for vendor bills**: не создавать синтетические bills MCP'ом даже если BBVA outflow известен по vendor+amount. Всегда искать оригинальный PDF в почте и forward'ить на purchases@ — AI extract даёт audit trail с PDF в chatter.
- **Robot voice in forwards**: automated forwards из espafloria@ на purchases@ должны читаться как system-generated, не как first-person owner. Signature `[Espafloria Odoo intake bot]` в начале body.
- **PDF-truth from vendor invoices** (2026-07-07): что vendor указал в своей factura (IVA rate, retención, base/tax split) — то и учитываем в bill. Не «доначисляем» retención за vendor'а, даже если по закону он должен был её выставить. Наша ответственность — совпасть с бумагой vendor'а. Юридические расхождения (autónomo без retención) — между vendor'ом и его asesor.

---

## 6. Ключевые файлы этой сессии

| Файл | Что |
|---|---|
| `pedido.files/q2-forward-log.json` | Полный лог 82 forward'ов (idx 1-82) с source messageId → sent_id → PDF filename |
| `pedido.files/q2-forward-pdfs/*.pdf` | 86 PDF файлов (11 из них — companion service-detail для Iván и Verdnatura A12621592 split) |
| `pedido.files/holded-export/concepto_vendor_mapping_2026-05-12.md` | Top-30 BBVA concepto → Holded partner map (использовать для vendor lookup при batch fix) |
| `pedido.files/bank-statements/concepto_analysis_2026-05-12.md` | 1820 line BBVA statement analysis с топ-30 |
| `kb/add/10_q2_close_handover_2026-07-07.md` | этот файл — точка входа для next session |

---

## 7. Nomenclatura Odoo IDs (быстрый lookup)

Taxes (verified):
- `[7]` = `21% G` (goods 21%)
- `[8]` = `21% S` (services 21%)
- `[68]` = `10% G` (goods 10%, plants)
- `[15]` = `10% EX S` (import services 10%) — **не должно быть** на nacional
- `[26]` = `2% EU G` (intra-community 2%) — **не должно быть** на nacional
- `[134]` = `19% WHI` (income tax retención general)
- `[137]` = `19% WH lease` (retención аренд)
- `[154]` = `15% WHI` (income tax retención autónomos прof.)

Accounts (verified from GL):
- `418` = `621000 Leases and royalties` (аренды)
- `401` = `600000 Merchandise purchased` (товар)
- `697` = `572004 Customer Account` — **банковский счёт, НЕ expense** (AI put Odoo subs here — bug)
- `629` = «Otros servicios» (comunicaciones/software/marketplace)
- `624` = «Transportes»
- `623` = «Servicios profesionales independientes»
- `628` = «Suministros» (свет/вода)
- `602` = «Otros aprovisionamientos»

Partners:
- id=1: Espafloria (наша компания — не должна быть на bill'ах)
- id=39: Serviflor Vilassar SL
- id=42/67: Verdnatura Levante SL (два id — дубликат из Holded, консолидировать при cleanup)
- id=43: Rillo Suministros
- id=59: Entidad de Gestión CC Anecblau (water refact)
- id=60: Cdad. Prop. C.C. Glories (Unibail-Rodamco)
- id=61: LE RETAIL ANEC BLAU SL (Gentalia rentals)
- id=62: Xfera Móviles SAU (Masmóvil)
- id=68: El Rengle Consultors SLU
- id=72: Movistar Prosegur Alarmas SLU
- id=75: Odoo ERP SP SL
- id=76: Lunaweb GmbH (Germany, intra-EU)

Journals:
- `15` = POS Tarjeta clearing (default 572001) — не путать с 23
- `23` = BBVA Account (main current account) — default 572001
- `25` = Administradora Efectivo (cash, CSH1)

Reconciliation models: 19 штук, все на `account.reconcile.model` с `type='writeoff'` или `'invoice_matching'`. Применяются к BBVA journal 23.

---

## 8. Modelo 303 / 111 / 115 deadline reminder

**20 июля 2026** — крайний срок подачи. Sanciones за просрочку: 5% первый месяц + 5% каждый последующий (max 15% первые 6 мес). Domiciliación возможна если поданный до 15 июля.
