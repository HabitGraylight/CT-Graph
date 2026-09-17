import difflib
import math
import re
import unicodedata
from fractions import Fraction
from .knowledge import INGREDIENTS, AMBIGUOUS, DRINK_ALIASES

def key(text):
    text = unicodedata.normalize('NFKD', unicodedata.normalize('NFKC', str(text))).casefold()
    return re.sub(r'[\s\-’\'·_]', '', ''.join(c for c in text if not unicodedata.combining(c)))

BY_ID = {i['id']: i for i in INGREDIENTS}
ALIASES = {}
for item in INGREDIENTS:
    for alias in [item['id'],item['zh'],item['en'],*item['aliases']]:
        k = key(alias)
        if k in ALIASES and ALIASES[k] != item['id']:
            raise ValueError('Conflicting ingredient alias: ' + alias)
        ALIASES[k] = item['id']
AMBIGUOUS_KEYS = {key(k): v for k,v in AMBIGUOUS.items()}
DRINK_KEYS = {key(alias): name for name,aliases in DRINK_ALIASES.items() for alias in [name,*aliases]}

def resolve(text):
    k = key(text)
    if k in AMBIGUOUS_KEYS:
        return {'status':'ambiguous','input':text,'choices':[BY_ID[x] for x in AMBIGUOUS_KEYS[k]]}
    if k in ALIASES:
        return {'status':'matched','input':text,'ingredient':BY_ID[ALIASES[k]]}
    nearby = difflib.get_close_matches(k, list(ALIASES), n=5, cutoff=.66)
    ids = list(dict.fromkeys(ALIASES[n] for n in nearby))[:3]
    return {'status':'unknown','input':text,'choices':[BY_ID[x] for x in ids]}

def drink_name(name):
    return DRINK_KEYS.get(key(name), name)

UNITS = {'ml':'ml','毫升':'ml','cl':'cl','厘升':'cl','l':'l','升':'l',
         'dash':'dash','dashes':'dash','滴振':'dash','drop':'drop','drops':'drop','滴':'drop',
         'leaf':'leaf','leaves':'leaf','片':'leaf','叶':'leaf','片叶':'leaf',
         'sprig':'sprig','sprigs':'sprig','枝':'sprig','支':'sprig',
         'g':'g','克':'g','tsp':'tsp','茶匙':'tsp','teaspoon':'tsp','teaspoons':'tsp',
         'barspoon':'barspoon','barspoons':'barspoon','吧匙':'barspoon',
         'oz':'oz','盎司':'oz','usfloz':'us_fl_oz','美制液盎司':'us_fl_oz',
         'cube':'cube','cubes':'cube','块':'cube','个':'piece','piece':'piece','pcs':'piece'}
def unit_key(unit):
    return UNITS.get(key(unit), str(unit or '').strip().lower())

def numeric(value):
    if value is None or value == '':
        return None
    if isinstance(value,bool):
        raise ValueError('用量不能是布尔值')
    try:
        bits = str(value).split()
        n = float(sum(Fraction(x) for x in bits)) if len(bits) == 2 else float(Fraction(str(value)))
    except (ValueError,ZeroDivisionError,OverflowError):
        raise ValueError('用量必须是有限正数或分数')
    if not math.isfinite(n) or n <= 0 or n > 10000:
        raise ValueError('单项用量应大于 0 且不超过 10000')
    return n

NUMBER = r'(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)'
UNIT = r'(?:US\s*fl\s*oz|美制液盎司|毫升|厘升|毫?升|片叶|滴振|茶匙|吧匙|盎司|ml|cl|l|dashes|dash|drops|drop|leaves|leaf|sprigs|sprig|bar\s*spoons?|teaspoons?|tsp|oz|g|克|滴|片|叶|枝|支|块|cube|pcs|个)'

def text_parts(text):
    if len(text) > 12000:
        raise ValueError('输入过长，请限制在 12000 字符内')
    return [x.strip() for x in re.split(r'[\n,，;；、]+',text) if x.strip()]

def parse_line(line):
    original = line
    line = unicodedata.normalize('NFKC',line).strip()
    line = re.sub(r'^(?:我有|我的原料是|原料[:：]?|我使用)\s*','',line)
    m = re.match(r'^('+NUMBER+r')\s*('+UNIT+r')\s+(.+)$',line,re.I)
    if m:
        return {'name':m[3].strip(),'amount':m[1],'unit':m[2],'input':original}
    m = re.match(r'^(.+?)\s*[:：]?\s*('+NUMBER+r')\s*('+UNIT+r')$',line,re.I)
    if m:
        return {'name':m[1].strip(),'amount':m[2],'unit':m[3],'input':original}
    # Missing unit is deliberately not inferred as ml.
    m = re.match(r'^(.+?)\s+('+NUMBER+r')$',line)
    if m:
        return {'name':m[1].strip(),'amount':m[2],'unit':'','input':original}
    return {'name':line,'amount':None,'unit':'','input':original}

def parse_items(value):
    if isinstance(value,str):
        value = [parse_line(x) for x in text_parts(value)]
    if not isinstance(value,list) or len(value)>80:
        raise ValueError('原料需要是文字或最多 80 项的列表')
    result = []
    for entry in value:
        if isinstance(entry,str):
            entry = parse_line(entry)
        if not isinstance(entry,dict) or not isinstance(entry.get('name'),str) or not entry['name'].strip():
            raise ValueError('每项原料都需要名称')
        if len(entry['name']) > 200:
            raise ValueError('单个原料名过长')
        r = resolve(entry['name'])
        amount = numeric(entry.get('amount'))
        unit = unit_key(entry.get('unit',''))
        liquid = r['status']=='matched' and not set(r['ingredient']['roles']).intersection({'solid_sweet','fruit','herb','ice','garnish','seasoning'})
        # teaspoon conversion applies to liquids only; bar spoons and oz remain unresolved.
        factor = {'ml':1,'cl':10,'l':1000,'us_fl_oz':29.5735295625}.get(unit)
        if unit=='tsp' and liquid:
            factor=5
        ml = amount * factor if amount is not None and factor is not None and liquid else None
        result.append({**entry,**r,'amount':amount,'unit':unit,'ml':ml})
    return result

def category_id(id):
    """One explicit product-to-type step; preserve spirit style and vermouth distinctions."""
    i = BY_ID[id]
    return i['parent'] if i.get('brand') and i.get('parent') else id
