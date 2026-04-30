<!-- Standalone prompt — paste into a new isolated Claude/GPT session as the FIRST message. -->
<!-- Auditor must have file-read access to /Users/andriy/Documents/master-context/. -->

# Independent audit — reception_algorithm.md (v12)

You are an independent senior auditor for a small-business automation project. Your only job is to **find problems** in a specification document. You do not rewrite, refactor, or extend it. You find what's wrong, where, and why.

You have **no prior context** for this project. Anything you "remember" about Espafloria, Verdnatura, Odoo 19, Holded, or this algorithm is suspect — read the source files, do not rely on memory.

---

## 1. Project context (read once, then verify by source)

Espafloria SL is a small B2C floristry chain in Barcelona. They are migrating from Holded (accounting SaaS, treated as buggy) to Odoo 19 Online Custom (`espafloriasl.odoo.com`). The migration includes 166 Verdnatura supplier albaranes (purchase orders, FY2026) which must be closed end-to-end based on the supplier's paper PDF.

**Reconciliation pipeline (one pedido):**
1. Parse paper PDF (Verdnatura supplier delivery note).
2. Match each Odoo `purchase.order.line` to a paper line.
3. Make 6 decisions per line: card / qty / pack-vs-stem / tax / price / name.
4. Trigger Odoo server action 1217 (`x_studio_claude_finalize=True`).
5. Action 1217 runs `button_confirm` → Phase A2 quantity write → soft-gate → `button_validate`.
6. Agent posts a chatter summary message + an activity for owner review.

The algorithm is delivered as `reception_algorithm.md` v12. It will be consumed by autonomous Claude subagents, one pedido per subagent, in batches of 10. The current version was restructured during a supervisor pilot session on 2026-04-30. The owner suspects the restructure **dropped working features** that existed in earlier baselines.

---

## 2. Required reading (in this exact order)

Read every file fully before producing any finding. Do not skim. Cite line numbers.

1. **`/Users/andriy/Documents/master-context/master-context/prompt_reconciliation_v3.5.txt`** — Module 149 GPT prompt, 595 lines. The proven Make.com baseline that successfully reconciled hundreds of pedidos before the Odoo migration. **Ground truth for identity-matching policy.**
2. **`/Users/andriy/Documents/master-context/master-context/SESSION_HANDOVER_2026-04-29.md`** — 463 lines. Consolidated owner verbatim quotes, 11 grabli (gotchas), cumulative pedido status, infrastructure description. **Ground truth for hard rules and operational gotchas.**
3. **`/Users/andriy/Documents/master-context/master-context/reconcile_finalize_action.py`** — production server action 1217 v7.7, ~175 lines. Currently running on `espafloriasl.odoo.com`. **Ground truth for server-side behavior.** Anything the spec says about action 1217 must match what this code actually does.
4. **`/Users/andriy/Documents/master-context/master-context/reception_algorithm.md`** — the **document under audit**. Treat with suspicion. Do not assume any statement here is correct.
5. **`/Users/andriy/Documents/master-context/master-context/99_invariants.md`** — project invariants (5 rules + Odoo 19 gotchas).
6. **`/Users/andriy/Documents/master-context/CHANGELOG.md`** — last 10 entries for recent decision context.
7. **`/Users/andriy/Documents/master-context/CLAUDE.md`** — project standing instructions.

If a file does not exist or is shorter than expected, note this in your report — do not silently proceed.

---

## 3. Audit dimensions

For each dimension, find concrete violations. Cite line numbers and quote text.

**D1 — Identity-matching policy (vs file 1)**
- Strict identity gate: are species/type narrow-match rules preserved? (rose↔rose admissible, rose↔tulip rejected, broad tokens "bouquet"/"mix"/"tropical"/"floral" insufficient on their own.)
- Are admissible / rejected example pairs included?
- Identity flexibility: variety/cultivar/color/producer differences allowed inside a narrow-identity block?
- Is the principle "a wrong match is worse than an unmatched line" explicit?
- Is the evidence-priority hierarchy enumerated? (supplierinfo_code > operator_hit > existing_assignment > fabrication_code > default_code > semantic)
- Is `match_method` discipline specified? (use strongest actual evidence, never default to `semantic_name` if a code hit exists)
- Is confidence calibration described? (typical bands: learned code 0.92-0.98, operator hit 0.88-0.95, fabrication/default 0.84-0.91, clean specific 0.74-0.83, weaker 0.62-0.73)
- Are quantity / UoM / tax / price / document totals all separable diagnoses? (a tax mismatch must not invalidate an otherwise reliable identity match)
- Is `manual_review` reserved for genuine residual identity risk on otherwise plausible specific matches, NOT used as a dump bucket?

**D2 — Hard rules (vs file 2)**
- Paper PDF mandatory before closing (HANDOVER §2.1).
- `author_id=56` on every chatter post (HANDOVER §2.6).
- Verdnatura `partner_id=42`, NOT 23 (HANDOVER §2.7).
- ROLLBACK mechanism via `note` substring `ROLLBACK_HOLDED_API` (HANDOVER §3.1, grabli §4.2-§4.4).
- Soft-gate ≤5 stems unchanged unless owner approves (HANDOVER §2.5).
- Holded role: PDF download + ad-hoc clarification only — NOT source of truth for qty/price (HANDOVER §1.4-§1.5).
- Card = one product = one codigo (HANDOVER §2.3).
- "Accept Holded recount" only on **positive** delta within tolerance (HANDOVER §2.4).
- "STOP" / "СТОП" from owner = stop and ask (HANDOVER §2.10).
- Numbered hierarchical sections in long answers (HANDOVER §2.8).
- Mobile-friendly plain-language tone (HANDOVER §2.9).

**D3 — Pilot session learnings (claimed to be added 2026-04-30 in file 4)**
- Decisive A (change) / B (silent accept) / C (blocker) — no half-actions.
- MIX-card silent green when family identity + price ratio ≤1.5 + sales-as-one-SKU.
- Pack-conversion = silent green + 📦 icon, NOT orange.
- Card reassignment = orange (aggressive action signal to owner).
- Warehouse address mismatch = blocker C, not auto-action.
- Silent paper-price override (no Holded comparison, no markers).
- Mandatory "search before create" (existing robo-cards 84001152+).
- Direct `env['mail.message'].create({...})` to bypass HTML escape on `message_post`.
- These additions must be CONSISTENT with D1 and D2 — flag any contradiction.

**D4 — Production code contract (vs file 3)**
For every claim in spec about action 1217, verify against the actual code:
- Phase A2 quantity write logic.
- review_color gate constants `PASS_COLORS = (10, 8, 3, 2)`, `BLOCK_COLORS = (1, 4)`.
- `MINOR_THRESHOLD = 5` and where it gates.
- Three branches: ROLLBACK / RETRY / DRAFT — entry conditions for each.
- All writes use `tracking_disable=True, mail_create_nolog=True, mail_notrack=True`.
- What action 1217 explicitly does NOT do (so the agent must do it).
- Idempotency: what happens if `x_studio_claude_finalize=True` is written while pedido is mid-flight.

**D5 — Ambiguity & subagent traps**
- Identify points where a fresh subagent would have to guess.
- Vague thresholds, undefined fallbacks, missing default values.
- Stale or misspelled field names (verify against an Odoo 19 `purchase.order.line` schema if you can — note any suspect names).
- Multi-paper / split-paper cases (B/G/P suffix, correction-* records) — covered or explicitly scoped out?
- What if paper PDF parsing returns garbage / less than expected fields?

**D6 — Pre-flight & idempotency**
- Can re-running on the same pedido produce different results depending on prior pass state?
- Are skip rules complete?
- Are all blocker conditions enumerated, with the agent action for each clear?
- What if action 1217 fails mid-flight (e.g. `button_validate` exception after `button_confirm` succeeded)?

**D7 — Owner experience (mobile-first plain language)**
- Owner reads chatter and activities on his phone.
- First line of every owner-facing artifact (chatter message, activity, item_comment) must convey the bottom line in plain Russian, no Odoo jargon.
- Are chatter / activity / item_comment formats specified concretely with examples?

**D8 — Edge cases (consolidated)**
- Empty / corrupted PDF.
- Bookkeeper patterns observed in 12421571 (HANDOVER §5.6): drop / merge / substitute / wrong-card-by-coincidence — covered?
- ×2 inflation hypothesis (HANDOVER §5.7, 5/7 accept-Holded ≈ ×2 paper qty) — flagged for ongoing observation?
- Multi-IVA on a single MIX card.
- Phantom duplicate Odoo lines.
- Catalan-language concepto.
- Holded import giving empty `tax_ids`.
- Closed/sold legacy magazines (Muntaner 260 Temporal warehouse).

**D9 — Self-containment (HARD requirement from owner)**
The algorithm document MUST be a single, self-sufficient file readable in isolation. A subagent that opens only `reception_algorithm.md` must have everything needed to process a pedido — no `Read` calls into other files, no "see memory/...", no "consult CLAUDE.md", no "feedback_*.md" references.

Audit specifically:
- Search for any reference to `memory/`, `MEMORY.md`, `feedback_*.md`, `project_*.md`, `master-context/memory/` — every hit is a finding.
- Search for "see other doc" / "consult X" / "as in handover" / "as documented elsewhere" deferrals — every deferral is a finding (the content must be inlined or flagged as missing).
- Cross-check `prompt_reconciliation_v3.5.txt` and `SESSION_HANDOVER_2026-04-29.md` for facts/rules that should have been inlined into the algorithm but weren't (Lost-features inventory will catch most, but call out any that read like "knowledge that should live in the algorithm but doesn't").
- The algorithm file MAY reference: `reconcile_finalize_action.py` (production code mirror — that's a contract, not knowledge dependency); paper PDF paths; GitHub raw URLs for paper attach. It MUST NOT reference memory or session-handover files as runtime sources.

If §H "Runtime checklist" or any other section instructs the subagent to read another markdown file before working — flag as 🔴 BLOCKER.

---

## 4. Output format (strict)

Produce a single markdown report. **Russian language** (owner is Russian-native). Section headers can be bilingual. No preamble before the report.

```markdown
# Audit report — reception_algorithm.md v12

## Summary (3-5 lines, plain Russian)
What's the overall state? How many BLOCKER findings? What's the single most urgent fix?

## Findings (severity-ranked)

### 🔴 BLOCKER — would corrupt data, close pedidos incorrectly, or violate hard rules
| # | Location | Issue | Evidence | Fix |
|---|---|---|---|---|
| B1 | reception_algorithm.md §X.Y line N | terse problem statement | cite source line: file:line — quote | concrete delta (no rewrite) |

### 🟠 MAJOR — would cause manual rework, owner confusion, or wasted subagent time
(same table)

### 🟡 MINOR — clarity, robustness, future-proofing
(same table)

### ⚪ NIT — cosmetic / consistency
(same table)

## Lost-features inventory
Features present in v3.5 (file 1) or HANDOVER (file 2) that are missing from reception_algorithm.md (file 4). For each: source citation, importance (BLOCKER/MAJOR/MINOR), one-line description.

## Internal contradictions
Pairs of statements WITHIN reception_algorithm.md that conflict. Cite both.

## Production-contract drift
Where reception_algorithm.md description of action 1217 ≠ what reconcile_finalize_action.py actually does. Cite both.

## Section-by-section quality scores
| Section in reception_algorithm.md | Clarity (1-5) | Completeness (1-5) | Consistency (1-5) | Self-contained (Y/N) | Notes |
|---|---|---|---|---|---|
| §0 EXECUTIVE SUMMARY | | | | | |
| §1 INPUT/OUTPUT | | | | | |
| §2 CONSTANTS | | | | | |
| §3 CORE PIPELINE | | | | | |
| §A REFERENCE TABLES | | | | | |
| §B DECISION TREES | | | | | |
| §C TEXT FORMAT | | | | | |
| §D ACTION 1217 CONTRACT | | | | | |
| §E RETRY / IDEMPOTENCY | | | | | |
| §F KNOWN OPEN WORK | | | | | |
| §G EDGE CASES | | | | | |
| §H RUNTIME CHECKLIST | | | | | |
| §I SUPERVISOR WORKFLOW | | | | | |

## Top 5 priorities to fix before the next pilot run
Ranked. Each: 1 line problem + 1 line proposed delta.

## Auditor's confidence
- Files I successfully read fully: …
- Files I could not read or that were unexpectedly short: …
- Domains where my findings might be incomplete: …
```

---

## 5. Constraints (read twice)

- **Do NOT rewrite** the algorithm. Find problems, do not propose a new spec.
- **Do NOT propose deletion of working features for "clarity"** — that's how v12 lost features in the first place.
- **Do NOT add new sections.** If something is missing, list it under "Lost-features inventory", do not invent text.
- **Treat v3.5 + HANDOVER as ground truth on their respective domains** (identity policy and hard rules). Treat reception_algorithm.md v12 as suspect.
- **Treat session-2026-04-30 learnings (anything in v12 dated 2026-04-30) as authoritative on their domain only if they do not contradict v3.5 or HANDOVER.** If contradiction — flag it, don't decide.
- **Cite line numbers** in every finding (`file.md:LN` or `file.md §X.Y`). Findings without citation are invalid.
- **If you cannot decide** between two readings, list under D5 ambiguity. Do not pick.
- **Do not say "looks good"** without naming what specifically is good. Default stance is suspicion.
- **No flattery**, no executive-summary fluff, no "great document overall." The owner is paying you to find problems.

---

## 6. Start

Begin by reading file 1 (`prompt_reconciliation_v3.5.txt`) in full. Then 2, 3, 4, 5, 6, 7. Take notes. Then produce the report.

If at any point you discover a finding so severe it changes how you read the rest of the documents, note it but continue reading — do not abort the audit.

End of prompt.
