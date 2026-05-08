# Post-mortem / blocker

Factura 001369/2026 contains two payable returnable packaging lines:
- GALLEDA BASE IMP. (RETORNABLE): 14 × 4.00 = 56.00, IVA 21%
- ALÇA IMP. (RETORNABLE): 6 × 3.00 = 18.00, IVA 21%

No safe product.product External ID was found in the workbook mapping or Product Variant export. Clean PO files were generated only for 28 mapped goods lines and are marked BLOCKED/PARTIAL. Do not import as final Pedido until the two tara products are mapped or created in Odoo.
