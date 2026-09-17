import unittest
from cocktail import engine, design


class DesignTests(unittest.TestCase):
    def test_measurement_prompts_do_not_invent_scores(self):
        r = engine.evaluate('sour', '金酒 45ml,柠檬汁 25ml,糖浆 20ml', 'shake')
        prompts = r['judge']['design_review']['prompts']
        self.assertIn('missing_service_state', {p['id'] for p in prompts})
        self.assertTrue(all(p['numeric_score_effect'] is None for p in prompts))
        self.assertIsNone(r['judge']['sensory_total'])
        self.assertEqual(r['score'], 100)

    def test_supplied_service_measurements_are_respected(self):
        r = engine.evaluate('sour', '金酒 45ml,柠檬汁 25ml,糖浆 20ml', 'shake',
                            {'dilution_ml': 20, 'temperature_c': -3})
        self.assertNotIn('missing_service_state', {p['id'] for p in r['judge']['design_review']['prompts']})

    def test_framework_mapping_is_not_an_invented_flip_engine(self):
        roots = design.catalog()['roots']
        self.assertEqual(len(roots), 6)
        self.assertEqual(next(r['frames'] for r in roots if r['id'] == 'flip'), [])
        self.assertEqual(sum('collins' in r['frames'] for r in roots), 2)

    def test_wet_martini_explains_target_version(self):
        r = engine.evaluate('martini', '金酒 60ml,干味美思 30ml', 'stir')
        self.assertIn('version_specific_ratio', {p['id'] for p in r['judge']['design_review']['prompts']})


if __name__ == '__main__':
    unittest.main()
