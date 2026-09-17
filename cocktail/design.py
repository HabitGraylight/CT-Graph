"""Reviewed design prompts, kept separate from sensory scores and chemical laws."""
VERSION = '2026-09-17.1'
SOURCES = {
    'liquid': {'title': 'Dave Arnold — Liquid Intelligence（中文版：酸类，印刷页 42–43）', 'url': 'https://wwnorton.com/books/9780393089035', 'kind': 'book_method', 'scope': '已核读本地书页；URL 仅为原著出版社书目，不代表网页包含该段证据。'},
    'codex': {'title': 'Cocktail Codex — six root families', 'url': 'https://www.deathandcompanymarket.com/products/cocktail-codex', 'kind': 'author_framework'},
    'ice': {'title': 'Dave Arnold — Science of Shaking II', 'url': 'https://www.cookingissues.com/index.html%3Fp=1527.html', 'kind': 'author_experiment'},
    'pairing': {'title': 'Ahn et al. — Flavor network and the principles of food pairing', 'url': 'https://arxiv.org/abs/1111.6074', 'kind': 'observational_recipe_network'},
}
ROOTS = [
    {'id': 'old_fashioned', 'name': 'Old Fashioned / 古典', 'focus': '基酒、甜味与调味', 'frames': ['old_fashioned', 'julep']},
    {'id': 'martini', 'name': 'Martini / 马天尼', 'focus': '基酒与芳香酒的关系', 'frames': ['martini', 'manhattan', 'negroni']},
    {'id': 'daiquiri', 'name': 'Daiquiri / 大吉利', 'focus': '基酒、酸与甜', 'frames': ['sour', 'tropical', 'collins']},
    {'id': 'sidecar', 'name': 'Sidecar / 边车', 'focus': '利口酒同时贡献香气、糖与酒精', 'frames': ['daisy']},
    {'id': 'highball', 'name': 'Highball / 高球', 'focus': '基酒、延长料与气泡状态', 'frames': ['highball', 'collins', 'mule', 'spritz']},
    {'id': 'flip', 'name': 'Flip / 弗利普', 'focus': '蛋、糖与基酒的质地结构', 'frames': []},
]


def catalog():
    return {'version': VERSION, 'roots': ROOTS, 'sources': SOURCES,
            'mapping_policy': '根型来自作者体系；与本项目框架的多对多映射是编辑解释，不是历史谱系或唯一分类。Flip 尚无评分模板。'}


def review(evaluation, context):
    items = [i for i in evaluation['items'] if i['status'] == 'matched']
    roles = {role for i in items for role in i['ingredient']['roles']}
    frame = evaluation['frame_id']
    prompts = []

    def add(id, message, test, sources):
        prompts.append({'id': id, 'message': message, 'verification': test,
                        'source_ids': sources, 'numeric_score_effect': None,
                        'evidence_kind': 'editorial_application', 'status': 'trial_prompt'})

    add('role_before_replacement', '替换原料时同时检查结构角色、酒精度、糖/酸贡献和香气强度；同类原料不默认等量等味。',
        '保留原版，先单独替换一种原料，记录品牌与实际用量。', ['codex'])
    if evaluation.get('method') in {'shake', 'stir', 'shake_top'}:
        if 'dilution_ml' not in context or 'temperature_c' not in context:
            add('missing_service_state', '缺少出杯温度或额外水量记录；仅凭摇/搅秒数不能确认稀释是否合适。',
                '比较前后样品时同时记录温度、额外水量、冰的初温和表面带水；不要把大冰或透明冰直接换算成高分。', ['ice'])
    if 'acid' in roles:
        add('acid_measurement', '果汁酸味不能由 pH 单独表示；记录可滴定酸的计量基准、糖和批次。不同酸种不保证同 g/L 同口感。',
            '在相同糖量与稀释条件下试饮；未测浓度保留未知，不把书中典型值当作这一批果汁的实测值。', ['liquid'])
    if roles & {'liqueur', 'orange_liqueur', 'sweet_vermouth', 'red_bitter'}:
        add('modifier_multiple_roles', '辅酒可能同时改变甜度、烈度、苦味与香气，不能只把它当作一种味道的旋钮。',
            '调整辅酒时列出受到影响的所有维度；只有瓶标或测量充分时才重算浓度。', ['codex'])
    if roles & {'carbonated', 'sparkling_wine'}:
        add('carbonation_service', '气泡表现与加入时机、温度和操作相关；框架比例正确仍需验证实际气泡与口感。',
            '冷却后加入气泡料，记录出杯即刻和放置后的表现；不要以气泡多寡直接推定总分。', ['codex'])
    if roles & {'herb', 'garnish', 'liqueur', 'juice', 'fruit'}:
        add('pairing_hypothesis', '香气相似或有共同成分只能产生搭配候选；剂量、加工、味觉与个人偏好仍需验证。',
            '对照不加该配料的小样，分别记录鼻前香、鼻后香、苦涩与整体偏好；共现数据不是因果证明。', ['pairing'])
    if frame == 'martini':
        add('version_specific_ratio', '当前评分使用本项目干马天尼模板；更湿的经典或作者版本不应仅因偏离此比例被认定不好喝。',
            '先声明目标版本，再比较味美思比例、鲜度与酒精度；需要目标版本模板时单独建版本。', ['codex'])
    return {'version': VERSION, 'roots': [r for r in ROOTS if frame in r['frames']],
            'mapping_policy': catalog()['mapping_policy'], 'prompts': prompts,
            'sources': [dict(id=k, **v) for k, v in SOURCES.items() if any(k in p['source_ids'] for p in prompts)],
            'policy': '这是可复用设计检查，不是书籍全文摘要，也不产生新的味觉分数。无 source_ids 的提示为项目编辑约定；本地阅读证据另存。'}
