"""Editable bilingual vocabulary and framework rules. Ratios are design heuristics."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGREDIENTS = []
def ing(id, zh, en, roles, aliases='', parent=None, brand=None, sweetness=1.0, note='', source=None):
    INGREDIENTS.append(dict(id=id, zh=zh, en=en, roles=roles.split(), aliases=[a for a in aliases.split('|') if a],
                            parent=parent, brand=brand, sweetness=sweetness, note=note,
                            source=source or 'data/raw/bar_assistant/files/data/ingredients; editorial bilingual mapping'))

ing('gin','金酒','Gin','base gin','琴酒|杜松子酒|London Dry Gin|伦敦干金酒|Dry Gin')
ing('old_tom_gin','老汤姆金酒','Old Tom Gin','base gin','老汤姆',parent='gin',note='风格通常较柔和偏甜，和伦敦干金酒分别保留。')
ing('vodka','伏特加','Vodka','base vodka')
ing('rum','朗姆酒（未注明类型）','Rum','base rum','兰姆酒',note='未指定白朗姆、陈年或深色类型，完成配方时保留风格差异。')
ing('white_rum','白朗姆酒','White Rum','base rum white_rum','白朗姆|Light rum|White Cuban Ron|Cuban white rum',parent='rum')
ing('aged_rum','陈年朗姆酒','Aged Rum','base rum aged_rum','陈年朗姆|Gold rum|金朗姆',parent='rum')
ing('dark_rum','深色朗姆酒','Dark Rum','base rum dark_rum','黑朗姆|深色朗姆',parent='rum')
ing('jamaican_rum','牙买加朗姆酒','Jamaican Rum','base rum aged_rum','牙买加朗姆',parent='rum')
ing('whiskey','威士忌','Whiskey','base whiskey','Whisky')
ing('bourbon','波本威士忌','Bourbon Whiskey','base whiskey bourbon','波本|波旁|波旁威士忌|Bourbon',parent='whiskey')
ing('rye','黑麦威士忌','Rye Whiskey','base whiskey rye','黑麦|Rye',parent='whiskey')
ing('scotch','苏格兰威士忌','Scotch Whisky','base whiskey scotch','Scotch whiskey|Scotch|苏威',parent='whiskey')
ing('irish','爱尔兰威士忌','Irish Whiskey','base whiskey','爱尔兰威士忌酒',parent='whiskey')
ing('tequila','特基拉','Tequila','base tequila','龙舌兰酒|龙舌兰|Tequila 100% Agave')
ing('tequila_blanco','银特基拉','Tequila Blanco','base tequila','银龙舌兰|白龙舌兰|Silver tequila|Blanco tequila',parent='tequila')
ing('tequila_reposado','金色陈酿特基拉','Tequila Reposado','base tequila','Reposado tequila',parent='tequila')
ing('mezcal','梅斯卡尔','Mezcal','base mezcal','梅兹卡尔|麦斯卡尔')
ing('brandy','白兰地','Brandy','base brandy')
ing('cognac','干邑','Cognac','base brandy cognac','干邑白兰地',parent='brandy')
ing('apple_brandy','苹果白兰地','Apple Brandy','base brandy',parent='brandy')
ing('calvados','卡尔瓦多斯','Calvados','base brandy',parent='apple_brandy')
ing('pisco','皮斯科','Pisco','base brandy')
ing('cachaca','卡莎萨','Cachaça','base cachaca','Cachaca|巴西甘蔗酒')
ing('lemon_juice','柠檬汁','Lemon Juice','acid','鲜柠檬汁|鲜榨柠檬汁|Fresh Lemon Juice|Freshly squeezed lemon juice|Fresh squeezed lemon juice')
ing('lime_juice','青柠汁','Lime Juice','acid','鲜青柠汁|鲜榨青柠汁|莱姆汁|Fresh Lime Juice|Freshly squeezed lime juice|Fresh squeezed lime juice')
ing('grapefruit_juice','西柚汁','Grapefruit Juice','juice','葡萄柚汁|Fresh grapefruit juice',note='酸度和含糖量与柠檬、青柠不同，不自动当作等量酸源。')
ing('orange_juice','橙汁','Orange Juice','juice','鲜橙汁|Fresh orange juice|Freshly squeezed orange juice')
ing('pineapple_juice','菠萝汁','Pineapple Juice','juice tropical','凤梨汁|Fresh pineapple juice')
ing('cranberry_juice','蔓越莓汁','Cranberry Juice','juice','红莓汁')
ing('tomato_juice','番茄汁','Tomato Juice','juice','西红柿汁')
ing('passionfruit_puree','百香果果泥','Passion Fruit Puree','juice tropical','Passionfruit puree|百香果泥')
ing('simple_syrup','原味糖浆','Simple Syrup','syrup sweet','糖浆|单糖浆|普通糖浆|Sugar syrup|1:1糖浆|1:1 simple syrup',note='试配按常见 1:1 糖浆作为参照；糖水比例未明确时，甜度建议仅为起点。')
ing('rich_syrup','浓糖浆 2:1','Rich Syrup','syrup sweet','浓糖浆|2:1糖浆|Rich simple syrup|2:1 simple syrup',sweetness=1.5,note='约按原味糖浆 1.5 倍甜味贡献估算；是可调整启发式，不是密度实测。')
ing('honey_syrup','蜂蜜糖浆','Honey Syrup','syrup sweet','蜂蜜水|蜂蜜糖水',note='蜂蜜兑水比例未知，不能与纯蜂蜜等同。')
ing('agave_syrup','龙舌兰糖浆','Agave Syrup','syrup sweet','Agave nectar|龙舌兰蜜')
ing('demerara_syrup','德梅拉拉糖浆','Demerara Syrup','syrup sweet','红糖糖浆|Demerara sugar syrup')
ing('grenadine','石榴糖浆','Grenadine','syrup sweet','红石榴糖浆|Grenadine syrup')
ing('orgeat','杏仁糖浆','Orgeat','syrup sweet nut_syrup','Orgeat syrup|奥给特糖浆|Orgeat Syrup (Almond)',note='通常含杏仁；糖浆品牌配方不同。')
ing('passionfruit_syrup','百香果糖浆','Passionfruit Syrup','syrup sweet tropical','Passion fruit syrup')
ing('ginger_syrup','姜糖浆','Ginger Syrup','syrup sweet')
ing('sugar','砂糖','Sugar','solid_sweet','白糖|细砂糖|White sugar|Superfine sugar|White cane sugar|Powdered sugar')
ing('sugar_cube','方糖','Sugar Cube','solid_sweet','方糖块')
ing('honey','蜂蜜','Honey','solid_sweet','Raw Honey',note='纯蜂蜜不等于蜂蜜糖浆。')
ing('triple_sec','三重橙酒','Triple Sec','orange_liqueur','橙味利口酒|Triple-sec|Orange liqueur')
ing('cointreau','君度橙酒','Cointreau','orange_liqueur','君度|Cointreau liqueur',parent='triple_sec',brand='Cointreau',source='https://www.cointreau.com/us/en/what-cointreau')
ing('grand_marnier','柑曼怡','Grand Marnier','orange_liqueur','柑曼怡橙酒|Grand Marnier Cordon Rouge',brand='Grand Marnier',note='干邑基底橙酒；与君度风味不同，不是同义词。')
ing('dry_curacao','干库拉索橙酒','Dry Curaçao','orange_liqueur','Dry curacao|Orange curacao|干橙皮酒')
ing('blue_curacao','蓝库拉索','Blue Curaçao','orange_liqueur','Blue curacao|蓝橙酒',note='颜色与具体产品甜度会改变成品。')
ing('sweet_vermouth','甜红味美思','Sweet Vermouth','sweet_vermouth','甜味美思|红味美思|甜红威末酒|Sweet red vermouth|Red vermouth|Vermouth rosso')
ing('dry_vermouth','干味美思','Dry Vermouth','dry_vermouth','干威末酒|Dry white vermouth|Extra dry vermouth')
ing('blanc_vermouth','白甜味美思','Blanc Vermouth','blanc_vermouth','Bianco vermouth|白味美思',note='白甜味美思不等于干味美思。')
ing('campari','金巴利','Campari','red_bitter aperitivo','Bitter Campari|康巴利',brand='Campari',source='https://www.campari.com/our-products/campari/')
ing('aperol','阿佩罗','Aperol','aperitivo','阿培罗|阿佩洛',brand='Aperol',note='比金巴利更轻柔的风格；不能当作金巴利同义词。',source='https://www.aperol.com/our-products/aperol/')
ing('cynar','西纳尔','Cynar','aperitivo','朝鲜蓟苦酒',brand='Cynar')
ing('angostura','安格式苦精','Angostura Aromatic Bitters','bitters','安高天娜苦精|安格仕苦精|安格斯图拉苦精|Angostura bitters|Angostura',brand='Angostura')
ing('aromatic_bitters','芳香苦精','Aromatic Bitters','bitters','芳香型苦精')
ing('orange_bitters','橙味苦精','Orange Bitters','bitters','橙皮苦精')
ing('peychauds','佩肖苦精','Peychaud’s Bitters','bitters','Peychauds bitters|Peychaud bitters',brand='Peychaud’s')
ing('soda','苏打水','Soda Water','soda carbonated mixer','气泡水|无糖气泡水|Club soda|Soda|Sparkling water|Seltzer')
ing('tonic','汤力水','Tonic Water','tonic carbonated mixer','通宁水|Tonic',note='含苦味与通常含糖，不能与苏打水归并。')
ing('ginger_beer','姜汁啤酒','Ginger Beer','ginger_beer carbonated mixer','姜啤',note='姜味强度和含糖量依品牌而异。')
ing('ginger_ale','干姜水','Ginger Ale','ginger_ale carbonated mixer','姜汁汽水|干姜汽水',note='比姜汁啤酒风味常更轻；不是同义词。')
ing('cola','可乐','Cola','carbonated mixer','Coca-Cola|Coke')
ing('sparkling_wine','起泡葡萄酒','Sparkling Wine','sparkling_wine carbonated','起泡酒')
ing('prosecco','普罗塞克','Prosecco','sparkling_wine carbonated','普罗赛克',parent='sparkling_wine')
ing('champagne','香槟','Champagne','sparkling_wine carbonated','Chilled Champagne',parent='sparkling_wine')
ing('white_wine','干白葡萄酒','Dry White Wine','wine','干白')
ing('red_wine','红葡萄酒','Red Wine','wine','红酒')
ing('port','波特酒','Port Wine','fortified_wine','Tawny port|Red tawny port wine|Ruby port')
ing('lillet','利莱白','Lillet Blanc','aromatized_wine','Lillet blonde|丽叶白',brand='Lillet',note='不自动等同干味美思。')
ing('mint','薄荷','Mint','herb mint','薄荷叶|Mint leaves|Mint sprigs|Fresh mint|Fresh mint leaves')
ing('basil','罗勒','Basil','herb basil','罗勒叶|Basil leaves|Italian basil leaves')
ing('lemon','柠檬','Lemon','fruit','鲜柠檬',note='整果不能直接按毫升当作果汁。')
ing('lime','青柠','Lime','fruit','莱姆|青柠檬|Fresh lime',note='整果不能直接按毫升当作果汁。')
ing('orange','橙子','Orange','fruit','橙')
ing('lemon_peel','柠檬皮','Lemon Peel','garnish','Lemon zest|Lemon twist')
ing('orange_peel','橙皮','Orange Peel','garnish','Orange zest|Orange twist')
ing('cherry','鸡尾酒樱桃','Cocktail Cherry','garnish','Maraschino cherry|樱桃')
ing('salt','盐','Salt','seasoning','食盐')
ing('ice','冰','Ice','ice','冰块|碎冰|Ice cubes|Crushed ice|Cracked ice')
ing('water','水','Water','water','清水|Plain water|Cold water')
ing('egg_white','蛋清','Egg White','foam','鸡蛋清|蛋白|Fresh egg white')
ing('egg_yolk','蛋黄','Egg Yolk','egg')
ing('cream','奶油','Cream','cream','淡奶油|Fresh cream|Heavy cream|Fresh cream (Chilled)')
ing('milk','牛奶','Milk','cream')
ing('coconut_cream','椰奶油','Coconut Cream','cream tropical',note='无糖椰奶油和甜椰浆并非同一产品，需确认甜度。')
ing('cream_of_coconut','甜椰浆','Cream of Coconut','cream tropical sweet',note='加糖椰浆，不等于无糖椰奶或椰奶油。')
ing('coconut_milk','椰奶','Coconut Milk','cream tropical',note='不等同甜椰浆。')
ing('coffee_liqueur','咖啡利口酒','Coffee Liqueur','liqueur coffee','咖啡酒')
ing('kahlua','甘露咖啡酒','Kahlúa','liqueur coffee','甘露|Kahlua',parent='coffee_liqueur',brand='Kahlúa')
ing('espresso','浓缩咖啡','Espresso','coffee','意式浓缩咖啡|Espresso coffee')
ing('amaretto','杏仁利口酒','Amaretto','liqueur','杏仁酒',note='不是杏仁糖浆。')
ing('maraschino','黑樱桃利口酒','Maraschino','liqueur','Maraschino Luxardo|Luxardo maraschino|马拉斯奇诺')
ing('absinthe','苦艾酒','Absinthe','accent','艾碧斯',note='与味美思、苦精均不同。')
ing('green_chartreuse','绿查特酒','Green Chartreuse','liqueur','绿查特|绿夏特|绿色查特',brand='Chartreuse')
ing('yellow_chartreuse','黄查特酒','Yellow Chartreuse','liqueur','黄查特|黄夏特',brand='Chartreuse')
ing('elderflower','接骨木花利口酒','Elderflower Liqueur','liqueur','St-Germain|St Germain|圣日耳曼')
ing('falernum','法勒纳姆','Falernum','liqueur','法勒纳姆利口酒')
ing('peach_liqueur','桃味利口酒','Peach Schnapps','liqueur','桃子利口酒|Peach liqueur')
ing('apricot_liqueur','杏味利口酒','Apricot Brandy','liqueur','Apricot liqueur')
ing('cacao_liqueur','可可利口酒','Crème de Cacao','liqueur','Creme de cacao|Crème de Cacao (Brown)')
ing('white_cacao','白可可利口酒','Crème de Cacao (White)','liqueur',parent='cacao_liqueur')
ing('violette','紫罗兰利口酒','Crème de Violette','liqueur','Creme de violette')
ing('mure','黑莓利口酒','Crème de Mûre','liqueur','Creme de mure|Blackberry liqueur')
ing('cassis','黑加仑利口酒','Crème de Cassis','liqueur','Creme de cassis')
ing('menthe','绿薄荷利口酒','Crème de Menthe (Green)','liqueur','Green creme de menthe')
ing('raspberry_liqueur','覆盆子利口酒','Raspberry Liqueur','liqueur','树莓利口酒')
ing('raspberry_syrup','覆盆子糖浆','Raspberry Syrup','syrup sweet','树莓糖浆')
ing('peach_puree','白桃果泥','White Peach Puree','juice','白桃泥|Peach puree')
ing('fernet','费尔奈特苦酒','Fernet','liqueur')
ing('fernet_branca','费尔奈特布兰卡','Fernet Branca','liqueur',parent='fernet',brand='Fernet Branca')
ing('frangelico','榛子利口酒','Frangelico','liqueur','Licor Frangelico|法兰榛子酒',brand='Frangelico')
ing('coffee','咖啡','Coffee','coffee','Hot coffee|热咖啡',note='浓度与浓缩咖啡不同，不自动视作同量替代。')
ing('worcestershire','伍斯特酱','Worcestershire Sauce','seasoning','辣酱油|喼汁')
ing('citron_vodka','柑橘味伏特加','Vodka Citron','base vodka','Citron vodka|柠檬味伏特加',parent='vodka')
ing('blackstrap_rum','黑糖蜜朗姆酒','Blackstrap Rum','base rum dark_rum','黑糖蜜朗姆',parent='rum')
ing('smirnoff','斯米诺原味伏特加','Smirnoff Vodka','base vodka','皇冠伏特加',parent='vodka',brand='Smirnoff')
ing('bacardi_white','百加得白朗姆','Bacardí Carta Blanca','base rum white_rum','百加得白|Bacardi Carta Blanca|Bacardi Superior|Bacardi White Rum',parent='white_rum',brand='Bacardí',source='https://www.bacardi.com/our-rums/carta-blanca-rum/')
ing('beefeater','必富达伦敦干金酒','Beefeater London Dry Gin','base gin','必富达金酒|必富达|Beefeater',parent='gin',brand='Beefeater')
ing('tanqueray','添加利伦敦干金酒','Tanqueray London Dry Gin','base gin','添加利伦敦干|Tanqueray London Dry',parent='gin',brand='Tanqueray')
ing('bombay_sapphire','孟买蓝宝石金酒','Bombay Sapphire','base gin','孟买蓝宝石|蓝宝石金酒',parent='gin',brand='Bombay Sapphire')
ing('absolut','绝对原味伏特加','Absolut Original','base vodka','绝对原味|Absolut vodka|绝对原味伏特加',parent='vodka',brand='Absolut')
ing('makers_mark','美格波本','Maker’s Mark','base whiskey bourbon','美格|Makers Mark|Maker\'s Mark',parent='bourbon',brand='Maker’s Mark')
ing('jim_beam','金宾白标波本','Jim Beam White Label','base whiskey bourbon','金宾白标|Jim Beam Bourbon',parent='bourbon',brand='Jim Beam')
ing('martini_rosso','马天尼红味美思','Martini Rosso','sweet_vermouth','马天尼红|马天尼甜红|Martini & Rossi Rosso',parent='sweet_vermouth',brand='Martini')
ing('martini_dry','马天尼干味美思','Martini Extra Dry','dry_vermouth','马天尼干|马天尼特干',parent='dry_vermouth',brand='Martini')
ing('martini_bianco','马天尼白甜味美思','Martini Bianco','blanc_vermouth','马天尼白|马天尼白味美思',parent='blanc_vermouth',brand='Martini')

AMBIGUOUS = {
    '百加得': ['bacardi_white','aged_rum','dark_rum'], 'bacardi': ['bacardi_white','aged_rum','dark_rum'],
    '马天尼': ['martini_rosso','martini_dry','martini_bianco'], 'martini': ['martini_rosso','martini_dry','martini_bianco'],
    '味美思': ['sweet_vermouth','dry_vermouth','blanc_vermouth'], 'vermouth': ['sweet_vermouth','dry_vermouth','blanc_vermouth'],
    '苦精': ['angostura','orange_bitters','peychauds'], 'bitters': ['angostura','orange_bitters','peychauds'],
    '添加利': ['tanqueray'], '绝对': ['absolut'], '柠檬水': ['lemon_juice','soda'],
    '椰浆': ['coconut_cream','coconut_milk','cream_of_coconut'], '橙酒': ['triple_sec','grand_marnier','blue_curacao'],
    'Bourbon or Rye Whiskey': ['bourbon','rye'], 'Rye Whiskey or Bourbon': ['rye','bourbon'],
    'Brut Champagne or Prosecco': ['champagne','prosecco'],
}

DRINK_ALIASES = {
    'Negroni':['尼格罗尼','内格罗尼'], 'Whiskey Sour':['威士忌酸','威士忌酸酒','Whisky Sour'],
    'Daiquiri':['戴基里','黛绮莉'], 'Margarita':['玛格丽特','玛格丽塔'],
    'Dry Martini':['干马天尼','干马丁尼'], 'Manhattan':['曼哈顿'], 'Old Fashioned':['古典','古典鸡尾酒','Old-Fashioned'],
    'Mojito':['莫吉托','莫希托'], 'Mint Julep':['薄荷朱利普','薄荷茱莉普'],
    'Sidecar':['边车'], 'Spritz':['斯普利兹','Aperol Spritz','阿佩罗斯普利兹'],
    'Gin Fizz':['金菲士','金费士'], 'French 75':['法国75','法式75'],
    'Moscow Mule':['莫斯科骡子','莫斯科之骡'], 'Mai Tai':['迈泰','Mai-Tai'],
    'Tom Collins':['汤姆柯林斯','汤姆科林斯'], 'Boulevardier':['林荫大道'],
    'Espresso Martini':['浓缩咖啡马天尼'], 'Cosmopolitan':['大都会'],
    'Piña Colada':['椰林飘香','Pina Colada'], 'Sazerac':['萨泽拉克'],
    'Aviation':['飞行'], 'Vesper':['薇斯帕'], 'White Lady':['白色佳人'],
    'Last Word':['最后一语'], 'Bramble':['荆棘'], 'Pisco Sour':['皮斯科酸'],
}

def slot(id, label, roles, default, amount, low, high, unit='ml'):
    return dict(id=id,label=label,roles=roles.split(),default=default,amount=amount,low=low,high=high,unit=unit)

FRAMEWORKS = []
def frame(id, zh, en, formula, description, slots, methods, steps, refs, note='', optional=None):
    FRAMEWORKS.append(dict(id=id,zh=zh,en=en,formula=formula,description=description,slots=slots,methods=methods,
                           steps=steps,reference_names=refs, note=note,optional=optional or [],
                           evidence_kind='经典结构 + 编辑定义试配范围；不是 IBA 发布的评分标准',
                           source_urls=['https://iba-world.com/iba-cocktail/'+r+'/' for r in refs]))

frame('sour','酸酒','Sour','基酒 + 酸 + 甜','最适合从现有基酒出发的三角结构。柑橘带来酸度，糖浆缓和尖锐感。',
      [slot('base','基酒','base','bourbon',45,.8,1.2),slot('acid','柑橘酸源','acid','lemon_juice',25,.35,.65),slot('sweet','糖浆','syrup','simple_syrup',20,.22,.50)],
      ['shake'],['将基酒、果汁和糖浆加冰摇匀。','滤入冰镇杯，或装有新冰的古典杯。','先尝一小口，再以 2–5 ml 调整酸甜。'],['whiskey-sour','daiquiri'],
      note='45:25:20 参考 Whiskey Sour；Daiquiri 的砂糖版本不可直接换算为同体积糖浆。',optional=['egg_white','lemon_peel'])
frame('daisy','橙酒酸酒','Daisy','基酒 + 柑橘 + 橙酒','以橙味利口酒承担甜味和香气，典型是玛格丽特与边车。',
      [slot('base','基酒','base','tequila_blanco',50,.8,1.2),slot('acid','柑橘酸源','acid','lime_juice',20,.25,.50),slot('orange','橙味利口酒','orange_liqueur','cointreau',20,.25,.50)],
      ['shake'],['基酒、果汁和橙酒加冰摇匀。','滤入冰镇杯。','使用不同橙酒时先少量试饮，再决定是否增添糖浆。'],['margarita','sidecar'],note='50:20:20 为教学起点；IBA Margarita 的青柠汁是 15 ml。',optional=['salt','orange_peel'])
frame('old_fashioned','古典','Old Fashioned','基酒 + 少量甜 + 苦精','以基酒为中心，少量甜味修饰，苦精形成香气层次。',
      [slot('base','基酒','base','bourbon',45,.8,1.2),slot('sweet','糖浆','syrup','simple_syrup',5,.06,.20),slot('bitters','苦精','bitters','angostura',2,1,4,'dash')],
      ['stir','build'],['基酒、糖浆和苦精与大冰块搅拌降温。','以橙皮挤油增香。'],['old-fashioned'],note='糖浆版本是便于试配的改编；原始官方条目使用方糖，未将方糖强行换算为 ml。',optional=['orange_peel'])
frame('martini','干马天尼','Martini','基酒 + 干味美思','简洁、酒感突出的搅拌结构，味美思用量决定干湿风格。',
      [slot('base','基酒','gin vodka','gin',60,.8,1.2),slot('vermouth','干味美思','dry_vermouth','dry_vermouth',10,.12,.35)],
      ['stir'],['将材料与冰充分搅拌降温。','滤入冰镇鸡尾酒杯，挤入柠檬皮油。'],['dry-martini'],note='评分范围针对干式起点；湿式和 50/50 Martini 是其他有效风格。',optional=['lemon_peel'])
frame('manhattan','曼哈顿','Manhattan','威士忌 + 甜味美思 + 苦精','陈年谷物香、葡萄酒香与苦精的组合。',
      [slot('base','威士忌','whiskey','rye',50,.8,1.2),slot('vermouth','甜红味美思','sweet_vermouth','sweet_vermouth',20,.30,.60),slot('bitters','苦精','bitters','angostura',1,1,3,'dash')],
      ['stir'],['材料加冰搅拌至充分冰冷。','滤入冰镇杯，用鸡尾酒樱桃装饰。'],['manhattan'],optional=['cherry'])
frame('negroni','尼格罗尼','Negroni','基酒 + 红色苦味开胃酒 + 甜味美思','经典等份结构。甜味美思连接基酒与金巴利的苦味。',
      [slot('base','基酒','base','gin',30,.8,1.2),slot('bitter','红色苦味开胃酒','red_bitter','campari',30,.75,1.25),slot('vermouth','甜红味美思','sweet_vermouth','sweet_vermouth',30,.75,1.25)],
      ['stir','build'],['将材料加入装冰的古典杯。','轻轻搅拌，用橙皮或橙片增香。'],['negroni','boulevardier'],note='阿佩罗可以形成改编，但不当作金巴利的等价替代。',optional=['orange_peel'])
frame('highball','高球','Highball','基酒 + 长饮填充','让基酒与大量冰冷的填充饮料形成清爽长饮。',
      [slot('base','基酒','base','whiskey',45,.8,1.2),slot('mixer','填充饮料','mixer','soda',120,2,4)],
      ['build'],['长饮杯装满冰，倒入基酒。','加入冰冷填充饮料，轻轻提拌。'],['cuba-libre','dark-n-stormy'],note='45:120 是通用试配起点；并非引用配方的完整复制。汤力、苏打、可乐的甜苦风格不同。',optional=['lemon_peel'])
frame('collins','柯林斯 / 菲士','Collins / Fizz','酸酒 + 苏打','酸甜结构延长为气泡长饮；不同杯型、用冰与苏打量形成变体。',
      [slot('base','基酒','base','gin',45,.8,1.2),slot('acid','柑橘酸源','acid','lemon_juice',25,.35,.70),slot('sweet','糖浆','syrup','simple_syrup',15,.15,.45),slot('soda','苏打水','soda','soda',60,1,2.5)],
      ['shake_top'],['基酒、果汁和糖浆加冰摇匀。','滤入长饮杯，最后加入苏打水并轻拌。'],['gin-fizz','john-collins'],note='此处生成的是加冰长饮试配。IBA Gin Fizz 不带冰上桌，苏打量为 splash，不能视为同一标准配方。')
frame('spritz','斯普利兹','Spritz','起泡酒 + 开胃酒 + 苏打','酒体较轻、以苦甜和气泡为主的开胃长饮。',
      [slot('base','起泡葡萄酒','sparkling_wine','prosecco',90,.8,1.2),slot('aperitif','开胃酒','aperitivo','aperol',60,.45,.85),slot('soda','苏打水','soda','soda',30,.15,.50)],
      ['build'],['葡萄酒杯装满冰。','加入起泡酒、开胃酒和苏打，轻轻混合。'],['spritz'],note='90:60:30 是试配起点；本批官方网页中的苏打量为 splash。',optional=['orange'])
frame('mule','骡子','Mule / Buck','基酒 + 青柠 + 姜汁啤酒','姜香与青柠提亮基酒，姜汁啤酒同时贡献甜度与气泡。',
      [slot('base','基酒','base','vodka',45,.8,1.2),slot('acid','柑橘酸源','acid','lime_juice',10,.15,.35),slot('ginger','姜汁啤酒','ginger_beer','ginger_beer',120,2,3.5)],
      ['build'],['杯中加冰、基酒与青柠汁。','最后加入姜汁啤酒并轻拌。'],['moscow-mule'],note='干姜水只作为风味改编候选，不直接占用姜汁啤酒槽位。')
frame('julep','朱利普','Julep','基酒 + 薄荷 + 少量甜','碎冰带来持续降温与稀释，薄荷强调鼻腔香气。',
      [slot('base','基酒','base','bourbon',60,.8,1.2),slot('sweet','糖浆','syrup','simple_syrup',7.5,.07,.20),slot('herb','薄荷','mint','mint',6,4,10,'leaf')],
      ['build'],['轻压薄荷使其释放香气，不要碾碎。','加入基酒与糖浆，填入碎冰并搅拌。','以薄荷枝装饰。'],['mint-julep'],note='糖浆及薄荷叶数是试配选择；官方使用砂糖、清水与薄荷枝，单位不同。')
frame('tropical','热带酸酒','Tropical Sour','朗姆 + 酸 + 橙酒 + 风味糖浆','以 Mai Tai 为参照的多层甜酸结构，控制糖浆与利口酒总量。',
      [slot('base','朗姆酒','rum','aged_rum',60,.8,1.2),slot('acid','柑橘酸源','acid','lime_juice',25,.30,.55),slot('orange','橙味利口酒','orange_liqueur','dry_curacao',15,.15,.35),slot('sweet','风味糖浆','syrup','orgeat',10,.10,.25)],
      ['shake'],['材料加冰摇匀。','滤入装碎冰的杯子，可用薄荷增香。'],['mai-tai'],note='这是 Mai Tai 启发的单朗姆简化版本，不代表所有 Tiki 或 Punch。',optional=['mint'])

METHODS = {'shake':'摇和','stir':'搅拌','build':'杯中兑和','shake_top':'先摇和，后加气泡'}
