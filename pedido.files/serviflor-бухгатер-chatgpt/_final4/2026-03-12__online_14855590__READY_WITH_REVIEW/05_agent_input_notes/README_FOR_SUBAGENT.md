# Serviflor package: online 14855590

Status: READY_WITH_REVIEW

## Processing rule
Start from 01_online_order as placed-order truth. Use 02_processed_todas_optional only as Serviflor processed/fulfilled evidence; do not double-count it. Use 03_factura as commercial truth for Odoo PO totals. Use 04_bookkeeper_workbook for SKU/pack/recount/store split if present.

## Note
Factura higher by likely packaging: Galleda/Alça. Line-check required.

