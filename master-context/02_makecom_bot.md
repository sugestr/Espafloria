<!-- v: 7 | updated: 2026-04-25T00:00Z -->
# 02. Make.com Telegram Bot

**Что в файле:** техдок Make.com бота (188+ pedido в проде). OCR + reconciliation + diagnostics. **Reconciliation principles** (бывшие 99 §6-12). Bot-specific gotchas (silent fail, Make.com string handling).

**Status:** 🟢 PROD.

---

## 1. Назначение

Telegram-бот на Make.com, который принимает от оператора фото/PDF поставщицкого документа (factura / albarán / ticket / pedido) и:
- **Route 1:** создаёт **новый** `purchase.order` в Odoo (если pedido по VAT + document_number не найден).
- **Route 2:** **обогащает существующий pedido** — приводит цены, коды, упаковки и комментарии строк в соответствие с бумагой, учит базу маппингов, пишет операторскую сводку.

**Ядро:** 3 LLM-вызова (OCR-экстрактор, reconciliation engine, diagnostics reporter) + 19 Odoo XML-RPC вызовов.

---

## 2. Reconciliation principles (бывшие 99 §6-12)

> Архитектурные принципы reconciliation — контракт между Make-сценарием и LLM-промптами. Меняются медленно, нарушать нельзя без согласованной перенастройки промпта.

### 2.1. Learned vendor code = сильный положительный сигнал
Если `paper.supplier_sku == data[].product_code` → **confidence растёт**, не падает. Даже если внутреннее имя в Odoo ugly/legacy (`[8400253] 🚫 MARFULL - rama` vs paper «Photinia Red Robin»).

### 2.2. Operator hit (`x_studio_operator_hit`) ≈ прямая команда
Уважается **выше** semantic similarity, broad family, line order. Исключение только hard species conflict (`rose ↔ tulip`, `vase ↔ flower`).

### 2.3. Wrong match хуже unmatched
Не максимизируй coverage за счёт identity safety. Broad category tokens (`bouquet`, `bqt`, `mix`, `tropical`, `greenery`) **не доказывают identity**.

### 2.4. Good identity match выживает quantity/tax/price mismatches
Расхождение количеств / налогов / цен = diagnostic, **НЕ disqualifying**. Держим match, диагностируем отдельно.

### 2.5. `manual_review` ≠ dump bucket
Используется **только** когда остаётся конкретный concrete identity risk. Если identity unsafe → идёт в `unmatched`, не в manual_review.

### 2.6. Diagnostics смотрит на FINAL state pedido после updates
`prompt_diagnostics_v3.1` опирается на **FINAL PEDIDO AFTER UPDATES** (модуль 170) + COMPARISON RESULT, не только pre-update mismatch.

### 2.7. Make.com string-handling опасен
- ❌ Никогда не передавать boolean в string-функции (`replace(false, ...)` ломается).
- ✅ Всегда защищать через `ifempty(...; "")`.
- ✅ `toString(...)` безопаснее `formatNumber(...)`.
- Простой шаблон > красивый хрупкий.

---

## 3. Platform Dependencies

**Бот зависит от 4 активных внешних коннекторов. Падение любого платного = тихий отказ без явной ошибки в Telegram.**

| # | Коннектор | Роль | Тариф | Риск |
|---|---|---|---|---|
| 1 | **CloudConvert OAuth** | PDF cutter — multi-page PDF на страницы + конвертация в изображения для OCR | Платный (credits/month) | 🔴 Высокий — без него OCR читает только первую страницу |
| 2 | **Odoo** | XML-RPC (19 вызовов на pedido) | Входит в Odoo Online Custom | 🟡 Средний — 1 Worker bottleneck |
| 3 | **OpenAI** | 3 LLM-вызова | Платный (tokens/month) | 🔴 Высокий — закончатся токены = бот стоит |
| 4 | **Telegram Bot** | Вход сообщений + ответы | Бесплатный | 🟢 Низкий (rate limits) |

**⚠️ Google connection в Make.com — НЕ используется** сценарием (только в списке коннекторов, можно отвязать).

### 3.1. Падение баланса = silent fail (правило debug)

При **любой** проблеме бота — первым делом проверять:
1. **Балансы** (CloudConvert credits, OpenAI tokens, Make.com operations).
2. **Статус OAuth коннекторов** (Re-authorize / Verify в Make.com UI).
3. **Quota Telegram** (rate limits).

И **только потом** лезть в код сценария.

### 3.2. Re-authorization

- CloudConvert — **OAuth**, требует периодической re-авторизации.
- Make.com присылает email когда connection скоро expire.
- **Игнорировать эти emails = бот падёт** через несколько дней.

### 3.3. Мониторинг балансов

🔴 Open: alerts при низких балансах (Make.com operations, OpenAI tokens, CloudConvert credits) через email / Telegram. См. [01_project § 9.3](01_project.md).

---

## 4. Промпты — source of truth

Production-промпты живут в **трёх** местах, обновляются согласованно:

| Место | Файл | Роль |
|---|---|---|
| **Make.com scenario (prod)** | модули 3 / 149 / 167 | То, что реально выполняется. Правка → prod идёт новым промптом сразу. |
| **Репо `master-context/`** | `prompt_ocr_v1.txt`, `prompt_reconciliation_v3.5.txt`, `prompt_diagnostics_v3.1.txt` | Долгосрочный снапшот для diff между версиями. |
| **Claude Project knowledge** | `prompt_ocr_v1.txt`, `prompt_reconciliation_v3_5.txt`, `prompt_diagnostics_v3_1.txt` | Upload для self-contained reference. Подчёркивания вместо точек — особенность Project upload. |

**При изменении промпта:**
1. В Make.com UI (применяется к prod сразу).
2. В репо (commit).
3. В Project knowledge (Owner перезаливает).

Если синхронизация отстала — prod работает правильно, но новые AI-чаты обсуждают старый промпт. Главный риск рассинхрона.

---

## 5. Архитектура сценария

### 5.1. Точка входа
```
[1] telegram:WatchUpdates
  → [2] telegram:DownloadFile (fileId = 1.message.document.file_id)
  → [35] BasicIfElse (PDF vs image routing)
  → [43] BasicMerge → array-final
  → [51] telegram:SendReplyMessage (статус «распознаём…»)
```

### 5.2. OCR-экстрактор (модуль 3)
- Model: `gpt-5.4-mini`, T=0.2, max_tokens=4048.
- Inputs: массив изображений (`43.array-final`).
- Output: STRICT JSON (`supplier_name`, `supplier_search_name`, `supplier_vat`, `document_number`, `document_date`, `document_type`, `lines[]`, `total_amount`, `tax_summary`).
- System prompt: см. `prompt_ocr_v1.txt`.

**Ключевые правила OCR:**
- Даты → `YYYY-MM-DD`.
- Числа: `"1.857,50" → 1857.50`, `"21,00 %" → 21.00`.
- Очистка: убирать `&` (→ "and"), двойные кавычки, переносы.
- `supplier_search_name` — без SL/SA/SLU/LLC/LTD.
- `supplier_vat` — без пробелов/точек/дефисов.
- `document_number` — ровно как в документе.
- `supplier_sku` — из Ref./Artículo/Código/Entrega/Lote.

### 5.3. Поиск поставщика и pedido

**Модуль 12 — `res.partner`:**
```
domain: ["|",
  ["vat", "=", "{{if(4.supplier_vat; 4.supplier_vat; \"НЕТ_ИНН\")}}"],
  ["name", "ilike", "{{4.supplier_search_name}}"]]
fields: [id, name], limit: 1
```

**Модуль 108 — `purchase.order`:**
```
domain: [
  ["partner_id", "=", 12.body[].id],
  ["partner_ref", "=", 4.document_number],
  ["state", "!=", "cancel"]]
fields: [id, name, partner_ref, partner_id, state, amount_untaxed, amount_tax, amount_total, currency_id, date_order, order_line]
limit: 5, order: "id desc"
```

### 5.4. Router 110 — три ветки

| Route | Триггер | Что делает |
|---|---|---|
| 1 | pedido НЕ найден | Создаёт новый `purchase.order` (мод. 8), прикрепляет фото (49), итерирует строки (10), ищет карточку (94), создаёт line (11), финальное сообщение |
| 2 | pedido найден | Reconciliation (см. § 5.5) |
| 3 | Ошибка | `SendReplyMessage` с текстом |

⚠️ **Route 1 modernization** — open work (см. § 9 ниже).

### 5.5. Route 2 — обогащение pedido

```
[143] прикрепить фото → ir.attachment
[144] search_read все строки pedido + кастомные поля
       (x_studio_supplier_sku, x_studio_supplier_product_name,
        x_studio_item_comment, x_studio_expected_qty, x_studio_operator_hit)
[145] BasicFeeder по строкам pedido
  [146] search_read product.product → codigo из Holded
  [190] HTTP Make Request → внешний прайс из Holded
[147] BasicAggregator → enriched_array
[148] json:CreateJSON → canonical payload для reconciliation engine
[192] Telegram (статус «сверяем…»)
[149] OpenAI → Reconciliation engine v3.5 (strict JSON output)
[150] json:ParseJSON
[165] BasicRouter → 4 ветки:
  ROUTE 1: apply price + pack + comment (learned code hit)
    [193] product.supplierinfo: search (codigo-пачки-дата)
    [227/230] BasicIfElse / BasicMerge
    [196] SetVariables: var comment
    [156] purchase.order.line: write (price_unit, packs, comment)
  ROUTE 2: teach new codigo
    [218] product.supplierinfo: search (codigo-дата)
    [219] SetVariables: var comment
    [234] purchase.order.line: write (+ qty if differ)
    [157] product.supplierinfo: CREATE — обучаем базу новому коду
  ROUTE 3: comment only (unmatched or degenerate)
    [233] SetVariable2
    [236] purchase.order.line: write comment
  ROUTE 4: document-level summary
    [170] purchase.order: read — свежие итоги
    [167] OpenAI → Diagnostics v3.1 → short Russian report
    [168] telegram:SendReplyMessage
    [178] SetVariable2
    [169] mail.message: CREATE — дублируем в chatter pedido
```

---

## 6. LLM промпты

### 6.1. Reconciliation Engine v3.5 (модуль 149)
- Model: `gpt-5.4`, T=0, max_tokens=4500.
- Output: STRICT JSON.

**Архитектурные принципы (контракт с Make-сценарием):**
- **Pipeline split:** LLM делает identity matching, Python делает арифметику. LLM не считает, только выбирает.
- **Safety > Coverage:** wrong match хуже unmatched (см. § 2.3).
- **5 изолированных решений на строку:** candidate / quantity / pack-vs-unit / tax / price action.
- **Evidence priority:**
  1. Learned vendor code (`data[k].product_code`).
  2. Operator command (`x_studio_operator_hit`).
  3. Existing plausible assignment.
  4. Fabrication code (`x_studio_codigo_fabrica`).
  5. Default code.
  6. Semantic similarity (tie-breaker only).

> ℹ️ Конкретные значения confidence calibration и match method handlers (`supplierinfo_code` / `fabrication_code` / `default_code` / `semantic_name` / `manual_review`) — в самом промпте. База держит только архитектурные принципы.

Полный текст: `prompt_reconciliation_v3.5.txt`.

### 6.2. Diagnostics v3.1 (модуль 167)
- Model: `gpt-5.4-mini`, T=0.2, max_tokens=1200.
- Output: plain Russian text (не JSON).

**Формат:**
```
STATUS: OK ✅ / WARNING ⚠️ / CRITICAL 🚨

Суммы
• …

Строки
• ✅/⚠️/❌ …

Риски
• 🚨 (только для критичного)
```

**RESOLVED DOCUMENT RULE:** если после updates `FINAL PEDIDO AFTER UPDATES total == paper total`, `tax == paper tax`, нет `unmatched_paper_lines`, нет `unmatched_pedido_lines`, нет `manual_review` → **STATUS: OK**.

**Source of truth:**
- Paper → `paper_document`.
- Текущие итоги pedido → **FINAL PEDIDO AFTER UPDATES** (модуль 170), НЕ pre-update (см. § 2.6).

Полный текст: `prompt_diagnostics_v3.1.txt`.

---

## 7. Canonical JSON payload (модуль 148)

```json
{
  "pedido_header": {
    "odoo_id": "{{108.body[].id}}",
    "currency": "{{108.body[].currency_id.value}}",
    "vendor_name": "{{108.body[].partner_id.value}}",
    "vendor_reference": "{{108.body[].partner_ref}}"
  },
  "pedido_totals": {
    "total_amount": "{{108.body[].amount_total}}",
    "subtotal_amount": "{{108.body[].amount_untaxed}}",
    "total_tax_amount": "{{108.body[].amount_tax}}"
  },
  "paper_document": {
    "lines": "{{4.lines}}",
    "currency": "{{4.currency}}",
    "tax_summary": {...},
    "supplier_vat": "{{4.supplier_vat}}",
    "total_amount": "{{4.total_amount}}",
    "document_date": "{{4.document_date}}",
    "supplier_name": "{{4.supplier_name}}",
    "document_number": "{{4.document_number}}",
    ...
  },
  "pedido_lines_enriched": "{{147.array}}"
}
```

**Структура `pedido_lines_enriched[j]`:**
- Корневые: `id, name, price_unit, product_qty, product_id, tax_ids, x_studio_operator_hit`.
- `body[]` — массив product card data: `name, default_code, x_studio_codigo_fabrica, product_tmpl_id`.
- `data[]` — **ТОЛЬКО learned vendor codes:** `product_code`.

**Output JSON shape (Reconciliation engine):**
```json
{
  "document_ok": false,
  "overall_confidence": 0.85,
  "can_apply_prices": false,
  "financial_summary": {...},
  "matches": [
    {
      "paper_index": 3,
      "paper_item_name": "...",
      "supplier_sku": "197433",
      "pedido_line_id": 29367,
      "pedido_product_id": 7304,
      "match_method": "supplierinfo_code",
      "confidence": 0.97,
      "quantity_match": true,
      "current_price_unit": 1.24,
      "new_price_unit": 1.24,
      "action": "no_action"
    }
  ],
  "unmatched_paper_lines": [...],
  "unmatched_pedido_lines": [...],
  "warnings": []
}
```

**`action` values:** `update_price` / `no_action` / `manual_review`.

---

## 8. Все Odoo XML-RPC вызовы (19 штук)

| ID | Название | Action | Model |
|---|---|---|---|
| 12 | Найти поставщика | search_read | res.partner |
| 108 | Найти Pedido | search_read | purchase.order |
| 8 | Создать purchase | create | purchase.order |
| 49 | Прикрепить фото (Route 1) | create | ir.attachment |
| 94 | Поиск карточки товара | search_read | product.product |
| 11 | Добавить позицию товара | create | purchase.order.line |
| 143 | Прикрепить фото (Route 2) | create | ir.attachment |
| 144 | Все товары pedido | search_read | purchase.order.line |
| 146 | codigo из Holded | search_read | product.product |
| 193 | Supplierinfo codigo-пачки-дата | search_read | product.supplierinfo |
| 156 | Update price + packs + comment | write | purchase.order.line |
| 218 | Supplierinfo codigo-дата | search_read | product.supplierinfo |
| 234 | Update price + qty + comment | write | purchase.order.line |
| 157 | **Обучить новому codigo** | create | product.supplierinfo |
| 236 | Comment (route 3) | write | purchase.order.line |
| 258 | Comment unmatched pedido | write | purchase.order.line |
| 166 | Main document message | create | mail.message |
| 170 | Перечитать итоги pedido | search_read | purchase.order |
| 169 | Diagnostics message | create | mail.message |

**Awareness:** каждый новый вызов — осознанное решение. 1 HTTP Worker × ~300ms × 19 = ~6s на pedido. При сезонных пиках любой лишний N+1 → 502. Прежде чем добавлять — проверить нельзя ли получить из уже сделанного `search_read` или объединить с существующим `write`.

---

## 9. Hardcoded magic numbers (нельзя терять)

| Где | Значение | Комментарий |
|---|---|---|
| Модуль 8 | `partner_id fallback = 38` | Заглушка «unknown vendor» |
| Модуль 11 | `product_id fallback = 10` | Заглушка «НОВЫЙ ТОВАР» |
| Модуль 11 | `tax_ids 7, 8, 68, 70` | **Purchase** tax IDs для 10%/21% × goods/services. Sales-таблица в [08_holded_archive § 3](08_holded_archive.md) |
| Модуль 156, 193 | `uom_id = 31` | «Paquete (Усреднённый)» |
| Модуль 166 | `subtype_id = 1` | note subtype для mail.message |

**Tax mapping (критично для правок):**
- `tax_percent=10` + `item_type=service` → tax id `70`.
- `tax_percent=10` + `item_type=good` → tax id `68`.
- `tax_percent=21` + `item_type=service` → tax id `8`.
- `tax_percent=21` + `item_type=good` → tax id `7`.

---

## 10. Line-log шаблоны (Make.com)

Эти шаблоны пишутся в `x_studio_item_comment` на строке pedido.

**Пачечная ветка (модуль 196) — `make_line_log_pack.txt`:**
```
{{if(151.action = "update_price"; "📦 цена " + toString(151.current_price_unit) + "€→" + toString(151.new_price_unit) + "€. "; "📦 ✔цена ok. ")}}Пачка: {{151.pedido_quantity}} шт→{{151.paper_quantity}} пак. Código {{151.supplier_sku}}. /{{formatDate(now; "YY-MMM-DD")}}{{if((ifempty(255.existing_item_comment; "") != ""); "\n"; )}}{{replace(ifempty(255.existing_item_comment; ""); newline; "\n")}}
```

**Штучная ветка (модуль 219) — `make_line_log_unit.txt`:**
```
{{if(151.quantity_match = false; "⚠️ кол-во не совпало: pedido " + toString(151.pedido_quantity) + " шт→бумага " + toString(151.paper_quantity) + " шт. "; )}}{{if(151.action = "update_price"; "цена " + toString(151.current_price_unit) + "€→" + toString(151.new_price_unit) + "€."; "✔цена ok.")}} Código {{151.supplier_sku}}. /{{formatDate(now; "YY-MMM-DD")}}{{if((ifempty(255.existing_item_comment; "") != ""); "\n"; )}}{{replace(ifempty(255.existing_item_comment; ""); newline; "\n")}}
```

**Bundle fields (контракт reconciliation output → Make templates, не ломать!):**
```
151.action              151.current_price_unit    151.new_price_unit
151.paper_quantity      151.pedido_quantity       151.quantity_match
151.supplier_sku        255.existing_item_comment
```

---

## 11. Known issues / workarounds

### 11.1. XML-RPC экранирование
Бэкенд Odoo падает на `&`, `"`, `\n` в текстовых полях с `ExpatError: mismatched tag`. Решение: в OCR prompt запрет на эти символы + `escapeJsonCharacters(replace(body, newline, "&lt;br/&gt;"))` в chatter write.

### 11.2. Image pipeline
После Merge/Router массив изображений может «потеряться» (`BundleValidationError: Missing value of required parameter 'images'`). Решение: явно проверять branch-by-branch куда идёт `array-final`.

### 11.3. Telegram media groups
Альбомы (несколько фото) → многократный webhook → дубли pedido. Решение: **организационное** — только PDF через нативный сканер ОС.

---

## 12. OLD_ SKU awareness post-migration (open)

После миграции каталога v2.2 старая карточка получает префикс `OLD_` на `default_code`/`barcode` и `active=False`, новый `default_code` без префикса живёт на target. **Риск:** albaran от 2026-03-15 с `supplier_sku=8400010` должен прилипнуть к OLD_ карточке (как было тогда), не к новой target.

**Правило:** `if pedido_date < migration_date(source) → искать archived OLD_ source`, иначе → active target.

**Где расширять:**
- **Модуль 94:** домен `search_read` добавить OR-ветку по `default_code='OLD_'+supplier_sku` с `active=False`.
- **Prompt v3.5:** явно упомянуть что archived OLD_ source — valid candidate если дата pedido до миграции.
- **Контекст:** передавать `migration_date` с target-карточки (через `create_date` записи `x_studio_legacy_source` либо explicit Studio-поле `x_studio_migrated_at`).
- **Evidence priority:** при равных matches по `supplier_sku` — дата pedido tie-breaker.

🔴 **Не реализовано.** Workaround до реализации: старые pedido с OLD_ помечать в Telegram как «требует manual review» если дата < последней миграции.

---

## 13. Route 1 modernization (open)

Route 1 (создание нового pedido) **проще** Route 2. Не использует:
- Learned vendor codes при создании строк.
- Operator hits (их нет при создании).
- Reconciliation engine.

**Надо доработать:**
1. Проверка дубля `(supplier_vat, document_number)` — расширить domain модуля 108 до входа в Router 110. Сейчас два одинаковых PDF создадут 2 pedido.
2. Использование learned vendor codes при поиске карточки (модуль 94).
3. Возможно вызов reconciliation engine даже для нового pedido (self-check).
4. Telegram progress bar как в Route 2.

🔴 Open.

---

## См. также

- [01_project.md](01_project.md) — общая картина проекта.
- [03_inventory_pipeline.md](03_inventory_pipeline.md) — receipt слой (бот пишет `x_studio_supplier_sku`, `x_studio_expected_qty`, `x_studio_item_comment` в pedido — оттуда видны флористу).
- [05_catalog.md](05_catalog.md) — миграция карточек, при миграции `product.supplierinfo` (learned codes) копируются на новый variant.
- [06_infra.md](06_infra.md) — 1 Worker bottleneck, нагрузка от 19 XML-RPC.
- [99_invariants.md](99_invariants.md) — § 4 (сверка с Odoo 19 docs / community / live), § G1-G2 (automation gotchas).
- `prompt_ocr_v1.txt`, `prompt_reconciliation_v3.5.txt`, `prompt_diagnostics_v3.1.txt` — production prompts.
- `make_line_log_pack.txt`, `make_line_log_unit.txt` — Make.com line-log шаблоны.
