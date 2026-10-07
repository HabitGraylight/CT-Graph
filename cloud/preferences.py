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
                        'samples':n, 'stated':stated,
                        'basis':'自报偏好 + 喜欢的实饮' if n and stated is not None else '喜欢的实饮' if n else '自报偏好' if stated is not None else '尚未记录'}
    return {'frame':frame, 'tasted_recipes':len(relevant), 'liked_recipes':len(liked), 'targets':targets,
            'confidence':'初步实饮基线' if len(liked)>=3 else '待积累实饮',
            'method':'最近 200 个配方版本中，喜欢程度 ≥7 的实饮强度均值；自报偏好作为权重 3 的起点。每个版本仅保留该用户最新记录。不是因果估计或味觉预测。'}


def personalize(recommendation, target):
    if recommendation.get('blocked'):return recommendation
    sweet = target['targets']['sweet']
    chosen = 'less_syrup' if sweet['value'] is not None and sweet['value'] <= 4 else 'reference'
    # Keep the engine's safety-first ordering. The target only identifies an experiment to try.
    ids = {c['id'] for c in recommendation['candidates']}
    recommendation['suggested_trial'] = chosen if chosen in ids else 'reference'
    recommendation['baseline'] = target
    recommendation['personal_note'] = ('你的甜感目标较低，可先对照原版与少糖浆版；这不是预测你一定更喜欢减糖。'
                                       if chosen == 'less_syrup' else '先以原版为参照，再记录真实感受；当前没有足够理由自动改动已有用量。')
    return recommendation
