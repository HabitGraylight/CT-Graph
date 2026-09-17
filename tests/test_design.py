import unittest
from cocktail import engine, design, learning


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

    def test_processing_selects_prompts_and_is_preserved_in_snapshot(self):
        context={'process':{'batched':True,'service':'up','carbonation':'force',
                           'preparations':[{'name':'柠檬汁','state':'clarified'}]}}
        r=engine.evaluate('sour','金酒 45ml,柠檬汁 25ml,糖浆 20ml','shake',context)['judge']
        ids={p['id'] for p in r['design_review']['prompts']}
        self.assertTrue({'batch_aeration','service_evolution','carbonation_target',
                         'prepared_ingredient_identity','clarified_shake_texture'}<=ids)
        self.assertEqual(r['snapshot']['context'],context)
        self.assertEqual(r['composition']['process_stage'],'mixing_scenario')
        self.assertIsNone(r['sensory_total'])

    def test_whole_drink_clarification_does_not_mislabel_input_as_final(self):
        base={'composition':[{'name':'gin','abv':40,'basis':'label','source':'synthetic fixture'}]}
        for context in [{**base,'intent':'milk_clarified'},
                        {**base,'process':{'clarification':'whole_drink'}}]:
            with self.subTest(context=context):
                r=engine.evaluate('martini','金酒 60ml','stir',context)['judge']['composition']
                self.assertIsNone(r['estimates']['abv']['value'])
                self.assertEqual(r['input_scenario_estimates']['abv']['value'],40)
                self.assertEqual(r['process_stage'],'whole_drink_transformation')
        strained=engine.evaluate('martini','金酒 60ml','stir',
                                 {**base,'process':{'clarification':'strained'}})['judge']
        self.assertEqual(strained['composition']['estimates']['abv']['value'],40)
        self.assertIn('straining_is_not_clarification',{p['id'] for p in strained['design_review']['prompts']})

    def test_process_rejects_ambiguous_or_unrelated_state(self):
        for process in [[],{'batched':1},{'service':[]},{'carbonation':'maybe'},
                        {'pressure':40},{'preparations':[{'name':'伏特加','state':'heated'}]},
                        {'preparations':[{'name':'gin','state':'fresh'},{'name':'金酒','state':'heated'}]}]:
            with self.subTest(process=process),self.assertRaises(ValueError):
                engine.evaluate('martini','金酒 60ml','stir',{'process':process})
        with self.assertRaises(ValueError):
            engine.evaluate('martini','金酒 60ml','stir',{'intent':'milk_clarified','process':{'clarification':'none'}})

    def test_clarified_design_does_not_auto_tune_input_ratio(self):
        r=learning.improve('sour','金酒 45ml,柠檬汁 25ml,糖浆 50ml','shake',
                           {'process':{'clarification':'whole_drink'}})
        self.assertTrue(r['blocked'])
        self.assertIn('成分保留未知',r['reason'])


if __name__ == '__main__':
    unittest.main()
