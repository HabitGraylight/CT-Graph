import json
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cocktail.normalization import resolve,parse_items,BY_ID,key
from cocktail.knowledge import FRAMEWORKS,ROOT
from cocktail.engine import evaluate,complete,compare,pantry_matches,corpus

class AdvisorTests(unittest.TestCase):
    def test_bilingual_brands_preserve_identity(self):
        self.assertEqual(resolve('君度')['ingredient']['id'],resolve('Cointreau')['ingredient']['id'])
        self.assertEqual(resolve('君度')['ingredient']['parent'],'triple_sec')
        self.assertNotEqual(resolve('君度')['ingredient']['id'],resolve('Triple sec')['ingredient']['id'])
        self.assertNotEqual(resolve('金巴利')['ingredient']['id'],resolve('阿佩罗')['ingredient']['id'])
        self.assertNotEqual(resolve('汤力水')['ingredient']['id'],resolve('苏打水')['ingredient']['id'])
        self.assertNotEqual(resolve('马天尼白')['ingredient']['id'],resolve('马天尼干')['ingredient']['id'])
        self.assertNotEqual(resolve('Coconut Cream')['ingredient']['id'],resolve('Cream of Coconut')['ingredient']['id'])

    def test_brand_ambiguity_not_guessed(self):
        for name in ['百加得','马天尼','vermouth','椰浆']:
            self.assertEqual(resolve(name)['status'],'ambiguous')
        self.assertTrue(complete('sour','百加得 45ml')['blocked'])

    def test_parser_multilingual_and_metric(self):
        items=parse_items('金酒 4.5cl，25 ml 青柠汁；原味糖浆 20毫升')
        self.assertEqual([i['ml'] for i in items],[45,25,20])
        self.assertEqual(parse_items('金酒 1 1/2 US fl oz')[0]['ml'],1.5*29.5735295625)

    def test_ambiguous_units_not_converted(self):
        self.assertIsNone(evaluate('sour','金酒 1 oz，柠檬汁 25ml，糖浆 20ml')['score'])
        self.assertIsNone(evaluate('sour','金酒 45，柠檬汁 25ml，糖浆 20ml')['score'])
        self.assertIsNone(parse_items('砂糖 2 tsp')[0]['ml'])
        self.assertIsNone(parse_items('青柠 20ml')[0]['ml'])

    def test_bad_quantities_rejected(self):
        for v in [-1,0,float('nan'),float('inf'),True,10001,'1/0']:
            with self.assertRaises(ValueError):parse_items([{'name':'gin','amount':v,'unit':'ml'}])
        with self.assertRaises(ValueError):parse_items({'name':'gin'})

    def test_scoring_is_scale_invariant_and_diagnoses_imbalance(self):
        a=evaluate('sour','波本 45ml，柠檬汁 25ml，糖浆 20ml','shake')
        b=evaluate('sour','波本 90ml，柠檬汁 50ml，糖浆 40ml','shake')
        bad=evaluate('sour','波本 45ml，柠檬汁 60ml，糖浆 5ml','shake')
        self.assertEqual(a['score'],100)
        self.assertEqual(a['score'],b['score'])
        self.assertLess(bad['score'],a['score'])
        self.assertEqual(next(c for c in bad['checks'] if c['slot']=='acid')['state'],'high')
        self.assertIsNone(a['taste_score'])

    def test_unknown_and_unmodelled_extras_block_score(self):
        self.assertIsNone(evaluate('sour','神秘酒 45ml，柠檬汁 25ml，糖浆 20ml')['score'])
        self.assertIsNone(evaluate('sour','金酒 45ml，柠檬汁 25ml，糖浆 20ml，菠萝汁 80ml')['score'])
        self.assertIsNone(evaluate('sour','')['score'])

    def test_rich_syrup_uses_less_and_existing_amount_is_kept(self):
        r=complete('sour','金酒 45ml，青柠汁 25ml','浓糖浆')
        sweet=next(i for i in r['recipe'] if i['slot']=='sweet')
        self.assertAlmostEqual(sweet['amount'],20/1.5,places=2)
        r=complete('sour','金酒 55ml，浓糖浆 30ml','青柠汁',preference='drier')
        self.assertEqual(next(i for i in r['recipe'] if i['slot']=='sweet')['amount'],30)
        self.assertEqual(next(i for i in r['recipe'] if i['slot']=='base')['amount'],55)

    def test_all_frameworks_generate_valid_recipe_and_score(self):
        for f in FRAMEWORKS:
            with self.subTest(frame=f['id']):
                r=complete(f['id'],'',','.join(s['default'] for s in f['slots']))
                self.assertFalse(r['blocked'])
                self.assertFalse(r['shopping'])
                self.assertEqual(r['evaluation']['missing_slots'],[])
                self.assertEqual(r['evaluation']['score'],100)

    def test_pantry_priority_and_exclusion(self):
        r=complete('negroni','金酒 30ml','金巴利、马天尼红')
        self.assertFalse(r['shopping'])
        self.assertIn('martini_rosso',[i['name'] for i in r['recipe']])
        r=complete('daisy','','君度、青柠汁、银龙舌兰',avoid='三重橙酒')
        self.assertNotIn('cointreau',[i['name'] for i in r['recipe']])
        self.assertTrue(complete('sour','金酒 45ml',avoid='金酒')['blocked'])
        with self.assertRaises(ValueError):complete('sour',avoid='不明酒')

    def test_nonguessed_alternatives_and_gas_handling(self):
        r=complete('negroni','金酒 30ml','阿佩罗、甜红味美思')
        self.assertEqual(r['shopping'][0]['name'],'campari')
        r=evaluate('collins','金酒 45ml，柠檬汁 25ml，糖浆 15ml，苏打水 60ml','shake')
        self.assertTrue(any('密闭摇壶' in s for s in r['suggestions']))

    def test_completion_does_not_overwrite_unclear_unit(self):
        self.assertTrue(complete('sour','金酒 2 oz','柠檬汁、糖浆')['blocked'])
        self.assertTrue(complete('sour','金酒 45ml，伏特加','柠檬汁、糖浆')['blocked'])

    def test_recommended_alternatives_respect_exclusions(self):
        r=complete('daisy','','君度、青柠汁、银龙舌兰',avoid='三重橙酒')
        self.assertNotIn('cointreau',[i['id'] for s in r['alternatives'] for i in s['options']])
        self.assertNotIn('triple_sec',[i['id'] for s in r['alternatives'] for i in s['options']])

    @unittest.skipUnless((ROOT/'data/raw/iba_official/recipes').exists(), "Local source corpus is not included in this repository")
    def test_framework_evidence_resolves_to_collected_sources(self):
        for frame in FRAMEWORKS:
            for url in frame['source_urls']:
                self.assertTrue((ROOT/'data/raw/iba_official/recipes'/(url.rstrip('/').split('/')[-1]+'.html')).exists(),url)

    @unittest.skipUnless(bool(corpus()), "Local source corpus is not included in this repository")
    def test_recipe_comparison_and_provenance(self):
        result=compare('尼格罗尼')
        self.assertGreaterEqual(len(result['versions']),3)
        self.assertEqual(result['comparison']['reference_reason'],'IBA official')
        self.assertTrue(all(r['source_url'].startswith('https://') for r in result['versions']))
        bar=next(r for r in result['versions'] if r['dataset']=='bar_assistant')
        changes=next(d for d in result['comparison']['differences'] if d['variant_id']==bar['id'])
        self.assertEqual(changes['ingredient_differences'],[])
        ids={r['id'] for r in corpus()}
        self.assertEqual(len(ids),1241)
        self.assertTrue(all(i['canonical_id'] in BY_ID for r in corpus() for i in r['ingredients'] if i['status']=='matched'))

    @unittest.skipUnless(bool(corpus()), "Local source corpus is not included in this repository")
    def test_pantry_does_not_ignore_unknown_recipe_components(self):
        r=pantry_matches('金酒、金巴利、甜红味美思')
        self.assertTrue(any(i['name']=='Negroni' and not i['missing'] for i in r['recipes']))
        r=pantry_matches('gin')
        self.assertFalse(any(i['name']=='Negroni' and not i['missing'] for i in r['recipes']))

if __name__=='__main__':unittest.main()
