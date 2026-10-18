"""Explainable personal intensity targets; not a fitted taste predictor."""
DIMENSIONS = {'sweet':'甜感','sour':'酸感','bitter':'苦感','strength':'酒精感','body':'厚重感','aroma':'香气强度'}


def baseline(profile, tastings, frame=None):
    relevant = [t for t in tastings if not frame or t.get('frame') == frame]
    liked = [t for t in relevant if t['liking'] >= 7]
    prior = (profile or {}).get('preferences', {})
    targets = {}
    for key, label in DIMENSIONS.items():
        values = [t['intensities'][key] for t in liked if key in t.get('intensities', {})]
        stated = prior.get(key)
        n = len(values)
        value = ((sum(values) + 3 * stated) / (n + 3) if stated is not None and n
                 else sum(values) / n if n else stated)
        targets[key] = {'label':label, 'value':round(value, 2) if value is not None else None,
                        'samples':n, 'stated':stated, 'ready':n>=3,
                        'evidence':'初步实饮参考' if n>=3 else '少量实饮' if n else '仅自报' if stated is not None else '未记录',
                        'observed_range':[min(values),max(values)] if values else None,
                        'basis':'自报偏好 + 喜欢的实饮' if n and stated is not None else '喜欢的实饮' if n else '自报偏好' if stated is not None else '尚未记录'}
    ready = sum(t['ready'] for t in targets.values())
    return {'frame':frame, 'tasted_recipes':len(relevant), 'liked_recipes':len(liked), 'targets':targets,
            'ready_dimensions':ready,
            'confidence':f'{ready}/6 项有初步实饮参考' if ready else '待补充风味强度记录',
            'method':'最近 200 个配方版本中，喜欢程度 ≥7 的实饮强度均值；自报偏好作为权重 3 的起点。每个版本仅保留该用户最新记录。没有自报目标时，每项至少 3 个有效强度记录才用于自动试配选择；此门槛是产品规则，不代表统计置信度。范围是已记录的最小/最大值，不是置信区间。不是因果估计或味觉预测。'}


def low_sweet_target(target):
    sweet = target['targets']['sweet']
    # An explicit preference can guide a trial immediately; sparse observations alone cannot.
    supported = sweet['stated'] is not None or sweet['ready']
    return supported and sweet['value'] is not None and sweet['value'] <= 4


def personalize(recommendation, target):
    if recommendation.get('blocked'):return recommendation
    chosen = 'less_syrup' if low_sweet_target(target) else 'reference'
    # Keep the engine's safety-first ordering. The target only identifies an experiment to try.
    ids = {c['id'] for c in recommendation['candidates']}
    recommendation['suggested_trial'] = chosen if chosen in ids else 'reference'
    recommendation['baseline'] = target
    recommendation['personal_note'] = ('你的甜感目标较低，可先对照原版与少糖浆版；这不是预测你一定更喜欢减糖。'
                                       if chosen == 'less_syrup' else '先以原版为参照，再记录真实感受；当前没有足够理由自动改动已有用量。')
    sweet = target['targets']['sweet']
    recommendation['personal_note'] += f" 甜感依据：{sweet['basis']}，{sweet['samples']} 个喜欢的版本有甜感记录。"
    return recommendation
