# Prompt v4.4 note

Use one universal prompt for both Holded Albarán and Holded Compras evidence.
Do not split into separate prompts. The subagent should read whichever evidence folder exists:
- Albarán/Odoo CSV: downstream store/albarán evidence.
- Compras export/evidence: downstream purchase/SKU/price recognition evidence.

In folders with 06_holded_compras_evidence, use Compras as SKU/price matching evidence only. Factura remains commercial truth. Workbook remains pack/recount/split truth.
