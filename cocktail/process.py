"""Ordered preparation states. Unknown melting and separation losses stay unknown."""
import math
from .normalization import resolve

OPERATIONS = {'add', 'add_water', 'shake', 'stir', 'strain', 'clarify', 'carbonate', 'serve'}


def finite(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} 需为 {low}–{high} 的有限数值')


def validate_materials(materials):
    if not isinstance(materials, list) or len(materials) > 80:
        raise ValueError('materials 需要是最多 80 项的列表')
    seen = set()
    for m in materials:
        if not isinstance(m, dict) or set(m) - {'name', 'product_label', 'variant', 'batch'} or not isinstance(m.get('name'), str):
            raise ValueError('materials 字段无效')
        r = resolve(m['name'])
        if r['status'] != 'matched':
            raise ValueError('材料身份需要先消除歧义')
        if r['ingredient']['id'] in seen:
            raise ValueError('同一原料只能绑定一份材料记录；不同批次请分开制作记录')
        seen.add(r['ingredient']['id'])
        if not set(m) & {'product_label', 'variant', 'batch'}:
            raise ValueError('材料记录需至少提供产品标签、版本或批次')
        for key in set(m) - {'name'}:
            if not isinstance(m[key], str) or not m[key].strip() or len(m[key]) > 200:
                raise ValueError('材料标签需为 1–200 字文本')


def validate_steps(steps):
    if not isinstance(steps, list) or not 1 <= len(steps) <= 40:
        raise ValueError('steps 需要 1–40 个有序步骤')
    for s in steps:
        if not isinstance(s, dict) or not isinstance(s.get('op'), str) or s['op'] not in OPERATIONS:
            raise ValueError('工艺步骤 op 无效')
        allowed = {'op', 'temperature_c', 'duration_s'}
        if s['op'] == 'add': allowed.add('uses')
        if s['op'] in {'add_water', 'shake', 'stir'}: allowed.add('water_ml')
        if set(s) - allowed:
            raise ValueError('工艺步骤字段无效')
        if s['op'] == 'add':
            uses = s.get('uses')
            if not isinstance(uses, list) or not uses or len(uses) > 80 or any(type(i) is not int or i < 0 for i in uses) or len(set(uses)) != len(uses):
                raise ValueError('add.uses 需为不重复的配方行索引（从 0 开始）')
        if s['op'] == 'add_water' and 'water_ml' not in s:
            raise ValueError('add_water 需提供 water_ml')
        for key, low, high in [('water_ml', 0, 5000), ('temperature_c', -30, 100), ('duration_s', 0, 86400)]:
            if key in s: finite(s[key], key, low, high)
    if steps[-1]['op'] != 'serve' or any(s['op'] == 'serve' for s in steps[:-1]):
        raise ValueError('步骤需且只能以 serve 结束')


def trace(items, context):
    steps = context.get('process', {}).get('steps')
    if steps is None:
        return {'status': 'not_recorded', 'states': [], 'warnings': [], 'transformed': False,
                'additional_water_ml': context.get('dilution_ml')}
    validate_steps(steps)
    states = []; warnings = []; added = set(); water = 0; melting_unknown = False
    transformed = False; carbonated = False; temperature = None
    for index, step in enumerate(steps):
        op = step['op']
        if op == 'add':
            for use in step['uses']:
                if use >= len(items) or use in added:
                    raise ValueError('工艺重复加入或引用不存在的配方行')
                added.add(use)
                item = items[use]
                carbonated |= item['status'] == 'matched' and bool(set(item['ingredient']['roles']) & {'carbonated', 'sparkling_wine'})
        elif not added:
            raise ValueError('操作前需先 add 配方原料')
        if op == 'shake' and carbonated:
            warnings.append({'id': 'shake_carbonated', 'step': index, 'message': '气泡已进入混合物后又摇和；应把气泡料放在无气部分摇和之后。'})
        if op in {'shake', 'stir'} and 'water_ml' not in step:
            melting_unknown = True
        water += step.get('water_ml', 0)
        if water > 5000: raise ValueError('步骤额外水量合计不能超过 5000 ml')
        if op == 'clarify': transformed = True
        if op == 'carbonate': carbonated = True
        # A prior temperature is not a measurement after the next operation.
        temperature = step.get('temperature_c')
        volume_known = all(items[i]['ml'] is not None for i in added)
        volume = sum(items[i]['ml'] or 0 for i in added) + water
        states.append({'index': index, 'op': op, 'uses_present': sorted(added),
                       'volume_ml': round(volume, 3) if volume_known and not melting_unknown and not transformed else None,
                       'added_water_ml': round(water, 3), 'melting_unknown': melting_unknown,
                       'temperature_c': temperature, 'composition_retention_known': not transformed,
                       'basis': 'declared_process_scenario_not_observed'})
    if added != set(range(len(items))):
        raise ValueError('步骤遗漏配方原料；每行需且只能加入一次')
    declared = context.get('dilution_ml')
    if declared is not None and (declared < water or (not melting_unknown and abs(declared - water) > .001)):
        raise ValueError('dilution_ml 必须是总额外水量，不能与步骤水量矛盾或重复相加')
    total_water = declared if declared is not None else None if melting_unknown else water
    if total_water is not None and not transformed and all(i['ml'] is not None for i in items):
        states[-1]['volume_ml'] = round(sum(i['ml'] for i in items) + total_water, 3)
        states[-1]['basis'] = 'declared_final_water_scenario'
    if context.get('process', {}).get('clarification') in {'none', 'strained'} and transformed:
        raise ValueError('clarification 标签与 clarify 步骤冲突')
    return {'status': 'declared', 'states': states, 'warnings': warnings,
            'transformed': transformed, 'additional_water_ml': total_water,
            'note': '步骤是用户声明或试验计划，不能证明实际执行；未测融水与澄清损失不补默认值。'}
