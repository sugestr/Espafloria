<!-- v: 15 | updated: 2026-04-21T17:30Z -->
# CHANGELOG

Одна строка на worker-сессию. Детали — `git log master-context/` или `git show <sha>`.

Хранится максимум ~15 последних записей. Старые просто удаляются — их содержание уже уехало в git history.

---

- 2026-04-21 — eWallet POS prepayment chain end-to-end PROD-validated (Tata 100€ deposit → 3€ redemption, JE 19/20/21 verified). Income Account fix on discount product 7862 (false → 438000), orphan 7860 archived. New invariants §44 (eWallet/giftcard top-up: account 438 + tax 0% = multipurpose voucher) and §45 (top-up product activates in POS only AFTER loyalty.program exists, else ghost liability). 08 §E new section, 09 P2 «POS rights granularity» + «Bouquets as entity» queued.
- 2026-04-19 — Mega-session: POS launch (3 configs + warehouses fix + POS Terminal user + employee PIN), catalog migration v2.1→v2.2 (10 карточек, 2 бага fixed, category tree Flores Cortadas 287-290), 6 новых инвариантов (§38-43), make.com OLD_ SKU awareness TODO
- 2026-04-19 — Business-logic rebuild: 99 invariants tightened (2+35 merged, 25/26/27 reformulated, new #35 marketplace); POS warehouse config as P0; code/ path fixes; M-level cleanup across 01-10
- 2026-04-19 — Two transport paths documented (Claude Code + zip), GitHub connector in SYNC_STATE
- 2026-04-19 — Meta cleanup: flat-layout stale paths, --reset + zip-match in commit script, upload SoT in SYNC_STATE
- 2026-04-18 — README moved into master-context/, root stub for GitHub only
- 2026-04-18 — Fully flat layout: everything at master-context/ root, only legacy_migrations/ as subfolder
- 2026-04-18 — Split artifacts/code: odoo_actions/ (in Project) vs migrations/ (git only)
- 2026-04-18 — Flat layout + sandbox-delivery worker protocol + commit script
- 2026-04-18 — Base polish: SHA-sync → version-sync, commit-gate for worker
- 2026-04-18 — Multi-chat architecture: roles, briefings, SYNC_STATE
- 2026-04-18 — CRM scope, salary model, инварианты 31-37
- 2026-04-18 — Vision + 15-step roadmap, source files index
- 2026-04-18 — Hot-fix: migrate_variant supplierinfo copy, purchase_method bulk
- 2026-04-18 — Master Context initial (00-09, 99, artifacts)
