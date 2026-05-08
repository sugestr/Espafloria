# post_mortem.md

- What was wrong: previous v5.0-style run could over-classify rows as packs and inflate/alter PO mechanics in Odoo.
- Root cause: pack decision relied too much on workbook bought_packs instead of independent factura/UoM gate.
- Affected files: purchase order import and UoM classification.
- Correction: factura remains commercial truth; only 9 cut-flower rows with strong pack evidence use UoM DB ID 31; all plant/composition rows use Unit DB ID 1.
- Prevention rule: all-pack or excessive-pack result is a blocking UoM gate failure; PO self-check must equal factura base/IVA/total before delivery.
