# Serviflor package: online 15000475

Status: READY_NO_BOOKKEEPER

## Processing rule
Start from 01_online_order as placed-order truth. Use 02_processed_todas_optional only as Serviflor processed/fulfilled evidence; do not double-count it. Use 03_factura as commercial truth for Odoo PO totals. Use 04_bookkeeper_workbook for SKU/pack/recount/store split if present.

## Note
Serviflor layers match; bookkeeper workbook missing. Needs operational allocation before import.

## Missing / warnings
- workbook_missing
