#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A3 Attribute Extraction — Espafloria catalog migration.

Reads:
- audit_2026-05-10.xlsx (sheet "карантин_цветы_root" + "твердый_товар"), filter был_в_закупках_2026=yes
- odoo_supplierinfo_2026-05-10.xlsx (Verdnatura product_name + Serviflor x_studio_supplier_identity_key)
- odoo_products_2026-05-10.xlsx (name, default_code, descriptions, x_studio_botanic_name)
- odoo_pedidos_with_lines_2026-05-10.xlsx (Order Lines/Supplier product name, item_comment)

Writes:
- a3_extracted_attributes_2026-05-10.xlsx with 4 sheets:
    1. proposed_per_card  (~420 rows, 26 cols)
    2. proposed_tags_catalog
    3. proposed_variant_attributes
    4. red_flags_summary

NO ODOO WRITES. NO TAG CREATION. Output XLSX only for owner review.
"""

import re
import unicodedata
from collections import Counter, defaultdict
import pandas as pd

BASE = '/Users/andriy/Documents/espafloria.odoo/pedido.files/migration'
OUT = f'{BASE}/a3_extracted_attributes_2026-05-10.xlsx'

# ============================================================
# 1. Source loading
# ============================================================

def load_audit():
    """Return DF of the ~420 candidate cards (used_in_2026=yes), keyed by external_id (odoo_id)."""
    a = pd.read_excel(f'{BASE}/audit_2026-05-10.xlsx', sheet_name='карантин_цветы_root')
    b = pd.read_excel(f'{BASE}/audit_2026-05-10.xlsx', sheet_name='твердый_товар')
    df = pd.concat([a, b], ignore_index=True)
    df = df[df['был_в_закупках_2026'] == 'yes'].copy()
    df['external_id'] = df['odoo_id'].astype(str)
    df['template_id'] = df['odoo_id'].apply(_extract_template_id_or_external)
    return df


def _extract_template_id(s):
    if pd.isna(s):
        return None
    m = re.search(r'product_template_(\d+)_', str(s))
    return int(m.group(1)) if m else None


def _extract_template_id_or_external(s):
    """Use numeric template_id if pattern matches; else fall back to the full external_id string
    so cards using __import__.holded_xxx get a stable join key.
    """
    if pd.isna(s):
        return None
    m = re.search(r'product_template_(\d+)_', str(s))
    if m:
        return int(m.group(1))
    return str(s)  # use full external_id string as the key


def load_supplierinfo(prod_lookup):
    """Return DF with template_id resolved via product_tmpl_id/name → prod table."""
    si = pd.read_excel(f'{BASE}/odoo_supplierinfo_2026-05-10.xlsx')
    si['template_id'] = si['product_tmpl_id/name'].map(prod_lookup)
    return si


def load_products():
    """Return products DF and a name→template_id map (where template_id is the same key
    as audit's external_id-or-numeric).
    """
    p = pd.read_excel(f'{BASE}/odoo_products_2026-05-10.xlsx')
    p['template_id'] = p['id'].apply(_extract_template_id_or_external)
    # Build name and default_code maps
    name_map = dict(zip(p['name'].dropna(), p.loc[p['name'].notna(), 'template_id']))
    dc_map = {str(k): v for k, v in zip(p['default_code'].dropna(),
                                        p.loc[p['default_code'].notna(), 'template_id'])}
    return p, name_map, dc_map


def load_pedidos(name_map):
    """Return pedido lines with template_id from product/name → name_map."""
    p = pd.read_excel(f'{BASE}/odoo_pedidos_with_lines_2026-05-10.xlsx')
    p = p[p['Order Lines/Product/Name'].notna()].copy()
    p['template_id'] = p['Order Lines/Product/Name'].map(name_map)
    return p


# ============================================================
# 2. Constants — vocabulary mappings
# ============================================================

# Spanish/Catalan abbrevs used by Verdnatura/Serviflor → standard genus names
GENUS_ABBREV = {
    'ROS':'Rosa','ROSA':'Rosa','ROSE':'Rosa',
    'TUL':'Tulipa','TULIPAN':'Tulipa','TULIPA':'Tulipa',
    'TULIP':'Tulipa',
    'EUC':'Eucalyptus','EUCALIPTO':'Eucalyptus','EUCALYPTUS':'Eucalyptus',
    'CHRYS':'Chrysanthemum','CRISANTEMO':'Chrysanthemum',
    'CHR':'Chrysanthemum',
    'PHAL':'Phalaenopsis','PHALAENOPSIS':'Phalaenopsis',
    'CL':'Clavel','CLAVEL':'Dianthus','DIANTHUS':'Dianthus',
    'GERB':'Gerbera','GERBERA':'Gerbera',
    'GENISTA':'Genista','GE':'Genista',
    'PANI':'Gypsophila','PANICULATA':'Gypsophila','GYP':'Gypsophila',
    'LISI':'Eustoma','LISIANTHUS':'Eustoma','EUSTOMA':'Eustoma',
    'LIM':'Limonium','LIMONIUM':'Limonium',
    'LILY':'Lilium','LILIUM':'Lilium','LIL':'Lilium',
    'ALSTRO':'Alstroemeria','ALSTROEMERIA':'Alstroemeria',
    'AST':'Aster','ASTER':'Aster','ASTILBE':'Astilbe',
    'RAN':'Ranunculus','RANUNCULUS':'Ranunculus',
    'AGAP':'Agapanthus','AGAPANTHUS':'Agapanthus',
    'IRIS':'Iris','HYDR':'Hydrangea','HORTENSIA':'Hydrangea',
    'AMARYLLIS':'Hippeastrum','HIPP':'Hippeastrum',
    'ANEMONA':'Anemone','ANEMONE':'Anemone',
    'ANT':'Anthurium','ANTHURIUM':'Anthurium',
    'ALLIUM':'Allium',
    'AGER':'Ageratum','AGERATUM':'Ageratum',
    'AMA':'Amaranthus','AMARANTHUS':'Amaranthus',
    'BUP':'Bupleurum','BUPLEURUM':'Bupleurum',
    'CALA':'Calla','CALLA':'Zantedeschia','ZANTEDESCHIA':'Zantedeschia',
    'CAMPA':'Campanula','CAMPANULA':'Campanula',
    'CELOSIA':'Celosia',
    'CHAMEL':'Chamelaucium','CHAMELACIUM':'Chamelaucium','CHAMELAUCIUM':'Chamelaucium',
    'CRASP':'Craspedia','CRASPEDIA':'Craspedia',
    'DELPHI':'Delphinium','DELPHINIUM':'Delphinium','DEL':'Delphinium',
    'EREMURUS':'Eremurus','ERINGIUM':'Eryngium','ERYNGIUM':'Eryngium',
    'GLAD':'Gladiolus','GLADIOLO':'Gladiolus',
    'HEL':'Helianthus','HELIANTHUS':'Helianthus','GIRASOL':'Helianthus',
    'HYP':'Hypericum','HYPERICUM':'Hypericum','HYPOESTES':'Hypoestes',
    'JACINT':'Hyacinthus','JACINTO':'Hyacinthus',
    'LEU':'Leucadendron','LEUCADENDRON':'Leucadendron','LEUCO':'Leucospermum','LEUCOSPERMUM':'Leucospermum',
    'MARG':'Leucanthemum','MARGARITA':'Leucanthemum',
    'MATTHIOLA':'Matthiola','MATT':'Matthiola',
    'MIMOSA':'Acacia','ACACIA':'Acacia',
    'NAR':'Narcissus','NARCISO':'Narcissus','NARCISSUS':'Narcissus',
    'NIGE':'Nigella','NIGELLA':'Nigella',
    'ORN':'Ornithogalum','ORNITHOGALUM':'Ornithogalum',
    'OZOTHAMNUS':'Ozothamnus','OZ':'Ozothamnus',
    'PAEONIA':'Paeonia','PEONIA':'Paeonia',
    'PROTEA':'Protea',
    'SCABI':'Scabiosa','SCABIOSA':'Scabiosa',
    'SOLI':'Solidago','SOLIDAGO':'Solidago',
    'STATICE':'Limonium',
    'STOCK':'Matthiola',
    'TANACETUM':'Tanacetum','TANA':'Tanacetum',
    'TRACHELIUM':'Trachelium','TRACH':'Trachelium',
    'VERONICA':'Veronica','VER':'Veronica',
    'VIBURNUM':'Viburnum',
    'WAX':'Chamelaucium',
    'CERA':'Cera',
    'F':'Cera',
    'SKIMMIA':'Skimmia',
    # Greens / branches
    'PIST':'Pistacia','PISTACIA':'Pistacia',
    'SAL':'Salix','SALIX':'Salix',
    'SAUCE':'Salix',
    'COTONEASTER':'Cotoneaster','COTON':'Cotoneaster',
    'BEAR':'Aspidistra','ASP':'Aspidistra','ASPIDISTRA':'Aspidistra',
    'BAMBU':'Bambusa','BAMBOO':'Bambusa',
    'PALM':'Palma',
    'PHILO':'Philodendron','MONSTERA':'Monstera','SPATH':'Spathiphyllum',
    'SPATHIPHYLLUM':'Spathiphyllum',
    'TALINUM':'Talinum',
    'BAYAS':'Berries',
    # Pots
    'FICUS':'Ficus','PALMERA':'Palma','BONSAI':'Bonsai',
    'KALANCHOE':'Kalanchoe','KAL':'Kalanchoe',
    'ORCH':'Orchidaceae','ORCHIDEA':'Orchidaceae',
    'BROMELIA':'Bromelia',
    'CACTUS':'Cactus',
    'SANS':'Sansevieria','SANSEVIERIA':'Sansevieria',
    'SUC':'Suculenta',
    'FOLLAJE':'Follaje',
    'CIPRES':'Cupressus','CYPRESS':'Cupressus','CIP':'Cupressus',
    'PINO':'Pinus','ABETO':'Abies',
    'POINSETTIA':'Euphorbia','EUPHORBIA':'Euphorbia',
    # Additional plants/cuts seen in catalogue
    'ACHILEA':'Achillea','ACHILLEA':'Achillea',
    'ALOE':'Aloe',
    'ANANAS':'Ananas',
    'AGLAONEMA':'Aglaonema',
    'ANIGOZANTHOS':'Anigozanthos',
    'ANTIRRHINUM':'Antirrhinum','ANT2':'Antirrhinum',
    'ARALIA':'Fatsia','FATSIA':'Fatsia',
    'ASCLEPIA':'Asclepia','ASCLEPIAS':'Asclepias',
    'ASTRANTIA':'Astrantia',
    'BEARGRASS':'Xerophyllum',
    'BOUVARDIA':'Bouvardia',
    'BUXUS':'Buxus','BOJ':'Buxus',
    'CALADIUM':'Caladium',
    'CALATHEA':'Calathea',
    'CAMELIA':'Camellia','CAMELLIA':'Camellia',
    'CHEFLERA':'Schefflera','SCHEFFLERA':'Schefflera',
    'CICLAMEN':'Cyclamen','CYCLAMEN':'Cyclamen',
    'CITRUS':'Citrus',
    'CLEMATIS':'Clematis',
    'COMPOSITION':'Composition',
    'CONIFERA':'Conifera',
    'CORYLLUS':'Corylus','CORYLUS':'Corylus','AVELLANO':'Corylus',
    'CROTON':'Codiaeum','CODIAEUM':'Codiaeum',
    'CYMBIDIUM':'Cymbidium',
    'CRASULA':'Crassula','CRASSULA':'Crassula',
    'DENDROBIUM':'Dendrobium','DEN':'Dendrobium',
    'DIANTHUS':'Dianthus',
    'DIEFFENBACHIA':'Dieffenbachia',
    'DRACAENA':'Dracaena','DRECENA':'Dracaena','DRACENA':'Dracaena',
    'EQUISETUM':'Equisetum','BAMBU JAPONES':'Equisetum',
    'EREMOPHILA':'Eremophila',
    'ESPARRAGUERA':'Asparagus','ASPARAGUS':'Asparagus','ESP':'Asparagus',
    'FRESIA':'Freesia','FREESIA':'Freesia',
    'GALAX':'Galax','GLAMELIA':'Glamelia',
    'GAULTHERIA':'Gaultheria',
    'GLOXINIA':'Sinningia','SINNINGIA':'Sinningia',
    'GUZMANIA':'Guzmania',
    'HEDERA':'Hedera','HIEDRA':'Hedera',
    'HELLEBORUS':'Helleborus','HELEB':'Helleborus','ROSA NAVIDAD':'Helleborus',
    'HOSTA':'Hosta',
    'HOWEA':'Howea','KENTIA':'Howea',
    'HOYA':'Hoya',
    'JADE':'Crassula',
    'JATROPHA':'Jatropha',
    'KOLAR':'Kolar',
    'LATHYRUS':'Lathyrus','GUISANTE':'Lathyrus',
    'LAUREL':'Laurus',
    'LECHUZA':'Lechuza',
    'LEUCANTHEMUM':'Leucanthemum',
    'LIRIO':'Iris','LIRIO PASCUA':'Iris',
    'LOTUS':'Lotus',
    'LUNARIA':'Lunaria',
    'MARANTA':'Maranta',
    'MIKADO':'Mikado',
    'MIRTUS':'Myrtus','MYRTUS':'Myrtus',
    'MUEHLENBECKIA':'Muehlenbeckia',
    'MURRAYA':'Murraya','NARANJO JAZMIN':'Murraya',
    'NEPHROLEPIS':'Nephrolepis','HELECHO':'Nephrolepis','HELECHA':'Nephrolepis',
    'NERTERA':'Nertera',
    'OLIVO':'Olea','OLIVA':'Olea',
    'ORQUIDEA':'Orchidaceae','ORCHID':'Orchidaceae',
    'PACHIRA':'Pachira',
    'PEPEROMIA':'Peperomia',
    'PHILODENDRON':'Philodendron',
    'PILEA':'Pilea',
    'PHOENIX':'Phoenix',
    'PICUS':'Ficus',
    'PHLOX':'Phlox',
    'PIMIENTA':'Capsicum','CAPSICUM':'Capsicum',
    'PITTOSPORUM':'Pittosporum',
    'PLUMOSO':'Asparagus',
    'PODOCARPUS':'Podocarpus',
    'POLYSCIAS':'Polyscias',
    'PORTULACA':'Portulaca',
    'POTHOS':'Epipremnum','EPIPREMNUM':'Epipremnum',
    'PRIMULA':'Primula',
    'RAFIS':'Rhapis','RHAPIS':'Rhapis',
    'RHIPSALIS':'Rhipsalis',
    'ROBLE':'Quercus',
    'ROSA NAVIDAD':'Helleborus',
    'ROSCOEA':'Roscoea',
    'RUBUS':'Rubus','MORA':'Rubus','ZARZA':'Rubus',
    'SAGO':'Cycas','CYCAS':'Cycas',
    'SANDERSONIA':'Sandersonia',
    'SARRACENIA':'Sarracenia',
    'SAUCO':'Sambucus','SAMBUCUS':'Sambucus',
    'SEDUM':'Sedum',
    'SENECIO':'Senecio',
    'SOL':'Helianthus',
    'STRELITZIA':'Strelitzia',
    'SUAEDA':'Suaeda',
    'SYNGONIUM':'Syngonium',
    'TAPIOCA':'Manihot',
    'TILANDSIA':'Tillandsia','TILLANDSIA':'Tillandsia',
    'TRADESCANTIA':'Tradescantia',
    'TUYA':'Thuja','THUJA':'Thuja','TUJA':'Thuja',
    'VANDA':'Vanda',
    'VINCA':'Vinca',
    'WIRRA':'Wirra',
    'YUCA':'Yucca','YUCCA':'Yucca',
    'ZAMIA':'Zamia','ZZ':'Zamioculcas','ZAMIOCULCAS':'Zamioculcas',
    'ZINNIA':'Zinnia',
    'BAY':'Laurus',
    'BERZOS':'Erica','ERICA':'Erica','BREZO':'Erica',
    'BAMBOO LUCKY':'Dracaena',
    'ALHELI':'Matthiola','ALHELÍ':'Matthiola',
}

# Spanish color words → standard tag
COLOR_MAP = {
    'rojo':'rojo','rojos':'rojo','red':'rojo',
    'blanco':'blanco','blancos':'blanco','white':'blanco','wi':'blanco',
    'amarillo':'amarillo','yellow':'amarillo','ge':'amarillo','geel':'amarillo',
    'naranja':'naranja','orange':'naranja','or':'naranja',
    'rosa':'rosa','rosado':'rosa','pink':'rosa','ro':'rosa','pi':'rosa',
    'morado':'morado','purpura':'morado','purple':'morado','vi':'morado','violeta':'morado',
    'lila':'lila','lavanda':'lila','lavender':'lila','la':'lila',
    'azul':'azul','blue':'azul','bl':'azul',
    'verde':'verde','green':'verde','gr':'verde',
    'salmon':'salmon','sa':'salmon','salmón':'salmon',
    'crema':'crema','cream':'crema','beige':'crema','crm':'crema',
    'negro':'negro','black':'negro',
    'marron':'marron','brown':'marron','marrón':'marron','br':'marron',
    'matizado':'matizado','mixed':'mix','mix':'mix','mx':'mix','vario':'mix',
    'multicolor':'mix','bicolor':'mix','bicolour':'mix',
    'fucsia':'fucsia','fuchsia':'fucsia','fu':'fucsia',
    'champagne':'champagne','champan':'champagne',
    'burdeos':'burdeos','burgundy':'burdeos',
}

# Origin codes (Verdnatura uses 2-letter ISO + Spanish names)
ORIGIN_MAP = {
    'NL':'Holland','HOLANDA':'Holland','HOLLAND':'Holland','NETHERLANDS':'Holland',
    'EC':'Ecuador','ECUADOR':'Ecuador',
    'KE':'Kenya','KENYA':'Kenya','KENIA':'Kenya',
    'CO':'Colombia','COLOMBIA':'Colombia',
    'ES':'Spain','ESPAÑA':'Spain','ESPANA':'Spain','SPAIN':'Spain',
    'IT':'Italy','ITALIA':'Italy',
    'ZA':'South Africa','SUDAFRICA':'South Africa','SOUTH AFRICA':'South Africa',
    'ZW':'Zimbabwe','ZIMBABWE':'Zimbabwe',
    'ET':'Ethiopia','ETHIOPIA':'Ethiopia',
    'IL':'Israel','ISRAEL':'Israel',
    'TR':'Turkey','TURQUIA':'Turkey',
    'PT':'Portugal','PORTUGAL':'Portugal',
    'FR':'France','FRANCIA':'France',
    'DE':'Germany','ALEMANIA':'Germany',
    'CR':'Costa Rica','COSTA RICA':'Costa Rica',
    'EG':'Egypt','EGIPTO':'Egypt',
    'TH':'Thailand','TAILANDIA':'Thailand',
    'TZ':'Tanzania',
}

TREATMENT_KEYWORDS = {
    'teñido':'teñido','tenido':'teñido','dyed':'teñido',
    'preservada':'preservada','preserved':'preservada',
    'liofilizada':'liofilizada','lyophilized':'liofilizada',
    'seca':'seca','seco':'seca','dry':'seca','dried':'seca',
    'natural':'natural',
    'estabilizada':'estabilizada','estabilizado':'estabilizada','stabilized':'estabilizada',
    'pintado':'pintado','pintada':'pintado','painted':'pintado',
}


# ============================================================
# 3. Parsing primitives
# ============================================================

def _norm(s):
    if pd.isna(s):
        return ''
    s = str(s).strip()
    return s


def _norm_low(s):
    return _norm(s).lower()


def parse_verdnatura_name(name):
    """Verdnatura product_name → dict of extracted fields.
    Examples:
      '032 Mascarell Teñido (Santa Dorotea EXPORT) COLOR Verde ALTURA 70 cm'
      'CL Peach FCY (Aposentos) COLOR Salmón ALTURA 60 cm'
      'Esponja Pastilla Seco (Oasis) | DIMENSIONES 23 x 11 | ... | COLOR Gris | PACK=20'
    """
    out = {
        'genus': None, 'variety': None, 'origin': None, 'color': None,
        'length_cm': None, 'pot_size_cm': None, 'pack_units': None, 'pack_mode': None,
        'treatment': None,
    }
    if not name:
        return out
    s = str(name)

    # COLOR <word>
    m = re.search(r'\bCOLOR\s+([\w/áéíóúñü]+(?:\s*/\s*[\w/áéíóúñü]+)?)', s, re.IGNORECASE)
    if m:
        cval = m.group(1).strip().split('/')[0]  # take first if "Rojo/Blanco"
        cnorm = COLOR_MAP.get(cval.lower())
        if cnorm:
            out['color'] = cnorm

    # ALTURA NN cm
    m = re.search(r'\bALTURA\s+(\d{2,3})\s*cm\b', s, re.IGNORECASE)
    if m:
        out['length_cm'] = int(m.group(1))

    # PACK=N or PACK N
    m = re.search(r'\bPACK\s*[=:]?\s*(\d+)', s, re.IGNORECASE)
    if m:
        out['pack_units'] = int(m.group(1))

    # Origin parenthetical: "(Santa Dorotea EXPORT)" or "(Marginpar/BF)"
    paren = re.findall(r'\(([^)]+)\)', s)

    # Treatment keywords
    sl = s.lower()
    for kw, tag in TREATMENT_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', sl):
            out['treatment'] = tag
            break

    # Genus heuristic — first token only (avoid mistaking variety/color tokens for genus)
    head = re.split(r'[|()]', s)[0].strip()
    tokens = re.split(r'\s+', head)
    if tokens:
        # Skip leading numeric prefix (like "032 Mascarell")
        first = None
        for tok in tokens:
            tc = re.sub(r'[^\w]', '', tok)
            if not tc:
                continue
            if tc.isdigit():
                continue
            first = tc.upper()
            break
        if first and first in GENUS_ABBREV:
            out['genus'] = GENUS_ABBREV[first]

    # Variety: tokens after genus token, before parenthetical or pipe
    if out['genus']:
        # find genus token in head, take rest
        toks = head.split()
        for i, tok in enumerate(toks):
            tc = re.sub(r'[^\w]', '', tok).upper()
            if tc in GENUS_ABBREV:
                rest = ' '.join(toks[i+1:]).strip()
                # skip leading numbers like "032"
                rest = re.sub(r'^\d+\s+', '', rest)
                if rest:
                    out['variety'] = rest
                break
    else:
        # whole head minus leading numbers might be variety
        rest = re.sub(r'^\d+\s+', '', head)
        if rest:
            out['variety'] = rest

    return out


def parse_serviflor_key(key):
    """Serviflor x_studio_supplier_identity_key → dict.
    Format: SV|ART:<text>|COLOR:<x>|ORIGIN:<x>|GROWER:<x>|POT:<n>|HEIGHT:<n>|QUALITY:<x>|PIECES_UNIT:<n>|UNITS_PER_PACK:<n>|PACK_MODE:<x>|ATTR:<x>
    """
    out = {
        'genus': None, 'variety': None, 'origin': None, 'color': None,
        'length_cm': None, 'pot_size_cm': None, 'pack_units': None, 'pack_mode': None,
        'treatment': None,
    }
    if not key or pd.isna(key):
        return out
    parts = str(key).split('|')
    kv = {}
    for p in parts:
        if ':' in p:
            k, v = p.split(':', 1)
            kv[k.strip().upper()] = v.strip()

    art = kv.get('ART', '')
    if art:
        # First token usually genus
        toks = art.split()
        if toks:
            t0 = toks[0].upper()
            if t0 in GENUS_ABBREV:
                out['genus'] = GENUS_ABBREV[t0]
                # Variety = rest minus optional "LARGE" / "SMALL" / size markers
                rest_toks = toks[1:]
                # Drop known size descriptors that follow genus
                rest_toks = [x for x in rest_toks if x.upper() not in {'LARGE','SMALL','MEDIUM','EXTRA','XL','GRANDE','PEQUEÑO'}]
                if rest_toks:
                    out['variety'] = ' '.join(rest_toks).title()
            else:
                out['variety'] = art.title()

    if kv.get('COLOR'):
        c = kv['COLOR'].lower()
        out['color'] = COLOR_MAP.get(c)

    if kv.get('ORIGIN'):
        o = kv['ORIGIN'].upper()
        out['origin'] = ORIGIN_MAP.get(o)

    h = kv.get('HEIGHT', '').strip()
    if h:
        m = re.match(r'(\d+)', h)
        if m:
            out['length_cm'] = int(m.group(1))

    pot = kv.get('POT', '').strip()
    if pot:
        m = re.match(r'(\d+)', pot)
        if m:
            out['pot_size_cm'] = int(m.group(1))

    upp = kv.get('UNITS_PER_PACK', '').strip()
    if upp:
        try:
            out['pack_units'] = int(float(upp))
        except ValueError:
            pass

    pm = kv.get('PACK_MODE', '').strip().upper()
    if pm:
        out['pack_mode'] = pm.lower()  # 'unit' / 'paquete' / 'manojo'

    return out


def parse_card_name(name):
    """Card name: '🚫 ROSA RED NAOMI - flor', '🚫 EUCALIPTO - Cinerea - rama',
    '🚫 PHALAENOPSIS MIX - planta/28', '🚫 FICUS BONSAI GINSENG (con maceta) - planta/12'
    """
    out = {
        'genus': None, 'variety': None, 'color': None,
        'pot_size_cm': None, 'length_cm': None,
        'product_kind': None,  # flor / rama / planta / accesorio
        'is_mix': False, 'has_decor_pot': False,
    }
    if not name or pd.isna(name):
        return out
    s = str(name)
    # Strip emoji prefixes
    s = re.sub(r'^[^\w]+', '', s).strip()
    # Strip leading bookkeeper prefix "RS " (Roses Sale flag)
    s = re.sub(r'^RS\s+', '', s, flags=re.IGNORECASE)
    # Detect (con maceta)
    if re.search(r'\(con\s+maceta\)', s, re.IGNORECASE):
        out['has_decor_pot'] = True

    # Detect MIX
    if re.search(r'\bMIX\b', s, re.IGNORECASE):
        out['is_mix'] = True

    # Trailing - flor/rama/planta/N or - flor or - planta/12
    m = re.search(r'-\s*(flor|rama|planta|hoja|ramo|fruto|baya|maceta)(?:/(\d+))?\s*$', s, re.IGNORECASE)
    if m:
        out['product_kind'] = m.group(1).lower()
        if m.group(2):
            n = int(m.group(2))
            if out['product_kind'] in ('planta','maceta'):
                out['pot_size_cm'] = n
            else:
                out['length_cm'] = n
        s = s[:m.start()].strip().rstrip('-').strip()

    # Now s is "ROSA RED NAOMI" or "EUCALIPTO - Cinerea" or "PHALAENOPSIS MIX"
    # Strip [closed] / [archived] markers
    s = re.sub(r'\[(closed|archived|deleted)\]\s*', '', s, flags=re.IGNORECASE).strip()
    # Split by " - "
    segs = [x.strip() for x in re.split(r'\s+-\s+', s) if x.strip()]
    if segs:
        head_toks = segs[0].split()
        if head_toks:
            t0 = re.sub(r'[^\w]', '', head_toks[0]).upper()
            if t0 in GENUS_ABBREV:
                out['genus'] = GENUS_ABBREV[t0]
                rest = ' '.join(head_toks[1:]).strip()
                if rest and rest.upper() != 'MIX':
                    out['variety'] = rest.title()
            else:
                # First token may be genus name itself written out — keep it as fallback genus
                # (will be filled only if no other source resolves it)
                if t0 and t0.isalpha() and len(t0) >= 3:
                    out['genus_fallback'] = t0.title()
                rest = ' '.join(head_toks[1:]).strip()
                if rest and rest.upper() != 'MIX':
                    out['variety'] = rest.title()
                else:
                    out['variety'] = segs[0].title()
        if len(segs) > 1:
            # Could be variety or color
            v2 = segs[1].strip()
            if v2.upper() != 'MIX':
                if not out['variety'] or out['variety'].upper()=='MIX':
                    out['variety'] = v2.title()
                # Check color
                cnorm = COLOR_MAP.get(v2.lower())
                if cnorm:
                    out['color'] = cnorm

    return out


def parse_default_code_for_size(code):
    """e.g. '8400156' is just SKU; sometimes '4741293535133-14' has size suffix in cm."""
    if not code or pd.isna(code):
        return None
    s = str(code)
    m = re.search(r'-V?(\d{1,3})(?:cm)?$', s, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        if 5 <= n <= 200:
            return n
    return None


# ============================================================
# 4. Aggregation per card
# ============================================================

def aggregate_card(card_row, supplierinfos, pedido_lines, products_row):
    """Combine all sources for a single card → proposed attributes."""
    template_id = card_row['template_id']
    name = card_row['name']
    list_price = card_row.get('list_price', 0) or 0

    # Parse card name
    name_parse = parse_card_name(name)

    # Collect supplier sources
    verd_parses = []
    serv_parses = []
    n_verd = 0
    n_serv = 0
    for _, si in supplierinfos.iterrows():
        partner = si.get('partner_id', '')
        pname = si.get('product_name')
        sik = si.get('x_studio_supplier_identity_key')
        if 'VERDNATURA' in str(partner).upper():
            n_verd += 1
            if pname and not pd.isna(pname):
                verd_parses.append(parse_verdnatura_name(pname))
        elif 'SERVIFLOR' in str(partner).upper():
            n_serv += 1
            if sik and not pd.isna(sik):
                serv_parses.append(parse_serviflor_key(sik))

    # Pedido lines: use Order Lines/Supplier product name if we missed in SI
    pedline_parses = []
    n_pedlines = 0
    for _, pl in pedido_lines.iterrows():
        n_pedlines += 1
        spn = pl.get('Order Lines/Supplier product name')
        if spn and not pd.isna(spn):
            pedline_parses.append(parse_verdnatura_name(spn))

    all_parses = verd_parses + serv_parses + pedline_parses
    all_with_name = all_parses + [name_parse]

    # Aggregate per attribute
    def votes(field):
        c = Counter()
        for p in all_with_name:
            v = p.get(field)
            if v:
                c[v] += 1
        return c

    g = votes('genus')
    v = votes('variety')
    o = votes('origin')
    c = votes('color')
    t = votes('treatment')

    # Length cm distribution
    len_c = Counter()
    for p in all_parses:  # exclude name_parse for length, use only suppliers
        x = p.get('length_cm')
        if x:
            len_c[x] += 1
    if not len_c and name_parse.get('length_cm'):
        len_c[name_parse['length_cm']] += 1

    pot_c = Counter()
    for p in all_parses:
        x = p.get('pot_size_cm')
        if x:
            pot_c[x] += 1
    if not pot_c and name_parse.get('pot_size_cm'):
        pot_c[name_parse['pot_size_cm']] += 1

    pack_c = Counter()
    pack_units_c = Counter()
    for p in all_parses:
        if p.get('pack_mode'):
            pack_c[p['pack_mode']] += 1
        if p.get('pack_units'):
            pack_units_c[p['pack_units']] += 1

    # Resolve mode (most common)
    proposed_genus = g.most_common(1)[0][0] if g else None
    proposed_variety = v.most_common(1)[0][0] if v else None
    proposed_origin = o.most_common(1)[0][0] if o else None
    proposed_treatment = t.most_common(1)[0][0] if t else None

    # Fallback: use card-name's first token as genus where dict didn't recognise it.
    # Only for cards that look botanical (have product_kind set or in PLANTAS/FLORES categ).
    if not proposed_genus and name_parse.get('genus_fallback'):
        top_categ = str(card_row.get('top_categ','') or '')
        kind = name_parse.get('product_kind')
        if kind in ('flor','rama','planta','ramo','baya','fruto','hoja','maceta') or \
           'PLANTAS' in top_categ or 'FLORES' in top_categ or 'RAMAS' in top_categ:
            proposed_genus = name_parse['genus_fallback']

    # Color: keep all distinct colors as tag list, but if only 1 distinct, that's the variant
    distinct_colors = sorted(c.keys())
    if 'mix' in distinct_colors:
        distinct_colors = [x for x in distinct_colors if x != 'mix']
    proposed_color_tags = ','.join(distinct_colors) if distinct_colors else ''
    proposed_variant_color = ''
    color_distribution = ','.join(f"{k}:{v}" for k, v in c.most_common())
    if len(distinct_colors) >= 2 and not name_parse.get('is_mix'):
        # Multi-color → variant generating
        proposed_variant_color = '|'.join(distinct_colors)

    # MIX tier — name says MIX or audit flagged is_mix_candidate
    is_mix_cand = name_parse.get('is_mix') or False
    # Cross-check from audit red_flags column (already passed in card_row.get('red_flags') has 'mix_candidate')
    rf = str(card_row.get('red_flags', '') or '')
    if 'mix_candidate' in rf:
        is_mix_cand = True

    proposed_mix_tier = ''
    if is_mix_cand:
        try:
            lp = float(list_price or 0)
        except (ValueError, TypeError):
            lp = 0
        if lp <= 0:
            proposed_mix_tier = 'standard'
        elif lp < 5:
            proposed_mix_tier = 'cheap'
        elif lp < 15:
            proposed_mix_tier = 'standard'
        else:
            proposed_mix_tier = 'premium'

    # Pack mode / units
    proposed_pack_mode = pack_c.most_common(1)[0][0] if pack_c else ''
    proposed_units_per_pack = pack_units_c.most_common(1)[0][0] if pack_units_c else ''

    # Light (only for pots) — heuristic: not extracted from sources here, leave empty
    # category-based seed (PLANTAS DE FOLLAJE → media; SUCULENTAS/CACTUS → sol)
    top_categ = str(card_row.get('top_categ','') or '')
    sub_categ = str(card_row.get('sub_categ','') or '')
    proposed_light = ''
    if 'PLANTAS' in top_categ:
        if 'SUCULENTAS' in sub_categ or 'CACTUS' in sub_categ or 'TERRAZA' in sub_categ:
            proposed_light = 'sol'
        elif 'FOLLAJE' in sub_categ or 'COLGANTES' in sub_categ:
            proposed_light = 'sombra'
        elif 'FLORES' in sub_categ:
            proposed_light = 'media'

    # Variant length / pot size — propose mode
    proposed_variant_length_cm = len_c.most_common(1)[0][0] if len_c else ''
    length_distribution = ','.join(f"{k}:{v}" for k, v in sorted(len_c.items()))
    proposed_variant_pot_size_cm = pot_c.most_common(1)[0][0] if pot_c else ''
    pot_size_distribution = ','.join(f"{k}:{v}" for k, v in sorted(pot_c.items()))

    # Decide which (length OR pot_size) applies for THIS card
    kind = name_parse.get('product_kind')
    if kind in ('planta','maceta','hoja') or 'PLANTAS' in top_categ:
        # Pot card — clear length proposal
        proposed_variant_length_cm = ''
        length_distribution = ''
    elif kind in ('flor','rama','ramo','baya','fruto') or 'FLORES' in top_categ:
        proposed_variant_pot_size_cm = ''
        pot_size_distribution = ''

    # Confidence
    n_sources = n_verd + n_serv + n_pedlines
    if n_sources >= 3 and proposed_genus and proposed_variety:
        confidence = 'high'
    elif n_sources >= 1 and (proposed_genus or proposed_variety):
        confidence = 'medium'
    else:
        confidence = 'low'

    # Source evidence
    evid = []
    if n_verd:
        evid.append(f"verd:{n_verd}×")
    if n_serv:
        evid.append(f"serv:{n_serv}×")
    if n_pedlines:
        evid.append(f"ped:{n_pedlines}×")
    evid.append("name")
    source_evidence = ', '.join(evid)

    # Red flags
    flags = []
    if n_verd + n_serv == 0:
        flags.append('no_supplierinfo')
    if not (verd_parses or serv_parses) and not pedline_parses:
        flags.append('extracted_from_name_only')
    # multi_length only flagged for cuts (where length is the variant axis)
    if proposed_variant_length_cm and len(len_c) >= 3:
        flags.append('multi_length_conflict')
    if proposed_variant_pot_size_cm and len(pot_c) >= 3:
        flags.append('multi_pot_size_conflict')
    if is_mix_cand and not list_price:
        flags.append('mix_tier_arbitrary_no_price')
    # Genus only matters for botanical categories (FLORES, PLANTAS, RAMAS).
    is_botanical = ('PLANTAS' in top_categ or 'FLORES' in top_categ or 'RAMAS' in top_categ
                    or kind in ('flor','rama','planta','ramo','baya','fruto','hoja'))
    if not proposed_genus and is_botanical:
        flags.append('genus_not_resolved')
    if not proposed_variety and is_botanical:
        flags.append('variety_not_resolved')
    if not is_botanical:
        flags.append('hard_good_no_botany')
    red_flags_text = '; '.join(flags)

    # Default code
    default_code = card_row.get('default_code')
    if pd.isna(default_code):
        default_code = ''

    # categ path
    categ_id_path = str(card_row.get('categ_id', '') or '')

    # Existing legacy_botanic_tags (m2m field empty in this export)
    legacy_botanic_tags = ''
    if products_row is not None:
        bn = products_row.get('x_studio_botanic_name/name')
        if bn and not pd.isna(bn):
            legacy_botanic_tags = str(bn)

    return {
        'odoo_template_id': template_id,
        'name': name,
        'default_code': default_code,
        'categ_id_path': categ_id_path,
        'is_used_in_2026': 'yes',
        'is_mix_candidate': 'yes' if is_mix_cand else 'no',
        'legacy_botanic_tags': legacy_botanic_tags,
        'existing_standard_tags': '',
        'proposed_genus': f'Genus:{proposed_genus}' if proposed_genus else '',
        'proposed_variety': f'Variety:{proposed_variety}' if proposed_variety else '',
        'proposed_origin': f'Origin:{proposed_origin}' if proposed_origin else '',
        'proposed_treatment': f'Treatment:{proposed_treatment}' if proposed_treatment else '',
        'proposed_color_tags': ','.join(f'Color:{x}' for x in distinct_colors) if distinct_colors else '',
        'proposed_mix_tier': f'MixTier:{proposed_mix_tier}' if proposed_mix_tier else '',
        'proposed_pack_mode': f'PackMode:{proposed_pack_mode}' if proposed_pack_mode else '',
        'proposed_units_per_pack': proposed_units_per_pack if proposed_units_per_pack else '',
        'proposed_light': f'Light:{proposed_light}' if proposed_light else '',
        'proposed_variant_length_cm': proposed_variant_length_cm,
        'length_distribution': length_distribution,
        'proposed_variant_pot_size_cm': proposed_variant_pot_size_cm,
        'pot_size_distribution': pot_size_distribution,
        'proposed_variant_color': proposed_variant_color,
        'color_distribution': color_distribution,
        'confidence': confidence,
        'source_evidence': source_evidence,
        'red_flags': red_flags_text,
    }


# ============================================================
# 5. Main pipeline
# ============================================================

def main():
    print("Loading data...")
    audit = load_audit()
    print(f"  audit candidates: {len(audit)}")
    products, name_map, dc_map = load_products()
    print(f"  products: {len(products)}")
    # products has template-level rows; build name→template_id from products
    products_by_tmpl = products.drop_duplicates('template_id').set_index('template_id', drop=False)

    # Supplierinfo: join by default_code first (most reliable), fallback to name.
    si = pd.read_excel(f'{BASE}/odoo_supplierinfo_2026-05-10.xlsx')
    si['_dc'] = si['product_tmpl_id/default_code'].astype(str)
    si['template_id'] = si['_dc'].map(dc_map)
    si['template_id'] = si['template_id'].fillna(si['product_tmpl_id/name'].map(name_map))
    print(f"  supplierinfo: {len(si)}, with template_id: {si['template_id'].notna().sum()}")

    pedidos = load_pedidos(name_map)
    print(f"  pedido lines: {len(pedidos)}")

    si_by_tmpl = si.groupby('template_id')
    ped_by_tmpl = pedidos.groupby('template_id')

    print("Aggregating per card...")
    rows = []
    for _, card in audit.iterrows():
        tid = card['template_id']
        if tid is None:
            continue
        try:
            sis = si_by_tmpl.get_group(tid)
        except KeyError:
            sis = si.iloc[0:0]
        try:
            peds = ped_by_tmpl.get_group(tid)
        except KeyError:
            peds = pedidos.iloc[0:0]

        prod_row = None
        if tid in products_by_tmpl.index:
            try:
                prod_row = products_by_tmpl.loc[tid]
                if isinstance(prod_row, pd.DataFrame):
                    prod_row = prod_row.iloc[0]
            except (KeyError, IndexError):
                prod_row = None

        out = aggregate_card(card, sis, peds, prod_row)
        rows.append(out)

    df_out = pd.DataFrame(rows)
    print(f"  rows: {len(df_out)}")

    # ========== Sheet 2: tags catalog ==========
    print("Building tags catalog...")
    tag_counts = Counter()
    tag_category = {}

    def add_tag(t, cat):
        if not t:
            return
        # t may be comma-separated for color tags
        for x in str(t).split(','):
            x = x.strip()
            if not x:
                continue
            tag_counts[x] += 1
            tag_category[x] = cat

    for _, r in df_out.iterrows():
        add_tag(r['proposed_genus'], 'Genus')
        add_tag(r['proposed_variety'], 'Variety')
        add_tag(r['proposed_origin'], 'Origin')
        add_tag(r['proposed_treatment'], 'Treatment')
        add_tag(r['proposed_color_tags'], 'Color')
        add_tag(r['proposed_mix_tier'], 'MixTier')
        add_tag(r['proposed_pack_mode'], 'PackMode')
        add_tag(r['proposed_light'], 'Light')

    # Map color codes to Odoo palette
    color_palette = {
        'rojo':1,'naranja':2,'amarillo':3,'azul':8,'morado':5,'salmon':6,'verde':10,
        'lila':11,'rosa':9,'fucsia':9,'crema':6,'blanco':0,'negro':0,'marron':2,'mix':0,
        'champagne':6,'burdeos':1,
    }

    cat_palette = {
        'Genus':10, 'Variety':4, 'Origin':3, 'Treatment':2,
        'MixTier':5, 'PackMode':7, 'Light':3,
    }

    tags_rows = []
    for tag, cnt in tag_counts.most_common():
        cat = tag_category[tag]
        col = 0
        if cat == 'Color':
            cval = tag.split(':',1)[1] if ':' in tag else tag
            col = color_palette.get(cval.lower(), 0)
        else:
            col = cat_palette.get(cat, 0)
        tags_rows.append({
            'tag_name': tag,
            'category': cat,
            'proposed_color': col,
            'cards_using': cnt,
        })
    tags_df = pd.DataFrame(tags_rows)

    # ========== Sheet 3: variant attributes ==========
    print("Building variant attributes summary...")
    len_values = Counter()
    pot_values = Counter()
    color_values = Counter()
    for _, r in df_out.iterrows():
        if r['proposed_variant_length_cm']:
            len_values[int(r['proposed_variant_length_cm'])] += 1
        if r['proposed_variant_pot_size_cm']:
            pot_values[int(r['proposed_variant_pot_size_cm'])] += 1
        if r['proposed_variant_color']:
            for cv in str(r['proposed_variant_color']).split('|'):
                if cv:
                    color_values[cv] += 1

    var_attr_rows = [
        {
            'attribute_name': 'Длина (см)',
            'distinct_values': ', '.join(f"{k}({v})" for k, v in sorted(len_values.items())),
            'value_count': len(len_values),
            'cards_candidate': sum(len_values.values()),
            'usage_note': 'Создавать при первой multivariant rose-карте (см. plan §A5)',
        },
        {
            'attribute_name': 'Размер горшка (см)',
            'distinct_values': ', '.join(f"{k}({v})" for k, v in sorted(pot_values.items())),
            'value_count': len(pot_values),
            'cards_candidate': sum(pot_values.values()),
            'usage_note': 'Для горшечной (PLANTAS EN MACETAS)',
        },
        {
            'attribute_name': 'Цвет',
            'distinct_values': ', '.join(f"{k}({v})" for k, v in sorted(color_values.items())),
            'value_count': len(color_values),
            'cards_candidate': sum(color_values.values()),
            'usage_note': 'Только где карта объективно multi-color (редко)',
        },
    ]
    var_attr_df = pd.DataFrame(var_attr_rows)

    # ========== Sheet 4: red flags summary ==========
    print("Building red flags summary...")
    flag_counts = Counter()
    flag_examples = defaultdict(list)
    for _, r in df_out.iterrows():
        rf = str(r['red_flags'] or '')
        if rf:
            for f in rf.split(';'):
                f = f.strip()
                if not f:
                    continue
                flag_counts[f] += 1
                if len(flag_examples[f]) < 5:
                    flag_examples[f].append(r['name'])

    rf_rows = []
    for flag, cnt in flag_counts.most_common():
        rf_rows.append({
            'red_flag': flag,
            'count': cnt,
            'top_5_examples': ' | '.join(flag_examples[flag]),
        })
    rf_df = pd.DataFrame(rf_rows)

    # ========== Write XLSX ==========
    print(f"Writing {OUT}...")
    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        df_out.to_excel(w, sheet_name='proposed_per_card', index=False)
        tags_df.to_excel(w, sheet_name='proposed_tags_catalog', index=False)
        var_attr_df.to_excel(w, sheet_name='proposed_variant_attributes', index=False)
        rf_df.to_excel(w, sheet_name='red_flags_summary', index=False)

    # ========== Summary ==========
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Cards processed: {len(df_out)}")
    print()
    print("Tags by category (unique count):")
    cat_counts = Counter()
    for _, r in tags_df.iterrows():
        cat_counts[r['category']] += 1
    for cat, n in cat_counts.most_common():
        print(f"  {cat}: {n}")
    print()
    print(f"Total unique tags: {len(tags_df)}")
    print()
    print("Top-5 red flags:")
    for flag, cnt in flag_counts.most_common(5):
        print(f"  {flag}: {cnt}")
    print()
    print(f"Confidence breakdown:")
    cb = df_out['confidence'].value_counts()
    for k, v in cb.items():
        print(f"  {k}: {v}")
    print()
    print(f"Output: {OUT}")


if __name__ == '__main__':
    main()
