"""
A4 Catalog Design v1 — analysis pipeline.
Reads 5 input xlsx + a3 extracted attributes,
produces:
  - migration_map_2026-05-10.xlsx (3 sheets: old_to_new, new_templates, archive_candidates)
  - prints summary numbers used by markdown design doc

Run: python3 build_a4_design.py
Author: A4 sub-agent 2026-05-10
"""
import pandas as pd
import re
import warnings
import json
import os
from collections import Counter, defaultdict

warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# 1. LOAD INPUTS
# ============================================================================

print("=" * 70)
print("A4 Catalog Design — analysis pipeline")
print("=" * 70)

# Audit (2 sheets)
xl_audit = pd.ExcelFile(os.path.join(BASE, 'audit_2026-05-10.xlsx'))
df_flowers = pd.read_excel(xl_audit, 'карантин_цветы_root')
df_hard = pd.read_excel(xl_audit, 'твердый_товар')
audit = pd.concat([df_flowers, df_hard], ignore_index=True)
print(f"audit cards loaded: {len(audit)} ({len(df_flowers)} flowers + {len(df_hard)} hard)")

# A3 attributes
xl_a3 = pd.ExcelFile(os.path.join(BASE, 'a3_extracted_attributes_2026-05-10.xlsx'))
a3 = pd.read_excel(xl_a3, 'proposed_per_card')
a3_tags = pd.read_excel(xl_a3, 'proposed_tags_catalog')
a3_attrs = pd.read_excel(xl_a3, 'proposed_variant_attributes')
print(f"A3 per-card: {len(a3)}, tags catalog: {len(a3_tags)}, attrs: {len(a3_attrs)}")

# Holded (header row 4 = index 3)
df_holded = pd.read_excel(os.path.join(BASE, 'holded_products_2026-05-10.xlsx'), header=3)
print(f"Holded products: {len(df_holded)}")

# Supplierinfo
df_si = pd.read_excel(os.path.join(BASE, 'odoo_supplierinfo_2026-05-10.xlsx'))
print(f"Supplierinfo: {len(df_si)}")

# Pedidos
df_ped = pd.read_excel(os.path.join(BASE, 'odoo_pedidos_with_lines_2026-05-10.xlsx'))
print(f"Pedido rows: {len(df_ped)}")

# ============================================================================
# 2. MERGE AUDIT + A3 — single working dataframe of 395 used cards
# ============================================================================

# Build join key: prefer default_code; fallback to odoo_id-derived numeric to avoid NaN collisions
def make_join_key(dc, oid):
    s = str(dc).strip()
    if s and s.lower() not in ('nan', 'none', ''):
        return f"DC::{s}"
    # NaN default_code → use odoo numeric id as tie-breaker
    soid = str(oid)
    # Extract numeric id from "__export__.product_template_8337_..." or just digits
    m = re.search(r'product_template_(\d+)', soid) or re.search(r'^(\d+)$', soid)
    if m:
        return f"OID::{m.group(1)}"
    return f"OID::{soid}"

audit['_jk'] = audit.apply(lambda r: make_join_key(r['default_code'], r['odoo_id']), axis=1)
a3['_jk'] = a3.apply(lambda r: make_join_key(r['default_code'], r['odoo_template_id']), axis=1)

# Sanity: a3 has 395, audit-used has 395; expect ~395 join
audit_used = audit[audit['был_в_закупках_2026']=='yes'].copy()
print(f"audit_used unique join keys: {audit_used['_jk'].nunique()} / {len(audit_used)}")
print(f"a3 unique join keys: {a3['_jk'].nunique()} / {len(a3)}")

# Inner-join on join key
work = a3.merge(
    audit_used[['_jk', 'odoo_id', 'list_price', 'standard_price',
           'holded_list_price_subtotal', 'holded_list_price_total',
           'holded_stock', 'holded_iva', 'holded_categoria',
           'pedido_lines_count_2026', 'total_qty_purchased_2026',
           'price_match_status', 'red_flags', 'sub_categ', 'top_categ',
           'categ_id', 'qty_available', 'available_in_pos', 'purchase_method',
           'top_supplier_codigo', 'supplierinfo_count']],
    on='_jk', how='left', suffixes=('', '_audit'))
work['_dc'] = work['_jk']  # for downstream supplierinfo merge — re-keyed below

work = work.rename(columns={'red_flags_audit': 'audit_red_flags',
                             'red_flags': 'a3_red_flags'})
print(f"\nMerged: {len(work)} (a3 with audit data)")
print(f"  with holded_subtotal: {work['holded_list_price_subtotal'].notna().sum()}")
print(f"  with list_price: {work['list_price'].notna().sum()}")

# ============================================================================
# 3. LAST PURCHASE COST per card (from supplierinfo, max date)
# ============================================================================

df_si['_jk'] = df_si.apply(
    lambda r: make_join_key(r.get('product_tmpl_id/default_code'), r.get('product_tmpl_id', '')),
    axis=1)
df_si['_date'] = pd.to_datetime(df_si['date_start'], errors='coerce')
df_si_sorted = df_si.sort_values('_date', ascending=False)
last_cost = df_si_sorted.groupby('_jk').agg(
    last_supplier_price=('price', 'first'),
    last_supplier_partner=('partner_id', 'first'),
    last_supplier_date=('_date', 'first'),
).reset_index()

work = work.merge(last_cost, on='_jk', how='left')
print(f"  with last_supplier_price: {work['last_supplier_price'].notna().sum()}")

# ============================================================================
# 4. GROUP INTO FAMILIES (genus + variety + treatment)
#    Family = candidates for one template (maybe with variants)
# ============================================================================

def make_family_key(row):
    """Family key for grouping cards into single template candidates."""
    g = row['proposed_genus'] if pd.notna(row['proposed_genus']) else 'NO_GENUS'
    g = str(g).replace('Genus:', '')
    v = row['proposed_variety'] if pd.notna(row['proposed_variety']) else ''
    v = str(v).replace('Variety:', '')
    # Strip common variety prefixes that just mark length/type
    v = re.sub(r'^(RS|RSR|GRS)\s+', '', v)
    # For Rosa: variety alone is the family. For others: genus alone.
    if g == 'Rosa':
        return f"Rosa::{v}"
    elif g in ('NO_GENUS', '') and v:
        # NO_GENUS hardware (cajas, oasis, etc) — keep each card distinct
        # Use both variety and key (prevent multi-card collisions of unrelated stuff)
        return f"NO_GENUS::{v}::{row.get('_jk', row.get('default_code', '?'))}"
    elif g == 'NO_GENUS':
        return f"NO_GENUS::{row.get('_jk', row.get('default_code', '?'))}"
    else:
        # For non-rosa: genus is the family unit (variants of variety+length under it)
        return f"{g}::__GENUS__"

work['family_key'] = work.apply(make_family_key, axis=1)

# But: split families if pack_mode differs strongly (cut vs potted)
# Check categ_id_path: if some are PLANTAS EN MACETAS and others FLORES CORTADAS, split
def pack_class(row):
    cp = str(row.get('categ_id_path', ''))
    if 'PLANTAS EN MACETAS' in cp:
        return 'potted'
    elif 'FLORES CORTADAS' in cp:
        return 'cut'
    elif 'EMBALAJE' in cp:
        return 'packaging'
    elif 'EQUIPAMIENTO' in cp:
        return 'equipment'
    elif 'Consumibles' in cp:
        return 'consumable'
    elif 'PRODUCTOS' in cp:
        return 'special'
    elif 'DECORACION' in cp:
        return 'decoration'
    return 'other'

work['pack_class'] = work.apply(pack_class, axis=1)
work['family_key'] = work['family_key'] + '::' + work['pack_class']

family_sizes = work.groupby('family_key').size().sort_values(ascending=False)
print(f"\nFamilies: {len(family_sizes)} groups; multi-card families: {(family_sizes>1).sum()}")
print("Top-15 families:")
for fk, n in family_sizes.head(15).items():
    print(f"  {n:3d}  {fk}")

# ============================================================================
# 5. DECIDE FORM PER FAMILY (flat / 1-axis / 2-axis / split)
# ============================================================================

def decide_family_form(group):
    """
    Decide template form for a family of cards.
    Returns (form, variant_axes_text, notes).
    """
    n = len(group)
    is_mix = (group['is_mix_candidate']=='yes').any()
    pack_class = group['pack_class'].iloc[0]
    has_length = group['proposed_variant_length_cm'].notna()
    has_pot = group['proposed_variant_pot_size_cm'].notna()
    distinct_lengths = group['proposed_variant_length_cm'].dropna().unique()
    distinct_pots = group['proposed_variant_pot_size_cm'].dropna().unique()
    distinct_colors = group['proposed_variant_color'].dropna().unique()
    distinct_tiers = group['proposed_mix_tier'].dropna().unique()

    # Check for multi_length_conflict in red_flags
    multi_length_conflict = group['a3_red_flags'].fillna('').astype(str).str.contains('multi_length_conflict').any()

    if n == 1:
        row = group.iloc[0]
        # Single card. Could still need length variants if multi_length_conflict.
        if multi_length_conflict and len(str(row.get('length_distribution',''))) > 5:
            # Card has supplier evidence of multiple lengths — propose 1-axis variant
            # Extract distinct lengths from length_distribution
            ld = str(row['length_distribution'])
            lens = [int(x.split(':')[0]) for x in ld.split(',') if ':' in x and x.split(':')[0].isdigit()]
            lens = sorted(set(lens))
            if len(lens) >= 2:
                return ('1-axis', f"Длина (см): {lens}", 'auto-propose length variants from supplier evidence')
        return ('flat', '', '')

    # n >= 2 cards in family
    if pack_class == 'cut':
        # Cut flowers: typical axis is Length
        if len(distinct_lengths) >= 2:
            lens = sorted([int(x) for x in distinct_lengths if pd.notna(x)])
            return ('1-axis', f"Длина (см): {lens}", f'{n} cards merge to length variants')
        # If is_mix and tiers differ
        if is_mix and len(distinct_tiers) >= 2:
            tiers = [str(t).replace('MixTier:', '') for t in distinct_tiers]
            return ('1-axis', f"MIX Tier: {tiers}", 'mix-tier separation')
        # Otherwise split (keep separate)
        return ('split', '', f'{n} cards in family but no clear axis — keep separate')

    elif pack_class == 'potted':
        if len(distinct_pots) >= 2:
            pots = sorted([int(x) for x in distinct_pots if pd.notna(x)])
            return ('1-axis', f"Размер горшка (см): {pots}", f'{n} cards merge to pot size variants')
        if len(distinct_lengths) >= 2 and len(distinct_pots) >= 2:
            lens = sorted([int(x) for x in distinct_lengths if pd.notna(x)])
            pots = sorted([int(x) for x in distinct_pots if pd.notna(x)])
            return ('2-axis', f"Длина: {lens} × Горшок: {pots}", '2-dim variants')
        return ('split', '', f'{n} potted cards in family but no clear axis')

    else:
        # packaging/equipment/etc — keep flat or split
        return ('split', '', f'{n} cards in {pack_class} family — split')

family_decisions = {}
for fk, group in work.groupby('family_key'):
    form, axes, notes = decide_family_form(group)
    family_decisions[fk] = {'form': form, 'axes': axes, 'notes': notes,
                            'card_count': len(group),
                            'is_mix': (group['is_mix_candidate']=='yes').any()}

forms = Counter(v['form'] for v in family_decisions.values())
print(f"\nForm distribution: {dict(forms)}")

# ============================================================================
# 6. NEW CATEGORY TREE
# ============================================================================
# Live Odoo already has minimal new tree:
#   Flores Cortadas (287) → Rosa Uniflora (288), Ramas y Follaje (289), Flores Variadas (290)
#   Embalaje (292)
#   Espafloria Internal (291)
#   Deliveries (286)
#
# We extend with:
#   Flores Cortadas / Rosa Ramificada
#   Flores Cortadas / Bambu
#   Flores Cortadas / Bayas y Frutas
#   Plantas en Macetas (NEW root)
#     / Plantas con Flores
#     / Plantas de Follaje
#     / Suculentas y Cactus
#     / Plantas para Terraza
#     / Plantas Aromáticas
#   Embalaje / VBOX / Bolsas / Cintas / Oasis
#   Equipamiento (NEW root)
#   Consumibles (NEW root)
#   Productos Especiales (NEW root)

CATEGORY_TREE = {
    "Flores Cortadas": {
        "_id": 287,
        "Rosa Uniflora": {"_id": 288},
        "Rosa Ramificada": {"_id": "[NEW]"},
        "Flores Variadas": {"_id": 290},
        "Ramas y Follaje": {"_id": 289},
        "Bambu": {"_id": "[NEW]"},
        "Bayas y Frutas": {"_id": "[NEW]"},
    },
    "Plantas en Macetas": {
        "_id": "[NEW]",
        "Plantas con Flores": {"_id": "[NEW]"},
        "Plantas de Follaje": {"_id": "[NEW]"},
        "Suculentas y Cactus": {"_id": "[NEW]"},
        "Plantas para Terraza": {"_id": "[NEW]"},
        "Plantas Aromáticas y Frutales": {"_id": "[NEW]"},
        "Plantas Colgantes": {"_id": "[NEW]"},
    },
    "Embalaje": {
        "_id": 292,
        "VBOX": {"_id": "[NEW]"},
        "Bolsas": {"_id": "[NEW]"},
        "Cintas": {"_id": "[NEW]"},
        "Oasis y Esponjas": {"_id": "[NEW]"},
        "Tarjetas": {"_id": "[NEW]"},
    },
    "Equipamiento": {"_id": "[NEW]"},
    "Consumibles": {"_id": "[NEW]"},
    "Productos Especiales": {"_id": "[NEW]"},
    "Deliveries": {"_id": 286},
    "Espafloria Internal": {"_id": 291},
}

def map_to_new_categ(row):
    """Map a card to (new categ path).
    Logic priority: (1) genus-based lookup for cut flowers — Rosa→Rosa Uniflora,
    others→by sub_categ; (2) sub_categ heuristics; (3) fallback Flores Variadas."""
    pack = row['pack_class']
    sub = str(row.get('sub_categ', '')).upper()
    name = str(row.get('name', '')).upper()
    genus = str(row.get('proposed_genus', '')).replace('Genus:', '').strip()

    # Genuses that are foliage / branches (route to Ramas y Follaje regardless of audit sub)
    FOLLAJE_GENUSES = {'Eucalyptus','Skimmia','Genista','Acacia','Hedera','Ruscus',
                       'Pittosporum','Salal','Olivo','Olive','Pinus','Bambusa','Cupressus',
                       'Aspidistra','Ilex','Pistacho','Pistacia','Dichondra','Helechos',
                       'Gypsophila'}
    # Genuses that are berries/fruits
    BAYAS_GENUSES = {'Hypericum','Vaccinium','Ilex','Citrus'}
    # Rosa
    ROSA_GENUSES = {'Rosa'}

    if pack == 'cut':
        if genus in ROSA_GENUSES:
            # ROSA RAMIFICADA in name → branched
            if 'RAMIFICADA' in name or 'RAMI' in name or 'SPRAY' in name:
                return "Flores Cortadas / Rosa Ramificada"
            return "Flores Cortadas / Rosa Uniflora"
        if 'ROSA RAMIFICADA' in sub:
            return "Flores Cortadas / Rosa Ramificada"
        if genus in FOLLAJE_GENUSES or genus == 'Bambusa':
            if genus == 'Bambusa':
                return "Flores Cortadas / Bambu"
            return "Flores Cortadas / Ramas y Follaje"
        if genus in BAYAS_GENUSES:
            return "Flores Cortadas / Bayas y Frutas"
        if 'BAMBU' in sub:
            return "Flores Cortadas / Bambu"
        if 'BAYAS' in sub or 'FRUTAS' in sub:
            return "Flores Cortadas / Bayas y Frutas"
        if 'RAMAS' in sub or 'CONIFERAS' in sub:
            return "Flores Cortadas / Ramas y Follaje"
        # Default for cut: Flores Variadas (HORTENSIA, ASTILBE, PHALAENOPSIS as cut etc)
        return "Flores Cortadas / Flores Variadas"
    elif pack == 'potted':
        if 'PLANTAS DE FOLLAJE' in sub:
            return "Plantas en Macetas / Plantas de Follaje"
        if 'PLANTAS CON FLORES' in sub or 'PLANTAS NAVIDEÑAS' in sub or 'PLANTAS BULBOSAS' in sub:
            return "Plantas en Macetas / Plantas con Flores"
        if 'SUCULENTAS' in sub or 'CACTUS' in sub:
            return "Plantas en Macetas / Suculentas y Cactus"
        if 'PLANTAS PARA TERRAZA' in sub:
            return "Plantas en Macetas / Plantas para Terraza"
        if 'PLANTAS AROMÁTICAS' in sub or 'PLANTAS FRUTALES' in sub:
            return "Plantas en Macetas / Plantas Aromáticas y Frutales"
        if 'PLANTAS COLGANTES' in sub or 'PLANTAS AÉREAS' in sub:
            return "Plantas en Macetas / Plantas Colgantes"
        return "Plantas en Macetas / Plantas de Follaje"
    elif pack == 'packaging':
        if 'VBOX' in sub:
            return "Embalaje / VBOX"
        if 'BOLSAS' in sub:
            return "Embalaje / Bolsas"
        if 'CINTAS' in sub:
            return "Embalaje / Cintas"
        if 'OASIS' in sub:
            return "Embalaje / Oasis y Esponjas"
        if 'TARJETAS' in sub:
            return "Embalaje / Tarjetas"
        return "Embalaje"
    elif pack == 'equipment':
        return "Equipamiento"
    elif pack == 'consumable':
        return "Consumibles"
    elif pack == 'special':
        return "Productos Especiales"
    elif pack == 'decoration':
        return "Productos Especiales"  # 1 used decoration card — folds in
    return "Productos Especiales"

work['new_categ_path'] = work.apply(map_to_new_categ, axis=1)

# ============================================================================
# 7. POS CATEGORY MAPPING
# ============================================================================

def map_to_pos_categ(row):
    """Map to themed POS tab."""
    pack = row['pack_class']
    genus = str(row.get('proposed_genus', '')).replace('Genus:', '')
    sub = str(row.get('sub_categ', ''))
    if genus == 'Rosa':
        return "🌹 Rosas"
    if pack == 'cut' and ('RAMAS' in sub or 'CONIFERAS' in sub or 'BAMBU' in sub):
        return "🌿 Verde y Ramas"
    if pack == 'cut':
        return "💐 Flores Cortadas"
    if pack == 'potted':
        return "🪴 Plantas en Macetas"
    if pack == 'packaging':
        return "📦 Embalaje"
    if pack == 'equipment':
        return "🛠️ Equipamiento"
    if pack == 'consumable':
        return "🧰 Consumibles"
    if pack == 'special':
        return "⚙️ Servicios"
    return "⚙️ Servicios"

work['new_pos_categ_path'] = work.apply(map_to_pos_categ, axis=1)

# ============================================================================
# 8. NEW NAME, TAGS, PRICES
# ============================================================================

def make_new_name(row, family_form):
    """Make new template name in Spanish, no emoji."""
    genus = str(row.get('proposed_genus', '')).replace('Genus:', '')
    variety = str(row.get('proposed_variety', '')).replace('Variety:', '')
    is_mix = row.get('is_mix_candidate') == 'yes'
    name = str(row.get('name', ''))

    # Strip emoji prefix
    clean = re.sub(r'^[🚫🚧🟠⛔ ]+', '', name).strip()
    # Strip trailing " - flor" / " - rama" — variant form will take care
    clean_no_suffix = re.sub(r'\s*-\s*(flor|rama|ramo|tallo)\b.*$', '', clean, flags=re.I)

    # Drop placeholder "nan"
    if variety in ('nan', 'None'):
        variety = ''
    if genus in ('nan', 'NO_GENUS', 'None'):
        genus = ''

    if family_form == 'flat':
        return clean_no_suffix or f"{genus} {variety}".strip()

    # multivariant — name is genus-variety without size
    if genus:
        # Capitalize properly
        g = genus[0].upper() + genus[1:].lower() if genus.isupper() else genus
        if variety:
            return f"{g} {variety}".strip()
        return g
    return clean_no_suffix or clean


def collect_tags(row):
    """Build clean tag list (no prefix)."""
    tags = []
    g = str(row.get('proposed_genus', '')).replace('Genus:', '').strip()
    v = str(row.get('proposed_variety', '')).replace('Variety:', '').strip()
    o = str(row.get('proposed_origin', '')).replace('Origin:', '').strip()
    t = str(row.get('proposed_treatment', '')).replace('Treatment:', '').strip()
    cc = str(row.get('proposed_color_tags', ''))
    mt = str(row.get('proposed_mix_tier', '')).replace('MixTier:', '').strip()
    pm = str(row.get('proposed_pack_mode', '')).replace('PackMode:', '').strip()
    light = str(row.get('proposed_light', '')).replace('Light:', '').strip()

    if g and g not in ('nan', 'NO_GENUS', ''):
        # Capitalize Latin name
        tags.append(g[0].upper() + g[1:].lower() if g.isupper() else g)
    if v and v not in ('nan', ''):
        tags.append(v)
    if o and o not in ('nan', ''):
        tags.append(o)
    if t and t not in ('nan', ''):
        tags.append(t)
    if cc and cc != 'nan':
        for c in cc.split(','):
            c2 = c.strip().replace('Color:', '').strip()
            if c2:
                tags.append(c2)
    if mt and mt not in ('nan', ''):
        tags.append(f"mix-{mt}")
    if light and light not in ('nan', ''):
        tags.append(light)
    return [x for x in tags if x and x != 'nan']


def proposed_price(row):
    """Get proposed list price + status."""
    h = row.get('holded_list_price_subtotal')
    o = row.get('list_price')
    cost = row.get('last_supplier_price') or row.get('standard_price')

    if pd.notna(h) and h > 0:
        price = h
    elif pd.notna(o) and o > 0:
        price = o
    else:
        # No price → x3 cost placeholder
        if pd.notna(cost) and cost > 0:
            return cost * 3, 'new_x3_placeholder'
        return None, 'new_x3_placeholder'

    # Calculate margin status (retail florist margins typically 2-5x normal, >8x rare)
    if pd.notna(cost) and cost > 0:
        margin = price / cost
        if margin >= 8:
            status = 'review_too_expensive'
        elif margin < 1.5:
            status = 'review_too_cheap'
        elif margin >= 2:
            status = 'accept_old_ok'
        else:
            status = 'review_too_cheap'  # 1.5-2x is borderline cheap
    else:
        status = 'accept_old_ok'  # no cost → just accept Holded value
    return price, status


# ============================================================================
# 9. BUILD per-card migration_action
# ============================================================================

work['family_form'] = work['family_key'].map(lambda fk: family_decisions[fk]['form'])

new_template_assignments = {}  # family_key -> new template id

next_id = 1
for fk, dec in family_decisions.items():
    if dec['form'] in ('flat', '1-axis', '2-axis'):
        new_template_assignments[fk] = f"NEW-{next_id:03d}"
        next_id += 1
    # 'split' → each card becomes its own NEW-

# Per-card final mapping
old_to_new_rows = []
for idx, row in work.iterrows():
    fk = row['family_key']
    dec = family_decisions[fk]

    if dec['form'] == 'split':
        new_tmpl_id = f"NEW-{next_id:03d}"
        next_id += 1
        action = 'flat-migrate'
        is_multi = False
    elif dec['form'] == 'flat':
        new_tmpl_id = new_template_assignments[fk]
        action = 'flat-migrate'
        is_multi = False
    else:
        new_tmpl_id = new_template_assignments[fk]
        action = 'merge-to-multivariant'
        is_multi = True

    new_name = make_new_name(row, dec['form'])
    tags = collect_tags(row)
    price, price_status = proposed_price(row)
    pack = row['pack_class']

    # bill control
    if pack in ('cut', 'potted'):
        bill_control = 'purchase'
    else:
        bill_control = 'receive'

    # Variant attribute summary
    if dec['form'] == 'flat' or dec['form'] == 'split':
        var_attrs = ''
    else:
        # The card's specific variant value
        if pack == 'cut' and pd.notna(row.get('proposed_variant_length_cm')):
            var_attrs = f"Длина: {int(row['proposed_variant_length_cm'])}"
        elif pack == 'potted' and pd.notna(row.get('proposed_variant_pot_size_cm')):
            var_attrs = f"Горшок: {int(row['proposed_variant_pot_size_cm'])}"
        else:
            var_attrs = '?'
        # MIX tier as 2nd axis if applicable
        if dec['is_mix'] and pd.notna(row.get('proposed_mix_tier')):
            tier = str(row['proposed_mix_tier']).replace('MixTier:', '')
            if var_attrs:
                var_attrs += f", MIX Tier: {tier}"
            else:
                var_attrs = f"MIX Tier: {tier}"

    # Confidence
    conf = row.get('confidence', 'medium')
    if 'multi_length_conflict' in str(row.get('a3_red_flags', '')):
        conf_final = 'low' if conf == 'high' else 'medium'
        notes = f"multi_length_conflict — supplier evidence shows multiple lengths, owner verify"
    elif row.get('is_mix_candidate') == 'yes':
        notes = f"mix-tier={str(row.get('proposed_mix_tier','')).replace('MixTier:','')}"
        conf_final = conf
    elif dec['form'] == 'split':
        notes = f"split from {dec['card_count']}-card family — kept separate"
        conf_final = 'medium'
    else:
        notes = ''
        conf_final = conf

    old_to_new_rows.append({
        'old_template_id': row.get('odoo_id'),
        'old_name': row.get('name'),
        'old_default_code': row.get('default_code'),
        'old_barcode': row.get('default_code'),  # barcode often == default_code in this set
        'old_categ_id': row.get('sub_categ'),
        'old_list_price': row.get('list_price'),
        'holded_price_subtotal': row.get('holded_list_price_subtotal'),
        'holded_stock': row.get('holded_stock'),
        'pedido_lines_count_2026': row.get('pedido_lines_count_2026'),
        'total_qty_purchased_2026': row.get('total_qty_purchased_2026'),
        'migration_action': action,
        'new_template_id': new_tmpl_id,
        'new_template_name': new_name,
        'new_default_code': row.get('default_code'),
        'new_barcode': row.get('default_code'),
        'new_categ_path': row.get('new_categ_path'),
        'new_pos_categ_path': row.get('new_pos_categ_path'),
        'new_variant_attributes': var_attrs,
        'new_tags': ', '.join(tags),
        'proposed_list_price': price,
        'proposed_cost': row.get('last_supplier_price') or row.get('standard_price'),
        'price_review_status': price_status,
        'is_mix_candidate': row.get('is_mix_candidate'),
        'mix_tier': str(row.get('proposed_mix_tier','')).replace('MixTier:','') if pd.notna(row.get('proposed_mix_tier')) else '',
        'bill_control': bill_control,
        'family_key': fk,
        'family_form': dec['form'],
        'family_card_count': dec['card_count'],
        'confidence': conf_final,
        'notes': notes,
    })

old_to_new = pd.DataFrame(old_to_new_rows)
print(f"\nold_to_new built: {len(old_to_new)} rows")

# ============================================================================
# 10. NEW TEMPLATES SHEET
# ============================================================================

new_tmpl_rows = []
# Group by new_template_id
for new_tmpl_id, tmpl_grp in old_to_new.groupby('new_template_id'):
    first = tmpl_grp.iloc[0]
    fk = first['family_key']
    dec = family_decisions[fk]
    is_mv = dec['form'] in ('1-axis', '2-axis')
    n_cards = len(tmpl_grp)

    # Determine template name:
    # - flat (1 card): use that card's new name
    # - multivariant (multi-card or single with length variants): use Genus only
    if is_mv and n_cards > 1:
        # Multi-card multivariant — use Genus + most common variety (or just Genus)
        genus_str = first['family_key'].split('::')[0]
        if genus_str.startswith('NO_GENUS'):
            tmpl_name = first['new_template_name']
        else:
            # Capitalize genus properly
            g = genus_str[0].upper() + genus_str[1:].lower() if genus_str.isupper() else genus_str
            # If all cards share the same variety, append it; else just genus
            varieties = tmpl_grp['new_template_name'].apply(lambda n: ' '.join(n.split()[1:]) if len(n.split()) > 1 else '').unique()
            if len(varieties) == 1 and varieties[0]:
                tmpl_name = f"{g} {varieties[0]}"
            else:
                tmpl_name = g
    else:
        tmpl_name = first['new_template_name']

    # All tags union
    all_tags = set()
    for t in tmpl_grp['new_tags']:
        for x in str(t).split(','):
            x = x.strip()
            if x:
                all_tags.add(x)

    # Categ: pick majority categ across cards (for same template)
    categs = tmpl_grp['new_categ_path'].value_counts()
    categ_path = categs.idxmax() if len(categs) else first['new_categ_path']
    pos_categ = tmpl_grp['new_pos_categ_path'].value_counts().idxmax() if len(tmpl_grp) else first['new_pos_categ_path']

    # Variant attribute lines compactly
    attr_text = dec['axes'] if is_mv else ''

    avg_price = tmpl_grp['proposed_list_price'].dropna().median()
    avg_cost = tmpl_grp['proposed_cost'].dropna().median()

    # is_mix should be true only if any card is mix
    any_mix = (tmpl_grp['is_mix_candidate']=='yes').any()

    # Confidence: lowest among children
    conf_levels = {'low': 0, 'medium': 1, 'high': 2}
    min_conf = min((conf_levels.get(c, 1) for c in tmpl_grp['confidence']), default=1)
    conf_label = {0: 'low', 1: 'medium', 2: 'high'}[min_conf]

    new_tmpl_rows.append({
        'new_template_id': new_tmpl_id,
        'name': tmpl_name,
        'categ_path': categ_path,
        'pos_categ_path': pos_categ,
        'variant_attribute_lines': attr_text,
        'tags': ', '.join(sorted(all_tags)),
        'proposed_list_price': avg_price,
        'proposed_cost': avg_cost,
        'donor_cards_count': n_cards,
        'is_multivariant': 'yes' if is_mv else 'no',
        'is_mix': 'yes' if any_mix else 'no',
        'bill_control': first['bill_control'],
        'confidence': conf_label,
        'notes': dec['notes'],
    })

new_tmpl_df = pd.DataFrame(new_tmpl_rows)
print(f"new_templates: {len(new_tmpl_df)}")

# ============================================================================
# 11. ARCHIVE CANDIDATES
# ============================================================================

# All non-used cards
not_used = audit[audit['был_в_закупках_2026']!='yes'].copy()
print(f"archive candidates: {len(not_used)}")

def archive_reason(row):
    if pd.isna(row.get('top_supplier_codigo')) and pd.isna(row.get('pedido_lines_count_2026')):
        return 'orphan_no_si_no_pedido'
    sub = str(row.get('sub_categ', '')).upper()
    if 'NAVIDEÑO' in sub or 'NAVIDAD' in sub:
        return 'seasonal_dormant'
    if pd.notna(row.get('supplierinfo_count')) and row.get('supplierinfo_count', 0) > 0:
        return 'manual_review_needed'  # has SI but not used 2026
    return 'not_used_in_2026'

def seasonal_window(row):
    sub = str(row.get('sub_categ', '')).upper()
    name = str(row.get('name', '')).upper()
    if 'NAVIDEÑ' in sub or 'NAVIDAD' in sub or 'NAVIDA' in name:
        return 'Christmas (Nov-Dec)'
    if 'VALENTI' in name:
        return 'Valentine (Feb)'
    if 'HALLOWEEN' in name:
        return 'Halloween (Oct)'
    if 'MADRE' in name or 'MOTHERS' in name:
        return 'Mothers Day (May)'
    return ''

archive_rows = []
for _, row in not_used.iterrows():
    archive_rows.append({
        'old_template_id': row.get('odoo_id'),
        'name': row.get('name'),
        'default_code': row.get('default_code'),
        'categ_id': row.get('sub_categ'),
        'top_categ': row.get('top_categ'),
        'archive_reason': archive_reason(row),
        'seasonal_window': seasonal_window(row),
        'has_supplierinfo': 'yes' if (row.get('supplierinfo_count', 0) and row.get('supplierinfo_count', 0) > 0) else 'no',
    })
archive_df = pd.DataFrame(archive_rows)

# ============================================================================
# 12. WRITE migration_map_2026-05-10.xlsx
# ============================================================================

out_path = os.path.join(BASE, 'migration_map_2026-05-10.xlsx')
with pd.ExcelWriter(out_path, engine='openpyxl') as wr:
    old_to_new.to_excel(wr, sheet_name='old_to_new', index=False)
    new_tmpl_df.to_excel(wr, sheet_name='new_templates', index=False)
    archive_df.to_excel(wr, sheet_name='archive_candidates', index=False)
print(f"\nwrote {out_path}")

# ============================================================================
# 13. SUMMARY for markdown doc
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY (for markdown design doc)")
print("=" * 70)

# Form distribution
print(f"\nFamilies form breakdown:")
form_count = Counter(d['form'] for d in family_decisions.values())
for f, n in form_count.most_common():
    print(f"  {f}: {n}")

print(f"\nNew templates total: {len(new_tmpl_df)}")
print(f"  Multivariant: {(new_tmpl_df['is_multivariant']=='yes').sum()}")
print(f"  MIX templates: {(new_tmpl_df['is_mix']=='yes').sum()}")

# MIX-tier breakdown
mix_cards = old_to_new[old_to_new['is_mix_candidate']=='yes']
print(f"\nMIX-cards: {len(mix_cards)}")
print(mix_cards['mix_tier'].value_counts())

# Price status
print(f"\nPrice review status:")
print(old_to_new['price_review_status'].value_counts())

# Confidence
print(f"\nConfidence:")
print(old_to_new['confidence'].value_counts())

# Top-30 families by pedido_lines
print(f"\nTop-30 families by pedido_lines_count (sum):")
top_fam = old_to_new.groupby('family_key').agg(
    cards=('old_template_id', 'count'),
    lines=('pedido_lines_count_2026', 'sum'),
    qty=('total_qty_purchased_2026', 'sum'),
    form=('family_form', 'first'),
    name=('new_template_name', 'first'),
).sort_values('lines', ascending=False).head(30)
print(top_fam.to_string())

# Categ counts
print(f"\nNew categ_path distribution:")
print(old_to_new['new_categ_path'].value_counts())

# POS categ counts
print(f"\nNew POS categ distribution:")
print(old_to_new['new_pos_categ_path'].value_counts())

# Archive reasons
print(f"\nArchive reasons:")
print(archive_df['archive_reason'].value_counts())

# Save summary as JSON for the markdown step
summary = {
    'total_used_2026_cards': len(old_to_new),
    'total_new_templates': len(new_tmpl_df),
    'multivariant_templates': int((new_tmpl_df['is_multivariant']=='yes').sum()),
    'mix_templates': int((new_tmpl_df['is_mix']=='yes').sum()),
    'mix_cards_total': len(mix_cards),
    'mix_tier_breakdown': mix_cards['mix_tier'].value_counts().to_dict(),
    'archive_total': len(archive_df),
    'archive_reasons': archive_df['archive_reason'].value_counts().to_dict(),
    'form_breakdown': {f: n for f, n in form_count.items()},
    'price_review_status': old_to_new['price_review_status'].value_counts().to_dict(),
    'confidence': old_to_new['confidence'].value_counts().to_dict(),
    'categ_distribution': old_to_new['new_categ_path'].value_counts().to_dict(),
    'pos_categ_distribution': old_to_new['new_pos_categ_path'].value_counts().to_dict(),
    'top_families': top_fam.reset_index().to_dict('records'),
}
with open(os.path.join(BASE, '_a4_summary.json'), 'w') as f:
    json.dump(summary, f, ensure_ascii=False, default=str, indent=2)
print(f"\nSummary JSON saved to _a4_summary.json")
