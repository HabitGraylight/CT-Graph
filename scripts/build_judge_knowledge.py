"""Build the reviewed, qualitative chemistry layer; never rewrite source recipes."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cocktail.knowledge import ROOT, INGREDIENTS

DAY = '2026-09-15'
SOURCES = [
    ('usbg2025', 'USBG Shake It Up 2025 competition terms', 'https://usbg.org/shake-it-cocktail-competition-terms-conditions', 'competition_rules', '2025', '赛事区分纸面配方评审与现场感官评审，权重随赛制变化。只作为该届实例。'),
    ('sweet_sour', 'Sensory integration in citric acid/sucrose mixtures', 'https://academic.oup.com/chemse/article-abstract/15/1/87/322423', 'human_sensory_experiment', '1990', '蔗糖与柠檬酸混合存在不对称的感知抑制；限实验浓度。核对出版方摘要，不冒充读过付费全文。'),
    ('dilution', 'Dilution of whisky — the molecular perspective', 'https://pubmed.ncbi.nlm.nih.gov/28819215/', 'molecular_simulation', '2017', '乙醇/水/愈创木酚模型中稀释改变分子分布；不能推出所有香气都增强或具体好喝分。核对摘要和研究机构说明，全文访问受限。'),
    ('casein', 'University of Guelph: Milk Proteins and Casein Micelles', 'https://books.lib.uoguelph.ca/dairyscienceandtechnologyebook/chapter/milk-proteins-caseins-casein-micelles-whey-proteins-enzymes/', 'university_food_science', None, '酸化至等电区约 pH 4.6、乙醇和温度可改变酪蛋白胶束稳定性；取决于乳制品体系。'),
    ('foam', 'Effects of yolk contamination, shearing, and heating on foaming properties of fresh egg white', 'https://pubmed.ncbi.nlm.nih.gov/19323729/', 'food_experiment_abstract', '2009', '蛋黄污染及其中中性脂质可降低蛋清起泡能力；不是所有脂质必然让所有鸡尾酒泡沫消失。'),
    ('ouzo', 'Ouzo Effect Examined at the Nanoscale via Direct Observation of Droplet Nucleation and Morphology', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10037490/', 'physical_experiment', '2023', '反式茴香脑/乙醇/水及商业 ouzo 中观察到稀释诱发油滴成核；条件与浓度有关。'),
    ('co2', 'On the Losses of Dissolved CO2 during Champagne Serving', 'https://www.acs.org/content/dam/acsorg/avweb/1c2web3536/champagnepouring.pdf', 'physical_experiment', '2010', '香槟倒杯实验中低温与沿倾斜杯壁倒入可减少 CO2 损失；鸡尾酒应用为定性外推。'),
    ('carbonation_taste', 'The Taste of Carbonation', 'https://pubmed.ncbi.nlm.nih.gov/19833970/', 'animal_mechanistic_experiment', '2009', '小鼠实验将 CO2 味觉响应联系到酸敏细胞及碳酸酐酶；不作为人类偏好或分数预测。核对摘要。'),
    ('salt', 'Salt enhances flavour by suppressing bitterness', 'https://www.nature.com/articles/42388', 'human_sensory_experiment', '1997', '实验混合物中盐可选择性抑制苦味；不意味着所有酒加盐都会变好。核对出版方摘要。'),
    ('tannin', 'Effect of condensed tannins addition on the astringency of red wines', 'https://pubmed.ncbi.nlm.nih.gov/22086902/', 'human_sensory_and_chemical_experiment', '2012', '红酒中缩合单宁与唾液蛋白变化及涩感相关；涩感不是简单的苦味或总酚含量。核对摘要。'),
    ('juice', 'Quantitative Assessment of Citric Acid in Lemon Juice, Lime Juice, and Commercially-Available Fruit Juice Products', 'https://pubmed.ncbi.nlm.nih.gov/18290732/', 'chemical_measurement', '2008', '样本中鲜柠檬/青柠汁与商业果汁酸含量不同；不能拿论文均值代替用户瓶中的实测值。核对摘要。'),
    ('iba_martini', 'IBA Dry Martini', 'https://iba-world.com/iba-cocktail/dry-martini/', 'official_recipe', None, '60 ml 金酒与 10 ml 干味美思，搅拌、过滤至冰杯、可挤柠檬皮油。烈酒主导是风格。'),
    ('iba_sour', 'IBA Whiskey Sour', 'https://iba-world.com/iba-cocktail/whiskey-sour/', 'official_recipe', None, '含果汁并可加蛋清，摇和后过滤；泡沫与浑浊不自动是缺陷。'),
]

# Typical classes, not laboratory identification of every product or batch.
COMPONENTS = [
    ('ethanol', '乙醇', ['aroma','balance','texture'], '影响烈度、溶剂环境和挥发分分配；不能仅由 ABV 推断灼热或好喝。', ['dilution']),
    ('sugars', '糖类', ['balance','texture'], '提供甜味；浓度与基质会改变酸甜感知和酒体。', ['sweet_sour']),
    ('organic_acids', '有机酸', ['balance','structure'], '酸的种类、浓度、缓冲与感知相关；pH 不等于可滴定酸度。', ['juice','sweet_sour','casein']),
    ('aroma_compounds', '挥发性香气成分（待细分）', ['aroma','structure','expression'], '类别只说明可能有香气贡献，不能猜测每个品牌的具体分子及浓度。', ['dilution']),
    ('casein', '酪蛋白', ['appearance','texture'], '牛乳蛋白胶束可因酸、酒精及温度变化而聚集。', ['casein']),
    ('egg_protein', '蛋清蛋白', ['appearance','texture'], '在充气和适当处理下参与泡沫形成；稳定性受体系影响。', ['foam','iba_sour']),
    ('lipids', '脂质', ['texture','appearance'], '影响乳状体系与口感；某些脂质会干扰蛋清泡沫。', ['foam','casein']),
    ('co2', '溶解二氧化碳', ['texture','execution','balance'], '带来气泡与感官刺激，受温度和操作影响。', ['co2','carbonation_taste']),
    ('tannins', '缩合单宁（可能存在）', ['texture','structure'], '可与唾液蛋白相互作用并贡献涩感，实际含量及结构待测。', ['tannin']),
    ('bitter_compounds', '苦味成分（配方未公开）', ['balance','structure'], '苦味是某些风格的主体；不猜金巴利等专有产品的分子配方。', ['salt']),
    ('salt', '盐 / 氯化钠', ['balance'], '可影响混合味觉；未给盐水浓度时不按滴数推算克数。', ['salt']),
    ('anethole', '茴香脑（类别预期，非产品实测）', ['appearance','aroma'], '含茴香香气的酒在特定乙醇/水/油比例下可能出现乳浊。', ['ouzo']),
    ('suspended_solids', '果肉 / 悬浮颗粒', ['appearance','texture'], '果汁、果泥和草本颗粒影响外观与触感；是否过滤依风格决定。', ['iba_sour']),
    ('water', '水', ['balance','texture','execution'], '增加液体体积、稀释；融冰量须实测或声明情景假设。', ['dilution','co2']),
]

RULES = [
    ('sweet_acid', '酸甜的感知交互', ['sugars','organic_acids'], ['balance'], 'sensory', '甜味可能压低酸感，酸也可能压低甜感；糖不等同于化学中和剂。', '取决于各自浓度、酸种类及基质；没有通用最优糖酸比。', '固定其他条件，比较糖浆相差少量的两杯。', ['sweet_sour']),
    ('milk_acid', '乳蛋白遇酸的聚集风险', ['casein','organic_acids'], ['appearance','texture'], 'physical_chemical', '酸化可能使牛乳酪蛋白聚集。目标若是奶洗澄清，这是工艺环节；若要求顺滑乳状成品，应检查絮凝。', '是否发生取决于最终 pH、缓冲、酒精、乳配方、温度和顺序；不是一加柠檬就必定失败。', '记录最终 pH、加料顺序、静置状态及过滤结果。', ['casein']),
    ('milk_ethanol', '乙醇与乳胶束稳定性', ['casein','ethanol'], ['appearance','texture'], 'physical_chemical', '乙醇可能降低乳胶束稳定性，与酸及温度共同作用。', '低量乙醇不等于必然结块；不预测精确沉淀阈值。', '观察即时与静置后的颗粒、分层。', ['casein']),
    ('foam_lipid', '脂质对蛋清泡沫的影响', ['egg_protein','lipids'], ['appearance','texture'], 'physical', '蛋黄中的中性脂质有降低蛋清起泡的实验依据；含脂材料提示检查泡沫持久性。', '向奶油、椰脂等鸡尾酒体系的外推仅为低置信提醒；不自动扣分。', '记录泡沫初始高度和 2 分钟后保持情况；先对照无脂版本。', ['foam']),
    ('foam_air', '蛋清与摇和充气', ['egg_protein'], ['appearance','texture','execution'], 'physical', '摇和可以形成蛋清泡沫；泡沫质量仍须看杯中表现。', '不能从写了 Shake 就断言泡沫细腻；摇和并非必须保留冰屑。', '检查泡孔、异味与稳定性，记录摇和和过滤方式。', ['foam','iba_sour']),
    ('gas_retention', '温度与操作影响保气', ['co2'], ['texture','execution'], 'physical', '气泡材料的低温、轻柔倒入有利于减少 CO2 损失。', '证据来自香槟倒杯；气泡鸡尾酒效应大小需实测。', '先处理无气部分，气泡料最后加入，比较入口与放置后的气泡。', ['co2']),
    ('co2_taste', 'CO2 的味觉贡献', ['co2'], ['balance','texture'], 'physiological', '气泡并非只有机械触感；CO2 也有味觉机制。', '细胞机制的动物证据不用于预测人类喜欢程度或酸味强度。', '对照脱气前后，记录刺感与酸感，勿据此直接改酸量。', ['carbonation_taste']),
    ('louche', '稀释诱发油滴乳浊', ['anethole','water','ethanol'], ['appearance','aroma'], 'physical', '含茴香脑体系加水后可能出现油滴成核与乳浊，不等于变质。', '依油/乙醇/水比例而定；不能泛化到所有柑橘皮油。', '检查风格是否预期乳浊，记录稀释前后外观。', ['ouzo']),
    ('salt_bitter', '盐与苦味的感知交互', ['salt','bitter_compounds'], ['balance','structure'], 'sensory', '部分混合物中盐可抑制苦味，效果与苦味物及剂量有关。', '不能宣称固定滴数必定提鲜、增甜或提升分数。', '单独做小样，对照盐水浓度和体积，防止把苦味风格抹去。', ['salt']),
    ('astringency', '单宁与唾液蛋白', ['tannins'], ['texture','structure'], 'physiological', '单宁与唾液蛋白的相互作用可参与涩感形成；涩与苦需分别记录。', '红酒研究向混合酒的外推受糖、蛋白及其他成分影响。', '分别记录苦味强度、口腔干涩和余韵洁净度。', ['tannin']),
    ('aroma_partition', '稀释改变香气成分分布', ['ethanol','water','aroma_compounds'], ['aroma','structure','balance'], 'physical', '加水改变溶剂环境，可能改变某些香气分子的分布。', '愈创木酚模型不能证明所有酒稀释越多越香；这是机制提示。', '固定温度做小幅稀释对照，同时记录鼻前和鼻后香气。', ['dilution']),
]


def components_for(i):
    roles=set(i['roles']); c={'water'}
    if roles & {'base','liqueur','orange_liqueur','sweet_vermouth','dry_vermouth','blanc_vermouth','aperitivo','red_bitter','bitters','sparkling_wine','wine','fortified_wine','aromatized_wine'}: c.add('ethanol')
    if roles & {'sweet','syrup','solid_sweet','orange_liqueur','sweet_vermouth','blanc_vermouth','aperitivo','red_bitter','liqueur'}: c.add('sugars')
    if roles & {'juice','fruit','acid','dry_vermouth','wine','sparkling_wine','fortified_wine','aromatized_wine','tonic','ginger_beer','ginger_ale'} or i['id'] in {'cola','milk','cream'}: c.add('sugars')
    if roles & {'acid','juice'} or i['id']=='passionfruit_puree': c.add('organic_acids')
    if roles & {'base','liqueur','orange_liqueur','herb','garnish','juice','bitters','aperitivo','red_bitter','sweet_vermouth','dry_vermouth','blanc_vermouth','wine'}: c.add('aroma_compounds')
    if roles & {'acid','fruit','coffee','sparkling_wine','fortified_wine','aromatized_wine'}: c.add('aroma_compounds')
    if roles & {'carbonated','sparkling_wine'}:c.add('co2')
    if roles & {'bitters','red_bitter','aperitivo','tonic','coffee'} or i['id'] in {'fernet','fernet_branca'}:c.add('bitter_compounds')
    if roles & {'juice','herb','acid','fruit'} or i['id']=='passionfruit_puree':c.add('suspended_solids')
    if i['id'] in {'milk','cream'}:c|={'casein','lipids'}
    if i['id'] in {'egg_yolk','coconut_cream','cream_of_coconut','coconut_milk','orgeat'}:c.add('lipids')
    if i['id']=='egg_white':c.add('egg_protein')
    if i['id']=='red_wine':c.add('tannins')
    if i['id']=='salt':c={'salt'}
    if i['id']=='sugar' or i['id']=='sugar_cube':c={'sugars'}
    if i['id']=='absinthe':c|={'anethole','ethanol','aroma_compounds'}
    return sorted(c)


def build():
    sources=[dict(id=id,title=title,url=url,evidence_type=kind,published=year,reviewed_at=DAY,review_after_days=365,scope=scope) for id,title,url,kind,year,scope in SOURCES]
    components=[dict(id=id,name=name,dimensions=dims,mechanism=mechanism,source_ids=refs) for id,name,dims,mechanism,refs in COMPONENTS]
    rules=[dict(id=id,title=title,requires=requires,dimensions=dims,kind=kind,effect=effect,conditions=conditions,verification=verification,source_ids=refs,numeric_score_effect=None,confidence='conditional',status='active') for id,title,requires,dims,kind,effect,conditions,verification,refs in RULES]
    profiles=[dict(ingredient_id=i['id'],name=i['zh'],component_ids=components_for(i),basis='editorial_category_inference',concentrations={},coverage='qualitative_only_not_exhaustive',note='原料类别的可能成分，未穷尽或检测具体分子。浓度、零糖/无醇版本及加工差异须查瓶标或检测；文献支持机制，不证明每个品牌的组成。',source_ids=sorted({s for c in components if c['id'] in components_for(i) for s in c['source_ids']})) for i in INGREDIENTS]
    result=dict(schema_version=1,version='2026-09-15.1',reviewed_at=DAY,sources=sources,components=components,profiles=profiles,rules=rules)
    path=ROOT/'data/knowledge/judge.json';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise SystemExit('知识文件已存在；修改请走版本审查，不覆盖已有版本。')
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:len(result[k]) for k in ['sources','components','profiles','rules']}))

if __name__=='__main__':build()
