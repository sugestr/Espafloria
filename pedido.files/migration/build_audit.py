"""
A1.19.7.2 audit pipeline for Espafloria quarantine catalog.
Reads 5 input XLSX, produces 2-sheet audit XLSX + summary numbers for KB md.
"""
import pandas as pd
import re
import sys
from collections import Counter, defaultdict

BASE = "/sessions/bold-exciting-johnson/mnt/espafloria.odoo/pedido.files/migration"

# ---------- 1. Load inputs ----------
print("[1/8] Loading inputs...")
prod = pd.read_excel(f"{BASE}/odoo_products_2026-05-10.xlsx", header=0)
si = pd.read_excel(f"{BASE}/odoo_supplierinfo_2026-05-10.xlsx", header=0)
ped = pd.read_excel(f"{BASE}/odoo_pedidos_with_lines_2026-05-10.xlsx", header=0)
hold = pd.read_excel(f"{BASE}/holded_products_2026-05-10.xlsx", header=3)
hold_compras = pd.read_excel(f"{BASE}/holded_compras_items_2026-05-10.xlsx", header=3)

print(f"  prod: {len(prod)}, si: {len(si)}, ped rows: {len(ped)}, hold: {len(hold)}, compras: {len(hold_compras)}")

# ---------- 2. Filter to quarantine ----------
print("[2/8] Filter to quarantine...")
prod['categ_id_str'] = prod['categ_id'].fillna('').astype(str)
quarantine = prod[prod['categ_id_str'].str.startswith('⛔ Карантин Holded')].copy()
print(f"  quarantine cards: {len(quarantine)}")

# ---------- 3. Process Holded products ----------
print("[3/8] Process Holded products...")
HOLDED_CATS = [
    'FLORES CORTADAS', 'NOMBRES DE FLORES', 'PLANTAS EN MACETAS', 'NOMBRES DE PLANTAS',
    'PRODUCTOS ESPECIALES', 'ENTREGA', 'MACETAS PARA PLANTAS', 'JARRONES Y CONTENEDORES',
    'DECORACION Y ADORNOS', 'VELAS Y PORTAVELAS', 'EMBALAJE (упаковка)', 'Consumibles (расходники)'
]

def get_holded_categoria(row):
    for c in HOLDED_CATS:
        if c not in row.index:
            continue
        v = row[c]
        if pd.notna(v) and str(v).strip() and str(v).strip().lower() not in ('nan', 'none', ''):
            return c
    return ''

hold['holded_categoria'] = hold.apply(get_holded_categoria, axis=1)
hold['_sku_norm'] = hold['SKU'].fillna('').astype(str).str.strip().str.lower()
hold['_codigo_norm'] = hold['Código'].fillna('').astype(str).str.strip().str.lower()
hold['_name_norm'] = hold['Nombre'].fillna('').astype(str).str.strip().str.lower()

print("  hold columns:", list(hold.columns))

# Find expected columns
def find_col(substrs, exclude=None):
    for c in list(hold.columns):
        cs = str(c).lower()
        if exclude and any(e.lower() in cs for e in exclude):
            continue
        for s in substrs:
            if s.lower() in cs:
                return c
    return None

col_subtotal = find_col(['subtotal'])
col_total = None
# 'Total' alone may match many; pick column literally 'Total'
for c in hold.columns:
    if str(c).strip().lower() == 'total':
        col_total = c; break
col_stock = None
# Find a numeric stock col — typically named 'Almacén' or 'Stock'. We'll look for 'Stock' or 'Disponible' or 'Cantidad'
col_stock = find_col(['stock'])
col_iva = find_col(['iva', 'impuesto'])

print(f"  subtotal={col_subtotal!r} total={col_total!r} stock={col_stock!r} iva={col_iva!r}")

# Build Holded indexes
hold['_subtotal'] = pd.to_numeric(hold['Subtotal'], errors='coerce')
hold['_total'] = pd.to_numeric(hold['Total'], errors='coerce')
hold['_stock'] = pd.to_numeric(hold['Stock'], errors='coerce')
# Holded Impuestos column has labels like "IVA 10%", "IVA 21%"
hold['_iva_label'] = hold['Impuestos'].fillna('').astype(str).str.strip()

hold_by_sku = {}
hold_by_codigo = {}
hold_by_name = {}
for idx, h in hold.iterrows():
    if h['_sku_norm']:
        hold_by_sku.setdefault(h['_sku_norm'], idx)
    if h['_codigo_norm']:
        hold_by_codigo.setdefault(h['_codigo_norm'], idx)
    if h['_name_norm']:
        hold_by_name.setdefault(h['_name_norm'], idx)

print(f"  hold indexes: by_sku={len(hold_by_sku)}, by_codigo={len(hold_by_codigo)}, by_name={len(hold_by_name)}")

# ---------- 4. Build pedido lines aggregates ----------
print("[4/8] Process pedido lines...")
# Forward-fill ID so each line knows its pedido
ped['ID_ff'] = ped['ID'].ffill()
ped['Order Date_ff'] = ped['Order Date'].ffill()
ped['Vendor_ff'] = ped['Vendor/Name'].ffill()
lines = ped[ped['Order Lines/Product/Name'].notna()].copy()
lines['name_strip'] = lines['Order Lines/Product/Name'].astype(str).str.strip()
lines['qty'] = pd.to_numeric(lines['Order Lines/Quantity'], errors='coerce').fillna(0)

# Aggregate by product name
ped_agg = lines.groupby('name_strip').agg(
    pedido_lines_count_2026=('name_strip','size'),
    total_qty_purchased_2026=('qty','sum'),
).reset_index()
print(f"  lines: {len(lines)}, distinct products in pedido: {len(ped_agg)}")

# ---------- 5. Build supplierinfo aggregates ----------
print("[5/8] Process supplierinfo...")
si['_partner'] = si['partner_id'].fillna('').astype(str)
si['_tmpl_str'] = si['product_tmpl_id'].fillna('').astype(str)
si['_product_code'] = si['product_code'].fillna('').astype(str).str.strip()
si['_product_name'] = si['product_name'].fillna('').astype(str).str.strip()
si['_identity_key'] = si['x_studio_supplier_identity_key'].fillna('').astype(str).str.strip()

# Extract default_code prefix from product_tmpl_id text
def extract_si_code(s):
    m = re.match(r'^\[([^\]]+)\]', str(s))
    if m:
        return m.group(1).strip()
    return ''

si['_tmpl_code'] = si['_tmpl_str'].apply(extract_si_code)
si['_tmpl_default_code'] = si['product_tmpl_id/default_code'].fillna('').astype(str).str.strip()
# Use default_code if available (more reliable), else fall back to extracted code
si['_join_code'] = si['_tmpl_default_code'].where(si['_tmpl_default_code'] != '', si['_tmpl_code'])

# Aggregate per template default_code
si_agg = defaultdict(lambda: {
    'count': 0, 'verdnatura_codes': [], 'serviflor_keys': [],
    'partners': set(), 'product_names': set()
})
si_verdnatura_no_codigo = 0
si_serviflor_no_key = 0
for _, r in si.iterrows():
    code = r['_join_code']
    if not code:
        continue
    bag = si_agg[code]
    bag['count'] += 1
    partner = r['_partner']
    bag['partners'].add(partner)
    if r['_product_name']:
        bag['product_names'].add(r['_product_name'])
    if 'VERDNATURA' in partner.upper():
        if r['_product_code']:
            bag['verdnatura_codes'].append(r['_product_code'])
        else:
            si_verdnatura_no_codigo += 1
    elif 'SERVIFLOR' in partner.upper():
        if r['_identity_key']:
            bag['serviflor_keys'].append(r['_identity_key'])
        else:
            si_serviflor_no_key += 1

print(f"  supplierinfo aggregated by default_code: {len(si_agg)}")
print(f"  Verdnatura without product_code: {si_verdnatura_no_codigo}")
print(f"  Serviflor without identity_key: {si_serviflor_no_key}")

# ---------- 6. Build per-card audit row ----------
print("[6/8] Build audit rows...")

# Make pedido name->agg dict
ped_dict = ped_agg.set_index('name_strip').to_dict('index')

def safe_str(v, default=''):
    if pd.isna(v):
        return default
    return str(v).strip()

def safe_num(v, default=0.0):
    try:
        f = float(v)
        if pd.isna(f): return default
        return f
    except Exception:
        return default

audit_rows = []
red_flag_counts = Counter()
mix_candidates = []  # for §6
holded_match_methods = Counter()

# Track dup SKU
sku_counter = Counter()
for _, r in quarantine.iterrows():
    sku = safe_str(r['default_code'])
    if sku:
        sku_counter[sku.lower()] += 1
dup_skus = {k for k, v in sku_counter.items() if v > 1}

# Top-level category extraction
def top_categ(cat_str):
    """⛔ Карантин Holded / FLORES CORTADAS / ROSA UNIFLORA → 'FLORES CORTADAS'"""
    if not cat_str: return ''
    parts = [p.strip() for p in cat_str.split(' / ')]
    if len(parts) >= 2:
        return parts[1]
    return 'ROOT'  # only Карантин root

def sub_categ(cat_str):
    parts = [p.strip() for p in (cat_str or '').split(' / ')]
    if len(parts) >= 3:
        return parts[2]
    return ''

quarantine['top_categ'] = quarantine['categ_id_str'].apply(top_categ)
quarantine['sub_categ'] = quarantine['categ_id_str'].apply(sub_categ)

# Sheet 1 cats: FLORES CORTADAS, PLANTAS EN MACETAS, ROOT
SHEET1_CATS = {'FLORES CORTADAS', 'PLANTAS EN MACETAS', 'ROOT'}
# Sheet 2 cats: hardware
SHEET2_CATS = {
    'DECORACION Y ADORNOS', 'EMBALAJE (упаковка)', 'Consumibles (расходники)',
    'EQUIPAMIENTO (оборудование)', 'ENTREGA', 'PRODUCTOS ESPECIALES',
    'JARRONES Y CONTENEDORES', 'MACETAS PARA PLANTAS', 'VELAS Y PORTAVELAS'
}

for _, r in quarantine.iterrows():
    odoo_id_str = safe_str(r['id'])
    name = safe_str(r['name'])
    sku = safe_str(r['default_code'])
    barcode = safe_str(r['barcode'])
    categ_id_full = safe_str(r['categ_id'])
    list_price = safe_num(r['list_price'])
    standard_price = safe_num(r['standard_price'])
    qty_avail = safe_num(r['qty_available'])
    available_in_pos = safe_str(r['available_in_pos'])
    purchase_method = safe_str(r['purchase_method'])
    pos_categ_ids = safe_str(r['pos_categ_ids'])

    # Pedido aggregation by name
    pa = ped_dict.get(name.strip(), None)
    pedido_count = int(pa['pedido_lines_count_2026']) if pa else 0
    total_qty = float(pa['total_qty_purchased_2026']) if pa else 0.0
    was_in_pedido = 'yes' if pedido_count > 0 else 'no'

    # Supplierinfo aggregation by default_code
    si_bag = si_agg.get(sku, None) if sku else None
    si_count = si_bag['count'] if si_bag else 0
    suppliers_set = set()
    if si_bag:
        for p in si_bag['partners']:
            up = p.upper()
            if 'VERDNATURA' in up: suppliers_set.add('Verdnatura')
            elif 'SERVIFLOR' in up: suppliers_set.add('Serviflor')
            else: suppliers_set.add(p[:25])
    suppliers_str = ' + '.join(sorted(suppliers_set))

    # Top supplier codes
    top_verd = ''
    if si_bag and si_bag['verdnatura_codes']:
        top_verd = Counter(si_bag['verdnatura_codes']).most_common(1)[0][0]
    top_serv = ''
    if si_bag and si_bag['serviflor_keys']:
        top_serv = Counter(si_bag['serviflor_keys']).most_common(1)[0][0]

    # MIX detector
    distinct_supplier_names = len(si_bag['product_names']) if si_bag else 0

    # Match against Holded
    holded_match_idx = None
    match_method = ''
    if sku and sku.lower() in hold_by_sku:
        holded_match_idx = hold_by_sku[sku.lower()]; match_method = 'sku'
    elif barcode and barcode.lower() in hold_by_codigo:
        holded_match_idx = hold_by_codigo[barcode.lower()]; match_method = 'codigo'
    elif name and name.lower() in hold_by_name:
        holded_match_idx = hold_by_name[name.lower()]; match_method = 'name'

    holded_match_methods[match_method or 'no_match'] += 1

    if holded_match_idx is not None:
        h = hold.iloc[holded_match_idx]
        h_id = idx_to_id = f"row_{holded_match_idx}"  # Holded export does not include ID, use row index
        h_subtotal = safe_num(h.get('Subtotal'))
        h_total = safe_num(h.get('Total'))
        h_stock = safe_num(h.get('Stock'))
        h_iva = safe_str(h.get('Impuestos'))
        h_categoria = safe_str(h.get('holded_categoria'))
    else:
        h_id = ''
        h_subtotal = h_total = h_stock = 0.0
        h_iva = h_categoria = ''

    # Price match status
    if holded_match_idx is None:
        price_match = 'no_holded_match'
    else:
        if list_price <= 0 and h_subtotal <= 0:
            price_match = 'both_zero'
        elif list_price <= 0:
            price_match = 'odoo_zero'
        elif h_subtotal <= 0:
            price_match = 'holded_zero'
        else:
            diff = (list_price - h_subtotal) / h_subtotal
            if abs(diff) < 0.05:
                price_match = 'match'
            elif abs(diff) > 0.20:
                price_match = 'large_diff'
            elif diff > 0:
                price_match = 'odoo_higher_5pct'
            else:
                price_match = 'odoo_lower_5pct'

    # Red flags
    flags = []
    if not name:
        flags.append('name_empty')
        red_flag_counts['name_empty'] += 1
    if not sku:
        flags.append('sku_empty')
        red_flag_counts['sku_empty'] += 1
    if not barcode:
        flags.append('barcode_empty')
        red_flag_counts['barcode_empty'] += 1
    if sku and sku.lower() in dup_skus:
        flags.append('dup_sku')
        red_flag_counts['dup_sku'] += 1
    # supplier flags need full si scan, deferred to end (but we can use si_bag info)
    if si_count == 0 and pedido_count == 0:
        flags.append('card_no_supplierinfo_no_pedido')
        red_flag_counts['card_no_supplierinfo_no_pedido'] += 1
    if si_count == 0 and pedido_count > 0:
        flags.append('card_no_supplierinfo_but_used_2026')
        red_flag_counts['card_no_supplierinfo_but_used_2026'] += 1
    if holded_match_idx is None:
        flags.append('holded_no_match')
        red_flag_counts['holded_no_match'] += 1
    if price_match == 'large_diff':
        flags.append('price_large_diff')
        red_flag_counts['price_large_diff'] += 1
    if distinct_supplier_names >= 3:
        flags.append('mix_candidate')
        red_flag_counts['mix_candidate'] += 1
        mix_candidates.append({
            'name': name, 'sku': sku,
            'distinct_supplier_names': distinct_supplier_names,
            'pedido_lines_count_2026': pedido_count,
            'examples': '; '.join(list(si_bag['product_names'])[:5]) if si_bag else '',
        })
    if qty_avail < 0:
        flags.append('negative_stock')
        red_flag_counts['negative_stock'] += 1

    # group_root_carantine for ROOT-only cards
    grc = ''
    if r['top_categ'] == 'ROOT':
        grc = 'used_in_2026' if pedido_count > 0 else 'not_used_in_2026'

    audit_rows.append({
        'odoo_id': odoo_id_str,
        'name': name,
        'default_code': sku,
        'barcode': barcode,
        'categ_id': categ_id_full,
        'top_categ': r['top_categ'],
        'sub_categ': r['sub_categ'],
        'list_price': list_price,
        'standard_price': standard_price,
        'qty_available': qty_avail,
        'available_in_pos': available_in_pos,
        'purchase_method': purchase_method,
        'pos_categ_ids': pos_categ_ids,
        'был_в_закупках_2026': was_in_pedido,
        'pedido_lines_count_2026': pedido_count,
        'total_qty_purchased_2026': total_qty,
        'supplierinfo_count': si_count,
        'suppliers': suppliers_str,
        'top_supplier_codigo': top_verd,
        'top_supplier_identity_key': top_serv,
        'holded_match_id': h_id,
        'holded_match_method': match_method,
        'holded_list_price_subtotal': h_subtotal,
        'holded_list_price_total': h_total,
        'holded_stock': h_stock,
        'holded_iva': h_iva,
        'holded_categoria': h_categoria,
        'price_match_status': price_match,
        'red_flags': '; '.join(flags),
        'group_root_carantine': grc,
    })

print(f"  audit rows: {len(audit_rows)}")
audit_df = pd.DataFrame(audit_rows)

# ---------- 7. Split into 2 sheets ----------
print("[7/8] Split into 2 sheets...")
sheet1 = audit_df[audit_df['top_categ'].isin(SHEET1_CATS)].copy()
sheet2 = audit_df[audit_df['top_categ'].isin(SHEET2_CATS)].copy()
other = audit_df[~audit_df['top_categ'].isin(SHEET1_CATS | SHEET2_CATS)].copy()
print(f"  sheet1 (flowers + root carantine): {len(sheet1)}")
print(f"  sheet2 (hard goods): {len(sheet2)}")
print(f"  other (uncategorized): {len(other)}")
if len(other) > 0:
    print("  other top_categ values:", other['top_categ'].value_counts().to_dict())

out_path = f"{BASE}/audit_2026-05-10.xlsx"
with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
    sheet1.to_excel(writer, sheet_name='карантин_цветы_root', index=False)
    sheet2.to_excel(writer, sheet_name='твердый_товар', index=False)
    if len(other) > 0:
        other.to_excel(writer, sheet_name='прочее', index=False)
print(f"  -> {out_path}")

# ---------- 8. Compute summary stats for KB md ----------
print("[8/8] Compute summary stats...")

print()
print("="*80)
print("SUMMARY")
print("="*80)

# §1 Объём — top-level + sub-categ counts
print("\n--- §1 Top-level distribution ---")
print(quarantine['top_categ'].value_counts().to_string())
print("\n--- §1 Sub-categ distribution ---")
print(quarantine.groupby(['top_categ','sub_categ']).size().sort_values(ascending=False).to_string())

# §2 Supplierinfo coverage
print("\n--- §2 Supplierinfo coverage ---")
audit_df['si_bucket'] = pd.cut(audit_df['supplierinfo_count'],
                                bins=[-1, 0, 2, 5, 999],
                                labels=['0', '1-2', '3-5', '6+'])
print("Distribution by supplierinfo bucket:")
print(audit_df['si_bucket'].value_counts().to_string())

# Verdnatura/Serviflor breakdown
si['is_verdnatura'] = si['_partner'].str.upper().str.contains('VERDNATURA')
si['is_serviflor'] = si['_partner'].str.upper().str.contains('SERVIFLOR')
print(f"\nVerdnatura SI rows: {si['is_verdnatura'].sum()}")
print(f"Verdnatura without product_code: {(si['is_verdnatura'] & (si['_product_code']==''))[lambda x: x].sum()}")
print(f"Serviflor SI rows: {si['is_serviflor'].sum()}")
print(f"Serviflor without identity_key: {(si['is_serviflor'] & (si['_identity_key']==''))[lambda x: x].sum()}")

# §3 Activity 2026
print("\n--- §3 Activity 2026 ---")
print(f"Total quarantine cards: {len(audit_df)}")
print(f"Cards used in pedido 2026: {(audit_df['pedido_lines_count_2026']>0).sum()}")
print(f"Cards NOT used in pedido 2026: {(audit_df['pedido_lines_count_2026']==0).sum()}")

# Per top_categ
print("\nUsed-in-2026 per top_categ:")
print(audit_df.groupby('top_categ').agg(
    total=('odoo_id','size'),
    used=('pedido_lines_count_2026', lambda s: (s>0).sum())
).to_string())

# 675 root-only split
print("\nROOT-only carantine split:")
root_df = audit_df[audit_df['top_categ']=='ROOT']
print(root_df['group_root_carantine'].value_counts().to_string())

# §4 Price match status
print("\n--- §4 Price match (Odoo↔Holded) ---")
print(audit_df['price_match_status'].value_counts().to_string())
print(f"\nHolded match methods: {dict(holded_match_methods)}")

# Top-10 large_diff
print("\nTop-10 large_diff examples:")
ld = audit_df[audit_df['price_match_status']=='large_diff'].copy()
ld['diff_pct'] = (ld['list_price'] - ld['holded_list_price_subtotal']) / ld['holded_list_price_subtotal']
ld = ld.sort_values('diff_pct', key=lambda s: s.abs(), ascending=False)
print(ld[['name','default_code','list_price','holded_list_price_subtotal','diff_pct']].head(10).to_string())

# §5 Red flags counters
print("\n--- §5 Red flags ---")
for k, v in red_flag_counts.most_common():
    print(f"  {k}: {v}")

# §6 MIX candidates
print(f"\n--- §6 MIX candidates: {len(mix_candidates)} total ---")
mix_top = sorted(mix_candidates, key=lambda d: -d['pedido_lines_count_2026'])[:20]
for m in mix_top:
    print(f"  {m['name'][:50]:50s} sku={m['sku']:15s} suppliers={m['distinct_supplier_names']} pedido={m['pedido_lines_count_2026']}")

# §7 Holded gap by month for Verdnatura
print("\n--- §7 Holded gap (Verdnatura compras by month) ---")
hc = hold_compras.copy()
hc['_contacto'] = hc['Contacto'].fillna('').astype(str).str.upper()
verd_hc = hc[hc['_contacto'].str.contains('VERDNATURA')].copy()
verd_hc['Fecha'] = pd.to_datetime(verd_hc['Fecha'], errors='coerce')
verd_hc['_subtotal'] = pd.to_numeric(verd_hc['Subtotal'], errors='coerce').fillna(0)
verd_hc['ym'] = verd_hc['Fecha'].dt.to_period('M').astype(str)
verd_by_month = verd_hc.groupby('ym').agg(
    rows=('_subtotal','size'),
    subtotal_eur=('_subtotal','sum')
).reset_index()
print(verd_by_month.to_string(index=False))

# Compare to Odoo pedido subtotal by month for Verdnatura
ped_verd = ped[ped['Vendor/Name'].fillna('').str.upper().str.contains('VERDNATURA')].copy()
ped_verd['Order Date'] = pd.to_datetime(ped_verd['Order Date'], errors='coerce')
ped_verd['_subtotal'] = pd.to_numeric(ped_verd['Untaxed Amount'], errors='coerce').fillna(0)
ped_verd['ym'] = ped_verd['Order Date'].dt.to_period('M').astype(str)
ped_by_month = ped_verd.groupby('ym').agg(
    rows=('_subtotal','size'),
    subtotal_eur=('_subtotal','sum')
).reset_index()
print("\nOdoo pedido (Verdnatura) by month:")
print(ped_by_month.to_string(index=False))

print("\n--- DONE ---")
print(f"Audit XLSX: {out_path}")

