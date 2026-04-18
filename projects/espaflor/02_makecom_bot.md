<!-- v: 3 | updated: 2026-04-18T20:00Z -->
# 02. Make.com Telegram Bot

Статус: 🟢 **PROD** — работает, обрабатывает 188+ pedido.

---

## ⚠️ Platform Dependencies

**Бот зависит от 4 активных внешних коннекторов. Падение любого платного = тихий отказ без явной ошибки в Telegram.**

| # | Коннектор в Make.com | Роль | Тариф | Риск |
|---|---|---|---|---|
| 1 | **CloudConvert OAuth** | PDF cutter — разбивает multi-page PDF на страницы + конвертация в изображения для OCR | Платный (credits/month) | 🔴 Высокий — без него OCR читает только первую страницу |
| 2 | **Odoo** | XML-RPC в espafloriasl.odoo.com (19 вызовов на pedido) | Входит в Odoo.sh Custom | 🟡 Средний — 1 Worker bottleneck |
| 3 | **OpenAI** | 3 LLM-вызова (OCR + reconciliation v3.5 + diagnostics v3.1) | Платный (tokens/month) | 🔴 Высокий — закончатся токены = бот стоит |
| 4 | **Telegram Bot** | Вход сообщений + ответы | Бесплатный | 🟢 Низкий (только rate limits) |

**⚠️ Google connection в Make.com — НЕ используется** сценарием бота (только висит в списке коннекторов, можно отвязать).

### Промпты — source of truth

Production-промпты живут в **трёх** местах, которые должны обновляться согласованно:

| Место | Файл | Роль |
|---|---|---|
| **Make.com scenario (prod)** | модули 3 / 149 / 167 | То, что реально выполняется. Если правишь здесь — prod идёт новым промптом сразу. |
| **`prompts/` в этом репо** | `prompt_ocr_v1.txt`, `prompt_reconciliation_v3.5.txt`, `prompt_diagnostics_v3.1.txt` | Долгосрочный снапшот для diff между версиями. |
| **Claude Project knowledge** | `prompt_ocr_v1.txt`, `prompt_reconciliation_v3_5.txt`, `prompt_diagnostics_v3_1.txt` | Upload для self-contained reference в чате. Подчёркивания вместо точек — особенность Project upload. |

**При изменении промпта** — обновляются **все три**:
1. В Make.com UI (это применяется к prod сразу)
2. В `prompts/` репо (commit)
3. В Project knowledge (Owner перезаливает)

Если синхронизация отстала — prod работает правильно, но новые AI-чаты будут обсуждать старый промпт. Это главный риск рассинхрона.

### Правило диагностики

**При падении бота → первым делом проверить:**
1. Балансы (CloudConvert credits, OpenAI tokens, Make.com operations)
2. Статус OAuth коннекторов (Re-authorize / Verify в Make.com UI)
3. Quota Telegram (рейт лимиты)

**И только потом** лезть в код сценария.

### Re-authorization

- CloudConvert — **OAuth**, требует периодической re-авторизации
- Make.com присылает email когда connection скоро expire
- **Игнорировать эти emails = бот падёт** через несколько дней

### Мониторинг балансов (TODO)

⬜ Настроить alerts при низких балансах — email / Telegram notification. См. [09](09_open_work.md).

---

## Назначение

Telegram-бот на Make.com, который принимает от оператора фото/PDF поставщицкого документа (factura / albarán / ticket / pedido) и:

- **Route 1:** создаёт **новый** `purchase.order` в Odoo (если pedido по VAT + document_number не найден)
- **Route 2:** **обогащает существующий pedido** — приводит цены, коды, упаковки и комментарии строк в соответствие с бумагой, учит базу маппингов, пишет операторскую сводку

Ядро: **три LLM-вызова** (OCR-экстрактор, reconciliation engine, diagnostics reporter) + **19 Odoo XML-RPC вызовов**.

---

## Файлы-артефакты

- **Blueprint:** `Integration_Telegram_Bot_blueprint__22_.json` (55 модулей)
- **OCR prompt:** `prompts/prompt_ocr_v1.txt`
- **Reconciliation engine:** `prompts/prompt_reconciliation_v3.5.txt` (**prod**)
- **Diagnostics:** `prompts/prompt_diagnostics_v3.1.txt` (**prod**)
- **Line-log шаблоны:** `templates/make_line_log_unit.txt`, `templates/make_line_log_pack.txt`

---

## Архитектура сценария

### Точка входа
```
[1] telegram:WatchUpdates
  → [2] telegram:DownloadFile (fileId = 1.message.document.file_id)
  → [35] BasicIfElse (PDF vs image routing)
  → [43] BasicMerge → array-final
  → [51] telegram:SendReplyMessage (статус «распознаём…»)
```

### OCR-экстрактор (модуль 3)
- **Модель:** `gpt-5.4-mini`
- **Temperature:** 0.2, **max_tokens:** 4048
- **Входы:** массив изображений (`43.array-final`)
- **Выход:** STRICT JSON с полями `supplier_name`, `supplier_search_name`, `supplier_vat`, `document_number`, `document_date`, `document_type`, `lines[]`, `total_amount`, `tax_summary`
- **System prompt:** см. `prompts/prompt_ocr_v1.txt`

### Поиск поставщика и pedido

**Модуль 12 — Поиск поставщика (`res.partner`):**
```
domain: ["|",
  ["vat", "=", "{{if(4.supplier_vat; 4.supplier_vat; \"НЕТ_ИНН\")}}"],
  ["name", "ilike", "{{4.supplier_search_name}}"]]
fields: [id, name], limit: 1
```

**Модуль 108 — Поиск pedido (`purchase.order`):**
```
domain: [
  ["partner_id", "=", 12.body[].id],
  ["partner_ref", "=", 4.document_number],
  ["state", "!=", "cancel"]]
fields: [id, name, partner_ref, partner_id, state, amount_untaxed, amount_tax, amount_total, currency_id, date_order, order_line]
limit: 5, order: "id desc"
```

### Router 110 — три ветки

| Route | Триггер | Что делает |
|---|---|---|
| 1 | pedido НЕ найден | Создаёт новый `purchase.order` (мод. 8), прикрепляет фото (49), итерирует строки бумаги (10), ищет карточку (94), создаёт `purchase.order.line` (11), финальное сообщение. ⚠️ См. «Route 1 modernization» ниже. |
| 2 | pedido найден | Reconciliation (см. ниже). |
| 3 | Ошибка | `SendReplyMessage` с текстом. |

### Route 2 — обогащение pedido

```
[143] прикрепить фото → ir.attachment
[144] search_read все строки pedido (purchase.order.line)
       + кастомные поля: x_studio_supplier_sku, x_studio_supplier_product_name,
         x_studio_item_comment, x_studio_expected_qty, x_studio_operator_hit
[145] BasicFeeder по строкам pedido
  [146] search_read product.product по id → codigo из Holded
  [190] HTTP Make Request → внешний прайс из Holded (для обогащения)
[147] BasicAggregator → enriched_array
[148] json:CreateJSON → canonical payload для reconciliation engine
[192] Telegram (статус «сверяем…»)
[149] OpenAI → Reconciliation engine v3.5 (strict JSON output)
[150] json:ParseJSON
[165] BasicRouter → 4 ветки:
  ROUTE 1: apply price + pack + comment (learned code hit)
    [193] product.supplierinfo: search (codigo-пачки-дата)
    [227] BasicIfElse
    [230] BasicMerge
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

## LLM промпты (финальные prod-версии)

### OCR Extractor (prompt 3)
- Model: `gpt-5.4-mini`, T=0.2, max_tokens=4048
- Роль: Senior Odoo Accountant для испанских facturas/tickets/albaranes
- Выход: STRICT JSON (no markdown)

**Ключевые правила:**
- Даты → `YYYY-MM-DD`
- Числа: `"1.857,50" → 1857.50`, `"21,00 %" → 21.00`
- Очистка: убирать `&` (→ "and"), двойные кавычки, переносы
- `supplier_search_name` — без SL/SA/SLU/LLC/LTD
- `supplier_vat` — без пробелов/точек/дефисов
- `document_number` — ровно как в документе
- Строки: добавлять sub-параметры в `item_name` через запятые
- `supplier_sku` — из Ref./Artículo/Código/Entrega/Lote

Полный текст: `prompts/prompt_ocr_v1.txt`

### Reconciliation Engine v3.5 (prompt 149)
- Model: `gpt-5.4`, T=0, max_tokens=4500
- Выход: STRICT JSON

**Архитектурные принципы:**
- **Pipeline split:** LLM делает identity matching, Python делает арифметику → LLM не считает, только выбирает
- **Safety > Coverage:** "A wrong match is worse than an unmatched line"
- **5 изолированных решений на строку:** candidate / quantity / pack-vs-unit / tax / price action
- **Evidence priority (финальный порядок):**
  1. Learned vendor code (`data[k].product_code`)
  2. Operator command (`x_studio_operator_hit`)
  3. Existing plausible assignment
  4. Fabrication code (`x_studio_codigo_fabrica`)
  5. Default code
  6. Semantic similarity (tie-breaker only)
- **Learned code ПОВЫШАЕТ confidence**, не понижает (даже если name в Odoo ugly/legacy)
- **Operator hit ≈ direct command** (override semantic, broad family, line order)
- **Broad tokens** (`bouquet`, `bqt`, `mix`, `tropical`, `greenery`) — не доказывают identity

**Confidence calibration:**
- 0.92-0.98 — direct learned vendor code
- 0.88-0.95 — operator command
- 0.84-0.91 — fabrication/default code
- 0.74-0.83 — narrow-identity semantic
- 0.62-0.73 — weaker assigned card
- < 0.62 — только manual_review (не dump bucket!)

**Match method discipline:**
```
1. supplierinfo_code  (ТОЛЬКО если paper.supplier_sku == data[].product_code)
2. fabrication_code   (ТОЛЬКО если supplier_sku IN x_studio_codigo_fabrica)
3. default_code       (ТОЛЬКО если supplier_sku == default_code)
4. semantic_name
5. manual_review      (ТОЛЬКО если action = manual_review)
```

Полный текст: `prompts/prompt_reconciliation_v3.5.txt`

### Diagnostics v3.1 (prompt 167)
- Model: `gpt-5.4-mini`, T=0.2, max_tokens=1200
- Выход: plain Russian text (не JSON)

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

**RESOLVED DOCUMENT RULE:** если после апдейтов `FINAL PEDIDO AFTER UPDATES total == paper total`, `tax == paper tax`, нет `unmatched_paper_lines`, нет `unmatched_pedido_lines`, нет `manual_review` → STATUS: OK.

**Source of truth:**
- Paper → `paper_document`
- Текущие итоги pedido → **FINAL PEDIDO AFTER UPDATES** (модуль 170), НЕ pre-update

Полный текст: `prompts/prompt_diagnostics_v3.1.txt`

---

## Canonical JSON payload (модуль 148)

Что Make отправляет в OpenAI reconciliation engine:

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

### Структура `pedido_lines_enriched[j]`

- Корневые: `id, name, price_unit, product_qty, product_id, tax_ids, x_studio_operator_hit`
- `body[]` — массив product card data: `name, default_code, x_studio_codigo_fabrica, product_tmpl_id`
- `data[]` — **ТОЛЬКО learned vendor codes:** `product_code`

---

## Output JSON shape (Reconciliation engine)

```json
{
  "document_ok": false,
  "overall_confidence": 0.85,
  "can_apply_prices": false,
  "financial_summary": {
    "subtotal_match": false, "tax_match": false, "total_match": false,
    "paper_subtotal": 0.0, "pedido_subtotal": 0.0, ...
  },
  "matches": [
    {
      "paper_index": 3,
      "paper_item_name": "...",
      "supplier_sku": "197433",
      "pedido_line_id": 29367,
      "pedido_product_id": 7304,
      "pedido_display_name": "...",
      "match_method": "supplierinfo_code",
      "match_reason": "learned vendor code match",
      "confidence": 0.97,
      "quantity_match": true,
      "uom_mismatch_warning": false,
      "paper_quantity": 20,
      "pedido_quantity": 20,
      "current_price_unit": 1.24,
      "new_price_unit": 1.24,
      "price_difference": 0.0,
      "action": "no_action"
    }
  ],
  "unmatched_paper_lines": [...],
  "unmatched_pedido_lines": [...],
  "warnings": []
}
```

**action values:** `update_price` / `no_action` / `manual_review`

---

## Все Odoo XML-RPC вызовы (19 штук)

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

---

## ⚠️ Hardcoded magic numbers (нельзя терять!)

| Где | Значение | Комментарий |
|---|---|---|
| Модуль 8 | `partner_id fallback = 38` | Заглушка «unknown vendor» |
| Модуль 11 | `product_id fallback = 10` | Заглушка «НОВЫЙ ТОВАР» |
| Модуль 11 | `tax_ids 7, 8, 68, 70` | Sales tax IDs для 10%/21% × goods/services |
| Модуль 156, 193 | `uom_id = 31` | «Paquete (Усреднённый)» |
| Модуль 166 | `subtype_id = 1` | note subtype для mail.message |

**Tax mapping (критично для правок):**
- `tax_percent=10` + `item_type=service` → tax id `70`
- `tax_percent=10` + `item_type=good` → tax id `68`
- `tax_percent=21` + `item_type=service` → tax id `8`
- `tax_percent=21` + `item_type=good` → tax id `7`

---

## Line-log шаблоны (Make.com)

Эти шаблоны пишутся в `x_studio_item_comment` на строке pedido.

**Пачечная ветка (модуль 196) — `templates/make_line_log_pack.txt`:**
```
{{if(151.action = "update_price"; "📦 цена " + toString(151.current_price_unit) + "€→" + toString(151.new_price_unit) + "€. "; "📦 ✔цена ok. ")}}Пачка: {{151.pedido_quantity}} шт→{{151.paper_quantity}} пак. Código {{151.supplier_sku}}. /{{formatDate(now; "YY-MMM-DD")}}{{if((ifempty(255.existing_item_comment; "") != ""); "\n"; )}}{{replace(ifempty(255.existing_item_comment; ""); newline; "\n")}}
```

**Штучная ветка (модуль 219) — `templates/make_line_log_unit.txt`:**
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

## Known issues / workarounds

### XML-RPC экранирование
- Бэкенд Odoo падает на `&`, `"`, `\n` в текстовых полях с `ExpatError: mismatched tag`
- Решение: в OCR prompt запрет на эти символы + `escapeJsonCharacters(replace(body, newline, "&lt;br/&gt;"))` в chatter write

### Make.com type coercion опасен
- **Никогда** не передавать boolean в string-функции (`replace(false, ...)` ломается)
- Всегда защищать через `ifempty(...; "")`
- `formatNumber(...)` нестабилен → использовать `toString(...)`

### Image pipeline
- После Merge/Router массив изображений может "потеряться"
- Классическая ошибка: `BundleValidationError: Missing value of required parameter 'images'`
- Решение: явно проверять branch-by-branch, куда идёт `array-final`

### Telegram media groups
- Альбомы (несколько фото) → многократный webhook trigger → дубли pedido
- Решение: **организационное** — только PDF через нативный сканер ОС

---

## Route 1 modernization (TODO)

Route 1 (создание нового pedido) сейчас **проще** Route 2. Не использует:
- Learned vendor codes при создании строк
- Operator hits (их вообще нет при создании)
- Reconciliation engine

**Надо доработать:**
1. Проверка на дубль `(supplier_vat, document_number)` **до** модуля 8 (сейчас два одинаковых PDF создадут 2 pedido)
2. Использование learned vendor codes при поиске карточки (модуль 94)
3. Возможно вызов reconciliation engine даже для нового pedido (self-check)
4. Telegram progress bar как в Route 2

См. [09_open_work.md](09_open_work.md) — приоритет P1.

---

## Связи с другими модулями

- **Flow приёмки (stock.move):** см. [03_odoo_receipt_review.md](03_odoo_receipt_review.md) — бот пишет `x_studio_supplier_sku`, `x_studio_expected_qty`, `x_studio_item_comment`, они оттуда видны флористу
- **Migration action:** [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md) — при миграции карточки `product.supplierinfo` (learned codes, которые учит бот) копируются на новый variant
- **Infrastructure:** [07_infrastructure_devops.md](07_infrastructure_devops.md) — 1 Worker bottleneck, 19 XML-RPC вызовов на один pedido критично для пиков
