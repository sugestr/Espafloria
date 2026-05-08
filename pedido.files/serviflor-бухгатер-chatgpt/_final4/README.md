# Serviflor subagent catalog v4.4

One folder = one Serviflor online-order event.

For each subagent, provide:
1. the event folder;
2. files from 00_GLOBAL_REFERENCES;
3. the production prompt v4.4.

Important:
- Online order is event axis.
- Factura PDF is commercial truth for Odoo PO.
- Bookkeeper workbook is strong SKU/pack/split hint if no hard conflict.
- Holded Albaran and Holded Compras are downstream evidence only.
- If 06_holded_compras_evidence exists, use it as extra SKU/price/accounting evidence for this folder.
- Ignore old workbook-only Vilassar/Vilasar files not tied to current Serviflor online orders.
