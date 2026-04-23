<!-- v: 1 | updated: 2026-04-23T16:35Z -->
# Claude Session Feedback / Lessons Learned

Накопленные правила работы Claude в проекте Espafloria. Эти правила выработаны через ошибки в предыдущих сессиях и должны загружаться в **любую новую Claude-сессию** для сохранения контекста.

В Claude memory эти же правила лежат отдельными файлами в `memory/feedback_*.md` — но memory может сбрасываться. Этот файл — **долгосрочный backup в git**.

При начале новой сессии Claude должен **прочитать этот файл первым**, до любых правок в Espafloria-системе.

---

## 1. Odoo — всегда методы/actions, не прямые writes

**Правило:** прежде чем править запись в Odoo через `update_record`/`write`, проверить — есть ли **штатный action/method**, который делает то же с правильными side effects. Если есть — звать его. Прямой write — только когда штатного пути нет.

**Почему важно:**

1. **State machines** (pos.session, sale.order, stock.picking, mrp.production и т.п.) — штатный action (`action_confirm`, `action_cancel`, `button_validate`, `action_pos_session_closing_control` и т.д.) выставляет все смежные поля и проводки. Прямой write ломает computed fields.
2. **Inventory (stock.quant)** — штатный путь: write `inventory_quantity` + call `action_apply_inventory` → Odoo создаёт `stock.move` с правильными source/dest locations. Прямой write в `quantity` обходит audit trail.
3. **Смежные эффекты** — многие штатные actions триггерят chatter-сообщения, notifications, автоматизации. Write в обход их пропустит.

**Конкретные случаи:**
- 22 апреля 2026: force-closed pos.session id=34 через `write({'state': 'closed'})` без `stop_at`. На следующий день Owner не смог открыть POS — `_compute_last_session` падал с RPC_ERROR на `.astimezone()` от `False`. Штатный action закрытия выставил бы `stop_at` сам.
- 23 апреля 2026: для подъёма stock с -12 до 10 правильный путь — `stock.quant.inventory_quantity=10 + action_apply_inventory`, а не прямой write `quantity`.

**Как применять:**
1. Перед любым `update_record` на критичное поле — вспомнить: «это data edit или state/audit действие?»
2. Если state/audit — искать в модели метод с префиксом `action_`, `button_`, `do_`.
3. Если есть — звать через `mcp__odoo__execute_method`. Если в MCP такого нет — либо просить user сделать через UI (3 клика), либо создать `ir.actions.server` с кодом и запустить.
4. Прямой write на critical поля — только при отсутствии штатного пути, и с пониманием что computed/audit сломается.

**Mental check:** «Если бы эту запись менял живой человек в UI — что бы он нажал?» Если кнопку с именем — её и надо звать.

---

## 2. Odoo 19 stock.return.picking API

Wizard `stock.return.picking` в Odoo 19 имеет только 2 записываемых поля: `picking_id` и `product_return_moves` (o2m на `stock.return.picking.line`). **Нет `location_id`** — передача его в create vals поднимает ошибку.

Поля `stock.return.picking.line`: `product_id` (required), `quantity` (required), `move_id`, `to_refund`, `wizard_id`.

Метод создания возвратного picking: `action_create_returns()` — возвращает action dict с `res_id` нового picking.

**ACL:** `stock.return.picking` доступен только группе `Inventory / User` (id=56). POS-user (группа 87 Point of Sale / User) НЕ имеет прав. Для вызова из action на pos.payment / pos.order нужен `.sudo()`.

**Why:** при дебаге action 1203 (Bouquet re-assembly) reverse старого POS picking тихо падал в except — сначала из-за несуществующего `location_id`, потом из-за ACL. Оба исправления нужны.

**Шаблон применения:**
```python
env['stock.return.picking'].sudo().with_context(
    active_id=pick.id, active_ids=pick.ids, active_model='stock.picking'
).create({
    'picking_id': pick.id,
    'product_return_moves': [(0, 0, {
        'product_id': m.product_id.id,
        'quantity': m.product_uom_qty,
        'move_id': m.id,
    }) for m in pick.move_ids if m.state == 'done'],
}).action_create_returns()
```

Потом на возвратном picking: `mv.write({'quantity': mv.product_uom_qty})` для каждого move, затем `.with_context(skip_backorder=True).button_validate()` (тоже sudo на browse нового picking).

---

## 3. sale.order.line discount перезатирается на create

При `env['sale.order'].create({'order_line': [(0,0,{'discount': 50, ...})]})` значение `discount` не сохраняется — `sale.order.line._compute_discount` / pricelist onchange пересчитывает его в 0 на основе партнёра и прайслиста.

**Why:** в Bouquet workstream discount 50% с POS cart не перенёсся в новый SO BP-2026-0007. POS line показывал discount=50, SO line показал discount=0. Partner=53 (Anon) без pricelist — всё равно перетёр.

**Как применять:** после `so = env['sale.order'].create(vals)` явно прописать discount на SO-линиях:
```python
for pl, sol in zip(pos_order.lines, so.order_line):
    if pl.discount:
        sol.write({'discount': pl.discount})
```
(Python 3 safe_eval не даёт `iter`/`next` — только `zip`.)

`price_unit` аналогично может перетереться pricelist'ом — если важен ценник POS, пропиши и его.

---

## 4. Всегда смотреть актуальные Odoo 19 docs

Перед утверждениями о поведении Odoo 19 (POS / stock / Settle / SO flows) — **всегда верифицировать через**:
1. **Live base через MCP** (актуальное поведение в проде)
2. **Существующие code snapshots** в `master-context/` (наши actions могут уже обрабатывать edge case)
3. **Odoo 19 official docs** — `doc.odoo.com/19`, `help.odoo.com`, форум Odoo версии 19

**Why:** Знания Claude из training data — в основном Odoo 16/17/18-centric. Odoo 19 заметно изменил POS internals (stock moves timing, Settle/SO linkage, order reference handling). 23 апреля user поймал на утверждении про double-stock bug в Settle+ordinary payment flow — flow на самом деле работает штатно, я просто использовал старую модель Settle из предыдущих версий.

**Как применять:**
- Никогда не говорить «это вызовет проблему X» про POS/SO/stock без шага верификации.
- Если подозрение на квирк Odoo — fetch doc page, читать код на сервере (`ir.actions.server` или model methods), запустить тестовый query.
- Когда user говорит «мы уже это обсуждали» — доверять и **переверифицировать**, не повторять старое утверждение.
- POS internals меняются почти каждый major release. POS поведение — version-specific.

---

## 5. POS config changes требуют closed sessions

Перед любым изменением `pos.payment.method`, `pos.config.payment_method_ids`, `warehouse_id`, `picking_type_id` — **все сессии этого config должны быть в state `closed`**. Odoo 19 специально блокирует write'ы с ошибкой «закройте открытые сессии».

**Важный нюанс:** после закрытия сессии Odoo 19 **автоматом** создаёт следующую в state `opening_control` (для удобства следующей смены). Эта «предоткрытая» сессия **считается активной** для целей блокировки конфига. Имя «/», owner = тот, кто последним открыл POS UI.

**Как применять:**
1. Закрыть все open sessions через штатный Close (UI или `action_pos_session_closing_control`).
2. Поискать дополнительно `pos.session.state in ('opened', 'opening_control')` — найти остатки.
3. Cancel/close opening_control через backend (POS → Sessions → Cancel) либо full cycle через POS UI (Open → 0 cash → Close).
4. Потом делать изменения config'а.

**Связано с инвариантами:** §45 (POS cache refreshes), §17 (automation timing).

**Контекст случая:** 23 апреля 2026 после теста 1.1 в POS Plaza/00023 — закрыли смену, появилась session 38 в opening_control. Update имени pos.payment.method id=6 отклонён с ошибкой «Please close open sessions».

---

## 6. Cowork mode — git commit делается user'ом, не Claude через bash

**Разделение слоёв файловой работы:**

1. **File tools (Read/Write/Edit)** — работают с **реальным диском user'а** через workspace mount (например `/Users/andriy/Documents/master-context/`). Полные права на чтение/запись содержимого файлов. Изменения видны user'у мгновенно.

2. **`mcp__workspace__bash`** — это **отдельный sandbox-env** (Linux). Workspace папки видны через mount (`/sessions/.../mnt/master-context/`), но **с ограниченными правами**:
   - Read — обычно работает
   - Write/Edit/Delete на обычные файлы — может не работать (`Operation not permitted`)
   - **Modify `.git/` internals — запрещено** → `git add` может работать частично, но `git commit` падает с lock errors потому что не может cleanup `.git/index.lock` и `tmp_obj_*` файлы
   - rm/mv/cp на user-файлы — обычно блокированы

**✅ Правильный flow:**
1. Claude обновляет содержимое файлов через `Write`/`Edit` (реальный диск, full perms).
2. Claude генерирует commit message в своём ответе.
3. **User в своём локальном терминале** делает: `git add` + `git commit` + `git push`.
4. Если нужно посмотреть `git status` или `git diff` — bash работает (это read).

**❌ Неправильно:** пытаться `git commit` из `mcp__workspace__bash` — возможны частичные writes в `.git/objects/` без cleanup, локи остаются, последующие git ops падают.

**Что делать если случайно начал commit и сломалось:** user должен `rm -f .git/index.lock` в своём терминале перед следующей попыткой. Stage сохраняется (`git add` обычно работает).

**Случай 23 апреля 2026** — попытался закомитить букетный refactor через bash → `unable to unlink '.git/objects/52/tmp_obj_*'` → `index.lock` остался → `git commit` failed twice. User объяснил что это неправильный путь, я должен был просто Write файлы и отдать commit-msg user'у для локального терминала.

**Bash для git — только read-only ops:** `git status`, `git diff`, `git log`, `git branch -v` — это OK.

---

## См. также

- [99_invariants.md](99_invariants.md) — бизнес-инварианты Espafloria (37+ правил)
- [12_ai_workflow.md](12_ai_workflow.md) — multi-chat архитектура для Claude
- `memory/feedback_*.md` (только в Claude session storage, не в git) — отдельные файлы для quick recall

---

## Когда обновлять этот файл

Каждый раз, когда **новый feedback** появляется в Claude memory (`memory/feedback_*.md`):
1. Добавить раздел в этот документ.
2. Bump `v` в header + `updated`.
3. Update `VERSIONS.md`.
4. Запись в `CHANGELOG.md`.
5. Обычный commit + push.

Этот файл должен оставаться **точным mirror'ом** Claude memory feedback files — чтобы любая новая сессия могла загрузить его и работать с тем же контекстом.
