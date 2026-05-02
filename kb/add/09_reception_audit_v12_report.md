<!-- v: 1 | updated: 2026-04-30T22:30Z -->
# Audit report — reception_algorithm.md v12

## 1. Summary

Документ работоспособен как краткий operational guide, но **потерял ядро identity-policy от Make.com baseline (v3.5)** и **противоречит ground-truth правилам из HANDOVER §2.4 и §5.7 в двух местах одновременно** — там где речь о доверии бухгалтеру vs. paper. Также §H runtime checklist прямо указывает читать MEMORY.md (нарушение self-containment), а §F2 предписывает direct state-write на stock.picking (ломает 99_invariants G8).

Найдено: **5 BLOCKER**, **11 MAJOR**, **9 MINOR**, **6 NIT**.

Самый срочный фикс — §B2 матрица решений по qty (row 3 + row 5): сейчас бот будет переписывать paper qty поверх florist recount при положительной дельте >tolerance, и эскалировать любую ×2 ratio в red. Оба поведения противоречат HANDOVER. До следующего pilot — править строкой.

---

## 2. Findings (severity-ranked)

### 2.1 🔴 BLOCKER

| # | Location | Issue | Evidence | Fix |
|---|---|---|---|---|
| B1 | reception_algorithm.md §H:533 | §H Runtime Checklist предписывает agent'у `Прочитал master-context/memory/MEMORY.md — feedback rules` перед стартом каждого pedido. Нарушает D9 self-containment (audit prompt: «Если §H Runtime checklist или любая секция инструктирует subagent прочитать другой markdown файл — flag 🔴 BLOCKER»). | reception_algorithm.md:533 — `[ ] Прочитал \`master-context/memory/MEMORY.md\` — feedback rules` | Удалить строку `[ ] Прочитал master-context/memory/MEMORY.md`. Контент memory/feedback_*.md, релевантный приёмке, должен быть инлайнен (не входит в scope этого отчёта — только пометить как gap). |
| B2 | reception_algorithm.md §B2:323 | Row 3 матрицы qty: `Odoo > paper > tolerance (stem)` → `paper-truth override + activity` (🟠 orange). Противоречит HANDOVER §2.4: положительная дельта (M=Odoo > N=paper) = «щедрость поставщика → auto-OK accept Holded recount» с reasonable explanation. v12 пишет paper qty поверх — это **противоположное** действие. Owner verbatim в HANDOVER:42: *«соглашаться с ошибкой верить записям по кол-ву в holded = наверное прислали больше»*. | reception_algorithm.md:323 — `\| Odoo > paper > tolerance (stem) \| **paper-truth override** + activity \| 🟠 orange (2) — подозрительно для штучного \|`<br/>SESSION_HANDOVER_2026-04-29.md:42 — verbatim quote | Заменить action на `accept Odoo qty + activity 🟠 для review`. Не overwrite. Пометить `review_status='OK (accept Holded +N)'` (так уже сделано на 7 закрытых сессией 2026-04-29 — CHANGELOG:18). |
| B3 | reception_algorithm.md §F2:498-501 | Предписывает agent'у: `update_record('stock.picking', backorder_id, {'state': 'cancel'})` — direct state write. Нарушает 99_invariants.md G8 (state machines через штатный action) и feedback_odoo_state_machines.md. CHANGELOG 2026-04-25 (POS migration commit) явно фиксирует этот же урок. | reception_algorithm.md:499 — `agent вручную cancels backorder через update_record('stock.picking', backorder_id, {'state': 'cancel'})`<br/>99_invariants.md:78-79 G8 — «Прямая запись в state ломает computed-поля»<br/>memory/feedback_odoo_state_machines.md (referenced by MEMORY.md) | Заменить на: `НЕ trogai backorder из subagent — оставить supervisor manual или подождать action 1217 v7.8 (см. §F2 planned)`. Если нужно срочно — `picking.action_cancel()` через server action, не write. |
| B4 | reception_algorithm.md §B2:325 | Row 5 матрицы qty: `ratio ≈ ×2 (любая сторона)` → `flag suspect double-scan` 🔴 red (1). HANDOVER §5.7 явно ставит ×2 как **наблюдательную гипотезу** (5/7 случаев, owner: *«если будет четвёртый ×2-кейс в новой сессии — спросить owner'а: 5+/8 dual-count — паттерн или совпадение?»*) — то есть собирать данные, спрашивать. v12 без обсуждения с owner повышает до definitive blocker (red blocks Validate). | reception_algorithm.md:325 — `\| ratio ≈ ×2 (любая сторона) \| flag suspect double-scan \| 🔴 red (1) \|`<br/>SESSION_HANDOVER_2026-04-29.md:226-237 — таблица 7 закрытых через accept-Holded + verbatim quote owner о hypothesis | Понизить до 🟡 yellow (gate всё равно остановит) или 🟠 orange + activity «×2 наблюдение, owner: pattern или coincidence?». Decisive blocking без owner-разрешения противоречит самой концепции «owner approval gate» из HANDOVER §2.4. |
| B5 | reception_algorithm.md §3 Step 6:110 vs строки 111-117 | «Для каждой строки **5 решений**» но перечислено 6 пунктов: 1.Card, 2.Quantity, 3.Pack vs stem, 4.Tax, 5.Price, 6.Name. Subagent **обязательно** запутается на чём из шести «не делать». Это инструкция, а не fluffy текст — критично для correctness. | reception_algorithm.md:110 — `Для каждой строки 5 решений (см. §B):`<br/>reception_algorithm.md:111-117 — нумерованный список 1-6 | Поправить на «6 решений (см. §B)». Альтернатива: объединить «Pack vs stem» в «Quantity» (но §B2 vs §B3 разделены — лучше править число). |

### 2.2 🟠 MAJOR

| # | Location | Issue | Evidence | Fix |
|---|---|---|---|---|
| M1 | reception_algorithm.md §A2:201-206 (vs prompt_reconciliation_v3.5.txt:422-444) | Match-method discipline потерян. v3.5 фиксирует precedence supplierinfo_code > fabrication_code > default_code > semantic_name + правило «never default to semantic_name if direct code hit exists». v12 даёт хирархию evidence в §A2, но НЕ говорит: «match_method label должен отражать сильнейшее actual evidence; never label semantic если есть code hit». На bulk это разрушает аналитику матчинга. | reception_algorithm.md:201-206 — список 1-6<br/>prompt_reconciliation_v3.5.txt:422-444 — детальное правило | Инлайнить блок «MATCH METHOD DISCIPLINE» из v3.5:422-444 (≈20 строк) в §A2. |
| M2 | reception_algorithm.md (отсутствует) vs prompt_reconciliation_v3.5.txt:159-182 | **Identity flexibility** rule (v3.5:159-182) не инлайнен. Без этого правила subagent отклонит валидные матчи типа `freesia soleil ↔ freesia rosario`, `rose Mondial ↔ rose Pretty Pillow`, `bamboo spiral ↔ bamboo tiger`. v12 §3 Step 5:107 даёт narrow gate но не показывает что внутри narrow allowed varietal/cultivar/color/producer differences. | prompt_reconciliation_v3.5.txt:159-182 — раздел IDENTITY FLEXIBILITY с примерами | Инлайнить раздел в §A2 как §A2.1 IDENTITY FLEXIBILITY. |
| M3 | reception_algorithm.md (отсутствует) vs prompt_reconciliation_v3.5.txt:36 | Принцип «A wrong match is worse than an unmatched line» из v3.5:36 потерян. v12 §0 hard rules имеет 5 правил, но safety-first identity не один из них. Это ядро политики Make.com bot, охранявшее от агрессивного matching. | prompt_reconciliation_v3.5.txt:36 — `A wrong match is worse than an unmatched line` (буквально) | Добавить как hard rule #6 в §0:19. Альтернативно — в §A2 (но §0 виднее). |
| M4 | reception_algorithm.md (отсутствует) vs prompt_reconciliation_v3.5.txt:113-130 | Список broad tokens-not-identity (bouquet/bqt/mix/tropical/assorted/decorative/floral/greenery) потерян. v12 §B1a имеет MIX-card preferred (silent green) — это работающее улучшение, **но без явного запрета** «два line с MIX в имени != identity match» subagent пойдёт в обратную сторону: дробить MIX-карты или матчить flores↔greenery по слову `floral`. | prompt_reconciliation_v3.5.txt:113-130 | Инлайнить блок в §A2 как «Broad tokens — НЕ identity» (≈10 строк). |
| M5 | reception_algorithm.md (отсутствует) vs prompt_reconciliation_v3.5.txt:446-470 | Confidence calibration bands потеряны полностью. v3.5 даёт 5 bands (0.92-0.98 learned code, 0.88-0.95 operator hit, 0.84-0.91 fabrication/default, 0.74-0.83 clean specific, 0.62-0.73 weaker, <0.62 unmatched). v12 не пишет confidence ни в один artifact, и §B1 «match.confidence ≥ HIGH» — magic threshold без определения. | reception_algorithm.md:253 — `if match.confidence ≥ HIGH` без определения HIGH<br/>prompt_reconciliation_v3.5.txt:446-470 | Либо явно зафиксировать HIGH = 0.84+ (per v3.5 bands) и опустить confidence в lower-tier; либо инлайнить весь блок CONFIDENCE CALIBRATION. |
| M6 | reception_algorithm.md §D1:431-437 vs reconcile_finalize_action.py:48-51 | Production drift на ROLLBACK. v12 §D1 говорит «clear Phase A на лайнах» абстрактно. Код v7.7:49 чистит 4 поля: `price_unit=0, x_studio_supplier_sku=False, x_studio_supplier_product_name=False, x_studio_item_comment=False`. HANDOVER §3.1:83 говорит чистить 6 (включая `x_studio_expected_qty` и `name`). Реально код **не чистит** `x_studio_expected_qty` — после ROLLBACK сохранённое старое значение пойдёт в Phase A2 след. reconcile. v12 ничего не фиксирует. | reception_algorithm.md:431-437 — таблица branches без enumeration полей<br/>reconcile_finalize_action.py:49 — `line.with_context(...).write({'price_unit': 0, 'x_studio_supplier_sku': False, 'x_studio_supplier_product_name': False, 'x_studio_item_comment': False})`<br/>SESSION_HANDOVER_2026-04-29.md:83 | Перечислить в §D1 поля которые ROLLBACK ожидает увидеть очищенными. Параллельно — открыть тикет на код v7.8: добавить `x_studio_expected_qty: False` в clear-set (или зафиксировать в §D1 что expected_qty НЕ чистится — намеренно). |
| M7 | reception_algorithm.md §D2:438-446 vs reconcile_finalize_action.py:118-129 | Phase A2 fallback не описан. v12 пишет `quantity = expected_qty (stems)` для pack lines. Код v7.7:122 — `stems = line.x_studio_expected_qty or paq_count`. Если `expected_qty` пустой → fallback на `paq_count` (= число пачек, **не** стеблей!). Это потенциальный pack-as-stem bug на любом pedido где Phase A не дошла до expected_qty. v12 умалчивает. | reception_algorithm.md:441 — `Pack lines (uom_id=31): quantity = expected_qty (stems), x_studio_received_packs = product_qty (paq).`<br/>reconcile_finalize_action.py:122 — `stems = line.x_studio_expected_qty or paq_count` | Либо: (a) дополнить §D2 «если `expected_qty` пуст, код fallback'ит на `paq_count` — это БАГ, agent ОБЯЗАН залить expected_qty до trigger 1217»; (b) поднять до §3 Step 8 pre-flight: «все pack lines должны иметь `expected_qty > 0`». |
| M8 | reception_algorithm.md §D1:432 (RETRY description) vs reconcile_finalize_action.py:54-55 | RETRY branch описан как `state='purchase' AND есть picking в \`assigned\``. Код:55 фильтрует `picking.state not in ('done', 'cancel')` — то есть включая `draft`, `waiting`, `confirmed`, `assigned`. Описание уже кода — subagent не предскажет когда RETRY сработает. | reception_algorithm.md:432 — `state='purchase' AND есть picking в 'assigned'`<br/>reconcile_finalize_action.py:55 — `pending = pedido.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))` | Заменить «picking в `assigned`» на «picking не в `done`/`cancel`». |
| M9 | reception_algorithm.md §B2:316-317 | Tolerance formula `is_pack: tolerance = max(15, int(paper.qty * 0.30))` — для крошечных pack qty (paper=3 packs) tolerance=15 = 500% от paper. Decision matrix принимает Odoo от 0 до 18 packs как auto-OK без owner. Edge case на бизнес-критическом штучном товаре (Phaleopsis, Hortensia). | reception_algorithm.md:312-316 | Дополнить условие cap: `tolerance = min(max(15, int(paper.qty * 0.30)), paper.qty)` или явный override per продукт. |
| M10 | reception_algorithm.md §2:64 (Next free SKU = 84001172) | Hardcoded constant. После N pedido с new card 84001172 уже занят → коллизии при следующем sub-batch. Нет механизма обновления. CHANGELOG 2026-04-30:10 уже сдвигал 84009001→84001171 — то есть рекурсивная переименовка нумерации происходит руками. | reception_algorithm.md:64 — `\| Next free SKU (как только потребуется create) \| **84001172** \|`<br/>CHANGELOG.md:10 — pilot 12187009 уже использовал 84001171 | Заменить hardcode на формулу: `next_sku = max(default_code where default_code regex '^84001\\d{3}$') + 1`. Можно записать в §A5 (Card create) как обязательный шаг. |
| M11 | reception_algorithm.md (отсутствует) vs SESSION_HANDOVER_2026-04-29.md §5.6 | Bookkeeper patterns 12421571 потеряны 2/4. HANDOVER §5.6 описывает 4 паттерна нелинейных ошибок ввода: (А) сплит-объединение (paper N → Odoo M через MIX), (Б) merge multiple paper rows in 1 Odoo line с дропом одного из 4, (В) missing pair Verdnatura↔Odoo, (Г) wrong-product substitution по случайному совпадению qty/name. v12 §G покрывает только (А)≈"Multi-IVA на MIX" и (В)≈"Missing line". Merge-with-drop и substitute — нет. | reception_algorithm.md:514-524 — таблица §G<br/>SESSION_HANDOVER_2026-04-29.md:211-222 — детальный анализ 12421571 | Добавить 2 строки в §G: «Merge с дропом одной из N paper строк (12421571 CLAVEL example)» и «Wrong-product substitution по совпадению qty» с конкретным detection rule. |

### 2.3 🟡 MINOR

| # | Location | Issue | Evidence | Fix |
|---|---|---|---|---|
| m1 | reception_algorithm.md §1.2:42 | `Все stock.move.x_studio_review_color ∈ {2 orange, 3 yellow, 8 dark-blue, 10 green}; не 1 red, не 4 blue-legacy`. Color=0 (default) не упомянут — но §D3:455 говорит fallback по qty delta. Subagent может думать что 0 невалидный. | reception_algorithm.md:42 vs reception_algorithm.md:455 | Добавить «или 0 (если qty delta within MINOR)». |
| m2 | reception_algorithm.md §F1:494-496 | `~~product_uom_id~~ → uom_id` помечено strikethrough. Сам v12 уже использует `uom_id` (Step 6:127, §B3:333, §A2:201). Stale gap — введёт в заблуждение subagent'а («что-то не так с именем»). | reception_algorithm.md:494-496 | Удалить §F1 целиком (gap закрыт) либо переформулировать в «field name verified: `uom_id` (не `product_uom_id`)». |
| m3 | reception_algorithm.md §H:531-532 | Runtime instruction `Прочитал этот документ` + `Прочитал reconcile_finalize_action.py` — self-reference на сам алгоритм избыточен (subagent уже его читает). Код-mirror допустим per D9, но не как обязательное чтение, а как контракт. | reception_algorithm.md:531-532 | Заменить на «I have access to (a) this file (b) reconcile_finalize_action.py contract». |
| m4 | reception_algorithm.md §A4:220-228 | Carantine list incomplete: `214+ — спец. подразделы` без перечисления. Subagent догадывается. | reception_algorithm.md:220-228 | Перечислить 214-279 явно (если они есть в проде) либо удалить «214+ — спец. подразделы». |
| m5 | reception_algorithm.md §A5:243 | Barcode rule fuzzy: `default_code для цветов; manufacturer barcode допустим для твёрдых/горшечек`. Что значит «горшечки»? `categ_id=213 PLANTAS EN MACETAS`? Subagent с 50/50 шансом ошибётся. | reception_algorithm.md:243 | Привязать к categ_id: `barcode = default_code если categ_id ∈ {212,...}, иначе manufacturer barcode допустим`. |
| m6 | reception_algorithm.md §G:518 | `Concepto на каталанском` → `Levenshtein extended порог 5+, transliterate (cat→es). Если nothing → BLOCKER C`. Без алгоритма transliterate — subagent либо не сделает либо изобретёт свой. | reception_algorithm.md:518 | Привести минимальную таблицу cat→es или ссылку «out of scope, BLOCKER C сразу». |
| m7 | reception_algorithm.md §3 Step 1:73-83 | Threshold «pdftotext < 100 chars → BLOCKER» произвольный. Реальные битые PDF могут давать 200-400 chars (header только). | reception_algorithm.md:75-83 (логика парсинга) | Сделать threshold двумя проверками: «нет hit на `Cant`/`Concepto`/`Total` keywords» — функциональный, не char-count. |
| m8 | reception_algorithm.md §C1:396 | `[Лог] session=<short_id> algo=v12 closed=<UTC ISO8601>` — `algo=v12` зашит. При bump до v13 кто-то забудет. | reception_algorithm.md:396 | `algo=<value from §J>` или просто `algo` поле, заполняется из header. |
| m9 | reception_algorithm.md §2:56-59 | Hardcoded IDs: `res_model_id=819`, `activity_type_id=4`. Если перепушат таблицу `ir.model` или активити настройки — поломается тихо. | reception_algorithm.md:56-59 | Добавить «verified 2026-04-30 на espafloriasl.odoo.com» + рекомендацию pre-flight `search_records('ir.model', [['model','=','purchase.order']])`. |

### 2.4 ⚪ NIT

| # | Location | Issue | Evidence | Fix |
|---|---|---|---|---|
| n1 | reception_algorithm.md §C2:179 | `summary: f'🟠 Принять K substantial фиксов'` — англицизм «substantial фиксов». На мобильном owner'у не родное. | reception_algorithm.md:179 | `'🟠 Pedido <docNum>: K крупных правок на ревью'`. |
| n2 | reception_algorithm.md §0:23 | Hard rule #3 «Никаких half-actions» вне контекста identity — звучит как рекомендация по коду, не правило бизнеса. | reception_algorithm.md:23 | Перенести в §B как «Decisive rule: A/B/C — никаких половинных решений». |
| n3 | reception_algorithm.md §J:551-557 | Version log: `v: 1-10 — see git log` бесполезен для нового аудитора. | reception_algorithm.md:551-557 | Перечислить хотя бы заголовки v1, v6 (action 1217 v6 в проде), v11, v12 — что именно изменилось. |
| n4 | reception_algorithm.md везде | Mix RU/EN внутри одного абзаца («pre-flight verification», «Phase A2», «soft-gate») — неизбежно для тех-документа, но неконсистентно: где-то «Подтвердить», где-то «button_confirm». | по всему файлу | Глоссарий в §2 или сноска: «button_confirm = Подтвердить, button_validate = Валидировать (UI)» для cross-ref на mobile-friendly chatter. |
| n5 | reception_algorithm.md §2:67 | `review_color palette: 1=red, 2=orange, 3=yellow, 4=blue-legacy, 8=dark-blue, 10=green` — отсутствуют 5,6,7,9. Если когда-то появятся (Studio update) — bot не знает. | reception_algorithm.md:67 | Добавить «5-7,9 = reserved/unused — gate fallback по qty delta (см. §D3)». |
| n6 | reception_algorithm.md §3 Step 12:172 | `summary: f'🟠 Принять K substantial фиксов ({paper.docNum})'` — повторяет n1 в другом месте. Согласовать. | reception_algorithm.md:172 + reception_algorithm.md:179 | Один helper-template, ссылка в обоих местах. |

---

## 3. Lost-features inventory

| # | Source | Importance | What's missing |
|---|---|---|---|
| L1 | prompt_reconciliation_v3.5.txt:36 | MAJOR | «A wrong match is worse than an unmatched line» — основной safety принцип identity-policy. См. M3. |
| L2 | prompt_reconciliation_v3.5.txt:113-130 | MAJOR | Список broad tokens-not-identity (bouquet/bqt/mix/tropical/assorted/decorative/floral/greenery — 8 токенов с правилом «не establish identity сами по себе»). См. M4. |
| L3 | prompt_reconciliation_v3.5.txt:159-182 | MAJOR | Identity flexibility внутри narrow block — variety/cultivar/color/producer/style/legacy-naming OK когда species тот же. Без этого subagent дробит валидные rose↔rose матчи. См. M2. |
| L4 | prompt_reconciliation_v3.5.txt:215-241 | MAJOR | Learned vendor code rule — «Exact learned vendor code match should not receive lower confidence merely because the internal Odoo name is broad or ugly». v12 §A2:202 упоминает supplierinfo как strongest, но **не запрещает** downgrade на ugly name. |
| L5 | prompt_reconciliation_v3.5.txt:242-274 | MAJOR | Operator command rule — детальное описание `x_studio_operator_hit` semantics (когда сильнее learned, когда слабее, что не downgrade). v12 §A2:203 упоминает в одной строке. |
| L6 | prompt_reconciliation_v3.5.txt:275-298 | MAJOR | «Preserve existing product cards» — full раздел: когда existing assignment trust, когда reject. v12 §B1:249-271 имеет KEEP/Variant A/Variant C, но без явных условий когда reject existing assignment. |
| L7 | prompt_reconciliation_v3.5.txt:299-312 | MINOR | Duplicates / same-identity blocks tie-breaking rule (когда несколько кандидатов внутри narrow identity). v12 не покрывает. |
| L8 | prompt_reconciliation_v3.5.txt:313-326 | MINOR | «Missing line vs wrong card vs diagnostic mismatch» — 3-fold распознавание. v12 §G «Missing line» — частично. Diagnostic mismatch (identity good, qty/tax/price differ) явно не назван. |
| L9 | prompt_reconciliation_v3.5.txt:386-413 | MAJOR | «manual_review NOT a dump bucket» правило. v12 заменил manual_review на A/B/C decisive — это улучшение per pilot 2026-04-30, **но** «не использовать blocker C как dump bucket» нигде не зафиксировано. Замена не сохранила safety принцип. |
| L10 | prompt_reconciliation_v3.5.txt:422-444 | MAJOR | Match method discipline (precedence + «never default semantic»). См. M1. |
| L11 | prompt_reconciliation_v3.5.txt:446-470 | MAJOR | Confidence calibration bands. См. M5. |
| L12 | prompt_reconciliation_v3.5.txt:471-489 | MINOR | Document-level rules: financial totals mismatch не отменяет line matches. v12 §3 Step 8 pre-flight требует `amount_total ≈ paper.Total ±1€` — это **жёстче** v3.5 (там totals diagnostic). Может быть умышленно для финального state, но в процессе reconcile (pre-action 1217) это лишний gate. |
| L13 | SESSION_HANDOVER_2026-04-29.md:53 (§2.7) | MINOR | Warning «partner_id=23 это посторонняя запись, не использовать». v12 §2:53 даёт 42, не предупреждает о 23. На MCP search prone к ошибке. |
| L14 | SESSION_HANDOVER_2026-04-29.md:211-222 (§5.6) | MAJOR | Bookkeeper patterns 2/4 missing (merge с дропом, wrong-product substitution). См. M11. |
| L15 | SESSION_HANDOVER_2026-04-29.md:226-237 (§5.7) | MAJOR | ×2 inflation как hypothesis, не decisive blocker. См. B4. |
| L16 | SESSION_HANDOVER_2026-04-29.md:64 (§2.10) | MINOR | «STOP» = stop — owner protocol. Subagent не разговаривает с owner'ом мидл-pedido (только summary + activity), но если такая интеракция возникнет — правило потеряно. |
| L17 | SESSION_HANDOVER_2026-04-29.md:120 (§4.1) + memory feedback_cowork_git_workflow.md | MINOR | Subagent делает git ops через Desktop Commander, не bash. Не критично для приёмки (нет git ops в pipeline), но если subagent попробует commit Phase A — bash sandbox упадёт молча. |
| L18 | SESSION_HANDOVER_2026-04-29.md:132 (§4.4) | MINOR | `stock.return.picking` wizard quirk: `quantity=0` default + явный set перед `action_create_returns()`. v12 §D1 ROLLBACK абстрактен. Subagent сам не пишет wizard (это action 1217), но если придётся retry/debug — знание потеряно. |

---

## 4. Internal contradictions

| # | Statement A | Statement B | Conflict |
|---|---|---|---|
| C1 | reception_algorithm.md §3 Step 6:110 — «Для каждой строки **5 решений** (см. §B):» | reception_algorithm.md:111-117 — нумерованный 1-6 (Card / Quantity / Pack vs stem / Tax / Price / Name) | Заявлено 5, перечислено 6. Уже flagged как B5. |
| C2 | reception_algorithm.md §0:24 — `Direct env['mail.message'].create({...}), не message_post (та escape'ит HTML)` | reception_algorithm.md §3 Step 11:160 — `mcp__odoo__create_record('mail.message', {...})` | По смыслу одно и то же (через MCP это и есть create). Но §0 пишет про `env['mail.message'].create` — это server-side syntax (внутри ir.actions.server). Subagent на MCP не имеет `env` — путаница терминологии. |
| C3 | reception_algorithm.md §1.2:42 — `Все stock.move.x_studio_review_color ∈ {2 orange, 3 yellow, 8 dark-blue, 10 green}` | reception_algorithm.md §D3:455 — `else (color == 0): fallback по qty delta` | §1.2 говорит финальное состояние не должно содержать color=0; §D3 говорит gate допускает 0 как fallback path. Если pre-action color=0 и qty delta=0 — gate проходит, но финал имеет color=0, нарушая §1.2. |
| C4 | reception_algorithm.md §F2:498 — `agent вручную cancels backorder через update_record({'state': 'cancel'})` | reception_algorithm.md §D5:467 — `❌ obj.field = value (use write({...}))` (имплицитно через G8 правило) | §F2 предлагает direct state write; §D5 говорит про safe_eval, но spirit — состояния через action. Уже flagged как B3. |
| C5 | reception_algorithm.md §B2:323 — `Odoo > paper > tolerance (stem) → paper-truth override` | reception_algorithm.md §0:21 — `Никогда не сравниваем Holded цену с paper. Paper price пишется silent на каждой строке.` | §0 для PRICE говорит paper-truth silent — это OK. §B2 для QTY делает аналогичный paper-truth, но qty это **уже подсчитанные стебли бухгалтером** — не Holded import. Овержайтить = переписать florist work. Concept smearing: «paper-truth» применён где не должен (qty bookkeeper count ≠ price Holded import). Уже flagged как B2. |
| C6 | reception_algorithm.md §B1a:277 — `Family identity — все товары одной категории (CL разных сортов, CR разных сортов, ...)` | reception_algorithm.md §3 Step 5:107 — `Strict identity gate: NARROW species/type match. Допустимо rose↔rose, EUC cinerea↔EUC cinerea. НЕ допустимо rose↔general flower, EUC cinerea↔EUC parvifolia.` | §3 Step 5 запрещает EUC cinerea↔EUC parvifolia (одна семья, разные виды). §B1a допускает MIX-карту с CL разных **сортов** + PHAL разных **variants** — это уровень cultivar/variety. Граница «семьи» нечёткая. Subagent не различит «species OK» от «family OK» когда EUC cinerea + EUC parvifolia сидят на одной MIX-card в Odoo. |

---

## 5. Production-contract drift

| # | reception_algorithm.md says | reconcile_finalize_action.py does | Drift |
|---|---|---|---|
| P1 | §D1:434 ROLLBACK: «reverse done picking → button_draft → clear Phase A на лайнах» (без enumeration) | reconcile_finalize_action.py:49 — `write({'price_unit': 0, 'x_studio_supplier_sku': False, 'x_studio_supplier_product_name': False, 'x_studio_item_comment': False})` | 4 поля чистится, **`x_studio_expected_qty` НЕ чистится**. v12 не enumerates → subagent не знает. См. M6. |
| P2 | §D2:441 Phase A2 pack: `quantity = expected_qty (stems)` | reconcile_finalize_action.py:122 — `stems = line.x_studio_expected_qty or paq_count` | Fallback на `paq_count` (число пачек ≠ стеблей). См. M7. |
| P3 | §D1:432 RETRY: `state='purchase' AND есть picking в 'assigned'` | reconcile_finalize_action.py:55 — `pending = pedido.picking_ids.filtered(lambda p: p.state not in ('done','cancel'))` | RETRY срабатывает на любом non-done/cancel picking, не только assigned. См. M8. |
| P4 | §F2:498-501 — agent должен cancel backorder через write state='cancel' | reconcile_finalize_action.py — не имеет логики cancel backorder | v12 предписывает действие, противоречащее G8. Код этого не делает (планируется v7.8). См. B3. |
| P5 | §D2:443 — «Все writes под `tracking_disable=True, mail_create_nolog=True, mail_notrack=True`» | reconcile_finalize_action.py — везде ✅ confirmed на каждом write/button_call | Совпадает. |
| P6 | §D3:451-455 — gate logic с PASS_COLORS=(10,8,3,2), BLOCK_COLORS=(1,4) | reconcile_finalize_action.py:21-22 | Совпадает. |
| P7 | §0:24 — «Direct env['mail.message'].create({...})» | reconcile_finalize_action.py — после v7.7 mail.message create вынесен из action в subagent (комментарии в файле:130, 169) | Совпадает по версии. |
| P8 | §D2:439 — pre-flight (amount>0, all lines have supplier_sku) | reconcile_finalize_action.py:99-107 — checks `amount_total <= 0` AND `not order_line` AND `unfilled = filter(not supplier_sku)` | Совпадает. |
| P9 | §D2:445 — `picking.with_context(skip_backorder=True, ...).button_validate()` | reconcile_finalize_action.py:165 — то же | Совпадает. |

---

## 6. Section-by-section quality scores

| Section | Clarity (1-5) | Completeness (1-5) | Consistency (1-5) | Self-contained (Y/N) | Notes |
|---|---|---|---|---|---|
| §0 EXECUTIVE SUMMARY | 4 | 3 | 4 | Y | Hard rule #3 (decisive A/B/C) вне identity-context. Не упомянут «wrong match worse than unmatched» (M3). |
| §1 INPUT/OUTPUT | 4 | 3 | 3 | Y | Не упомянут color=0 case в output spec (C3, m1). |
| §2 CONSTANTS | 5 | 3 | 4 | Y | Hardcoded next SKU (M10), warning про partner_id=23 потерян (L13), incomplete carantine list (m4). |
| §3 CORE PIPELINE | 4 | 3 | 3 | Y | Step 6 «5 решений» vs 6 (B5), Step 1 char-threshold (m7), Step 8 pre-flight жёстче чем у v3.5 (L12). |
| §A REFERENCE TABLES | 3 | 3 | 4 | Y | §A2 hierarchy без discipline (M1), §A4 incomplete, §A5 barcode rule fuzzy (m5). |
| §B DECISION TREES | 3 | 2 | 2 | Y | §B2 row 3 contradicts HANDOVER §2.4 (B2), row 5 ×2 elevation (B4), tolerance edge cases (M9). Identity flexibility отсутствует (M2). MIX vs species граница нечёткая (C6). |
| §C TEXT FORMAT | 4 | 4 | 4 | Y | Англицизмы (n1, n6), `algo=v12` hardcode (m8), но в целом mobile-friendly format на месте. |
| §D ACTION 1217 CONTRACT | 4 | 3 | 3 | Y | RETRY description shorter than code (M8), ROLLBACK fields not enum (M6, P1), Phase A2 fallback не описан (M7, P2). |
| §E RETRY / IDEMPOTENCY | 3 | 2 | 4 | Y | Нет описания «что если crash mid-Phase A2» (агент догадывается). Нет checkpoint mechanism. |
| §F KNOWN OPEN WORK | 2 | 3 | 1 | Y | §F1 stale (m2), §F2 prescribes G8 violation (B3). |
| §G EDGE CASES | 3 | 2 | 3 | Y | Bookkeeper patterns 2/4 missing (M11, L14), Catalan vague (m6). |
| §H RUNTIME CHECKLIST | 1 | 2 | 2 | **N** | BLOCKER B1 — instructs to read MEMORY.md. Self-reference (m3). |
| §I SUPERVISOR WORKFLOW | 4 | 4 | 4 | Y | Подробен; вне scope subagent. Не аудитим строго. |

---

## 7. Top 5 priorities to fix before next pilot

1. **§B2 row 3** (paper-truth override на Odoo>paper>tolerance stem) — переключить на `accept Odoo qty + activity 🟠` (см. B2). Без этого бот будет переписывать florist recount при положительной дельте, ровно противоположно HANDOVER §2.4.
2. **§H:533** — удалить строку про MEMORY.md (см. B1). Self-containment — hard owner requirement.
3. **§F2:498** — заменить `update_record({'state':'cancel'})` на «leave for supervisor / wait v7.8» (см. B3). Direct state write на stock.picking ломает computed (G8).
4. **§B2 row 5** (×2 ratio = 🔴 red) — понизить до 🟡 yellow + activity «pattern observation» (см. B4). Definitive blocker без owner-обсуждения противоречит §5.7 hypothesis statusу.
5. **§3 Step 6:110** — поправить «5 решений» → «6 решений» (см. B5). Однострочный фикс, который снимает риск пропуска одного из шести шагов subagent'ом.

---

## 8. Auditor's confidence

**Files I successfully read fully:**
- `/Users/andriy/Documents/master-context/master-context/prompt_reconciliation_v3.5.txt` (595 lines)
- `/Users/andriy/Documents/master-context/master-context/SESSION_HANDOVER_2026-04-29.md` (463 lines)
- `/Users/andriy/Documents/master-context/master-context/reconcile_finalize_action.py` (175 lines)
- `/Users/andriy/Documents/master-context/master-context/reception_algorithm.md` (559 lines)
- `/Users/andriy/Documents/master-context/master-context/99_invariants.md` (114 lines)
- `/Users/andriy/Documents/master-context/master-context/CHANGELOG.md` (top 30 entries)
- `/Users/andriy/Documents/master-context/CLAUDE.md` (auto-loaded at session start)

**Files unread / partial:**
- `master-context/memory/MEMORY.md` и feedback_*.md / project_*.md — упомянуты в §H, но per audit prompt sec.D9 их содержимое **должно быть инлайнено в reception_algorithm.md**, поэтому я их не читал — само наличие зависимости и есть finding (B1, m3, L17, L18).

**Domains where my findings might be incomplete:**
- **Action 1217 corner cases**: я не воспроизводил каждую try/except цепочку прода и не проверял все 11 grabli HANDOVER §4 на соответствие текущему коду v7.7. Есть шанс что P1 ROLLBACK clear-set уже расширен в более новой версии prod, не отражённой в `reconcile_finalize_action.py` master-context.
- **Odoo 19 schema verify**: я не проверял live, что `purchase.order.line` имеет именно `product_qty` / `price_unit` / `uom_id` (не `product_uom_id`) — опираюсь на §F1 v12 + код v7.7. Если поля переименованы — несколько строк §3 Step 6 «писать в purchase.order.line» сломаются.
- **§A4 carantine 214+** не верифицирован против `product.category` table (нет live access).
- **MIX vs species граница (C6)**: я флагнул противоречие, но без бизнес-context не могу решить что правильно — это решение owner'а.
