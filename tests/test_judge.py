import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from unittest.mock import patch
from cocktail import engine, judge, learning
from cocktail.knowledge import ROOT
from scripts.advise import dispatch
from scripts.review_knowledge import validate
from scripts import review_knowledge

SOUR='金酒 45ml, 柠檬汁 25ml, 原味糖浆 20ml'


class JudgeTests(unittest.TestCase):
    def test_unobserved_dimensions_never_get_sensory_scores(self):
        result=engine.evaluate('sour',SOUR,'shake')['judge']
        self.assertEqual(len(result['dimensions']),7)
        self.assertIsNone(result['sensory_total'])
        self.assertTrue(all(d['sensory_score'] is None for d in result['dimensions']))
        self.assertTrue(all(d['plan_score'] is None for d in result['dimensions'] if d['id'] in {'aroma','appearance','texture','expression'}))
        self.assertIsNone(result['composition']['estimates']['abv']['value'])
        self.assertIn('sweet_acid',{r['id'] for r in result['interactions']})

    def test_martini_does_not_require_acid_sugar_or_hiding_alcohol(self):
        r=engine.evaluate('martini','金酒 60ml, 干味美思 10ml','stir')['judge']
        self.assertEqual(r['risks'],[])
        self.assertIn('可作为试饮候选',r['verdict'])

    def test_milk_curds_are_intent_dependent_and_coconut_has_no_casein(self):
        recipe=SOUR+', 牛奶 15ml'
        plain=engine.evaluate('sour',recipe,'shake')['judge']
        clarified=engine.evaluate('sour',recipe,'shake',{'intent':'milk_clarified'})['judge']
        self.assertIn('curdling_check',{r['id'] for r in plain['risks']})
        self.assertNotIn('curdling_check',{r['id'] for r in clarified['risks']})
        coconut=engine.evaluate('sour',SOUR+', coconut_milk 15ml','shake')['judge']
        self.assertNotIn('milk_acid',{r['id'] for r in coconut['interactions']})

    def test_gas_warning_removed_after_separate_addition(self):
        r=learning.improve('collins',SOUR+', 苏打水 60ml','shake')
        self.assertFalse(r['blocked']);self.assertEqual(r['candidate']['method'],'shake_top')
        self.assertNotIn('shake_carbonated',{i['id'] for i in r['after']['judge']['risks']})

    def test_composition_requires_coverage_and_preserves_assumptions(self):
        specs=[{'name':n,'abv':a,'sugar_g_l':s,'acid_g_l':ac,'basis':'assumption','source':'test scenario'}
               for n,a,s,ac in [('gin',40,0,0),('lemon_juice',0,20,50),('simple_syrup',0,600,0)]]
        ctx={'composition':specs,'dilution_ml':20}
        r=engine.evaluate('sour',SOUR,'shake',ctx)['judge']['composition']
        self.assertAlmostEqual(r['estimates']['abv']['value'],18/110*100,places=3)
        self.assertAlmostEqual(r['estimates']['sugar_g_l']['value'],12.5/.11,places=3)
        self.assertAlmostEqual(r['estimates']['acid_g_l']['value'],1.25/.11,places=3)
        self.assertEqual(len(r['estimates']['abv']['assumed_ingredients']),3)
        ctx['composition']=specs[:-1]
        r=engine.evaluate('sour',SOUR,'shake',ctx)['judge']['composition']
        self.assertIsNone(r['estimates']['sugar_g_l']['value'])
        self.assertIn('原味糖浆',r['estimates']['sugar_g_l']['missing'])

    def test_invalid_composition_and_context_do_not_get_silent_defaults(self):
        for ctx in [{'dilution_ml':-1},{'temperature_c':True},{'final_ph':float('nan')},{'bogus':1},
                    {'composition':[{'name':'gin','abv':40}]},
                    {'composition':[{'name':'vodka','abv':40,'basis':'label','source':'bottle'}]}]:
            with self.subTest(ctx=ctx),self.assertRaises(ValueError):engine.evaluate('sour',SOUR,'shake',ctx)

    def test_unknown_ingredient_and_unknown_volume_stay_unknown(self):
        r=engine.evaluate('sour',SOUR+', mystery cordial 10ml','shake')['judge']
        self.assertIn('unresolved',{r['id'] for r in r['risks']})
        self.assertIsNone(r['composition']['estimates']['abv']['value'])
        r=engine.evaluate('old_fashioned','波本 45ml, 原味糖浆 5ml, 安格仕苦精 2dash','stir')['judge']
        self.assertTrue(r['composition']['missing_volume'])

    def test_all_knowledge_references_and_profiles_are_valid(self):
        kb=judge.knowledge();self.assertEqual(validate(kb)['profiles'],127)
        for id in ['port','lillet','absinthe']:
            self.assertIn('ethanol',next(p for p in kb['profiles'] if p['ingredient_id']==id)['component_ids'])
        bad=copy.deepcopy(kb);bad['rules'][0]['numeric_score_effect']=2
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(kb);bad['rules'][0]['source_ids']=['unknown']
        with self.assertRaises(ValueError):validate(bad)

    def test_review_queue_date_does_not_invalidate_old_papers(self):
        self.assertFalse(any(s['needs_review'] for s in judge.knowledge_status(date(2026,9,15))['sources']))
        self.assertTrue(all(s['needs_review'] for s in judge.knowledge_status(date(2027,9,16))['sources']))

    def test_review_publication_archives_previous_version(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data/work') as folder:
            root=Path(folder);target=root/'data/knowledge/judge.json';target.parent.mkdir(parents=True)
            old=judge.knowledge();target.write_text(json.dumps(old),encoding='utf-8')
            candidate=copy.deepcopy(old);candidate['version']='isolated-publication-test'
            path=root/'candidate.json';path.write_text(json.dumps(candidate),encoding='utf-8')
            with patch.object(review_knowledge,'ROOT',root):
                result=review_knowledge.publish(path,'isolated synthetic publication test')
                with self.assertRaises(ValueError):review_knowledge.publish(path,'same-version retry')
            self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['version'],candidate['version'])
            archive=root/'data/knowledge/history'
            self.assertEqual(json.loads((archive/(result['previous_sha256']+'.json')).read_text(encoding='utf-8')),old)
            self.assertEqual(len(list(archive.glob('*.audit.json'))),1)


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'data/work')
        self.override=patch.object(learning,'DB',Path(self.temp.name)/'feedback.sqlite');self.override.start()
    def tearDown(self):self.override.stop();self.temp.cleanup()
    def save(self,**kwargs):
        return learning.save_feedback('sour',SOUR,'shake',tasting={'tasted':True,'ratings':{'balance':6},'descriptors':['too_sweet']},**kwargs)

    def test_trial_replay_is_idempotent_under_concurrency(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.save(request_id='same-trial-001'),range(2)))
        self.assertEqual(len(learning.records()),1)
        self.assertTrue(any(r.get('duplicate') for r in results))
        self.assertIsNone(results[0]['input']['sensory']['total'])
        self.assertEqual(learning.preference_profile('sour')['tasted_trials'],1)

    def test_retry_after_knowledge_update_retains_original_review(self):
        old=self.save(request_id='retry-version-001')
        kb=judge.knowledge();kb['version']='next-test-version'
        with patch.object(judge,'knowledge',return_value=kb):again=self.save(request_id='retry-version-001')
        self.assertTrue(again['duplicate'])
        self.assertEqual(again['input']['knowledge_version'],old['input']['knowledge_version'])

    def test_unobserved_notes_cannot_become_tasting_scores_or_preferences(self):
        with self.assertRaises(ValueError):learning.sensory_report({'tasted':False,'ratings':{'aroma':8}})
        with self.assertRaises(ValueError):learning.sensory_report({'tasted':True,'ratings':{'aroma':True}})
        with self.assertRaises(ValueError):learning.sensory_report({'tasted':True,'ratings':{'aroma':11}})
        learning.save_feedback('sour',SOUR,'shake',tasting={'tasted':False,'descriptors':['too_sweet']})
        self.assertEqual(learning.preference_profile('sour')['tasted_trials'],0)

    def test_seven_scores_only_sum_when_complete(self):
        r=learning.sensory_report({'tasted':True,'ratings':{id:8 for id,_,_ in judge.DIMENSIONS}})
        self.assertEqual(r['total'],56)

    def test_improvement_is_one_variable_and_keeps_original_trial(self):
        trial=self.save();original=copy.deepcopy(trial)
        r=learning.improve(feedback_id=trial['id'])
        self.assertFalse(r['blocked']);self.assertEqual(r['change']['after'],17.5)
        old=trial['input']['snapshot']['recipe'];new=r['candidate']['recipe']
        self.assertEqual(sum(a!=b for a,b in zip(old,new)),1)
        self.assertIsNone(r['predicted_taste_gain'])
        self.assertEqual(learning.records()[0],original)
        with self.assertRaises(ValueError):learning.improve(feedback_id=trial['id'],recipe='金酒 40ml, 柠檬汁 25ml, 原味糖浆 20ml')

    def test_learning_stays_personal_and_opt_in(self):
        for _ in range(3):self.save()
        self.assertEqual(learning.preference_profile('sour')['completion_preference'],'drier')
        self.assertEqual(learning.preference_profile('martini')['tasted_trials'],0)
        self.assertEqual(learning.preference_profile('sour','another')['tasted_trials'],0)
        base=engine.complete('sour');personal=engine.complete('sour',preference='personal')
        sweet=lambda r:next(i['amount'] for i in r['recipe'] if i['slot']=='sweet')
        self.assertEqual(sweet(base),20);self.assertEqual(sweet(personal),16)
        kept=engine.complete('sour',SOUR,preference='personal')
        self.assertEqual(sweet(kept),20)

    def test_pending_evidence_does_not_change_live_rules(self):
        before=judge.knowledge();r=learning.evidence_note('sweet_acid','https://example.com/study','测试待核验，不能当成论文结论')
        self.assertEqual(r['input']['status'],'pending_review')
        self.assertEqual(judge.knowledge(),before)
        self.assertEqual(len(learning.records('evidence')),1)

    def test_correction_keeps_audit_and_excludes_superseded_scores(self):
        original=self.save()
        corrected=learning.save_feedback('sour',SOUR,'shake',tasting={'tasted':False,'notes':'误填已试饮，实际没有喝'},supersedes_trial_id=original['id'])
        self.assertEqual(len(learning.records()),2)
        self.assertEqual(learning.preference_profile('sour')['tasted_trials'],0)
        with self.assertRaises(ValueError):learning.improve(feedback_id=original['id'])
        with self.assertRaises(ValueError):self.save(supersedes_trial_id=original['id'])
        self.assertEqual(corrected['input']['supersedes_trial_id'],original['id'])

    def test_improvement_honors_exclusions_and_context(self):
        self.assertTrue(learning.improve('sour',SOUR,'shake',avoid='金酒')['blocked'])
        trial=learning.save_feedback('sour',SOUR,'shake',tasting={'tasted':True,'descriptors':['too_strong']})
        r=learning.improve(feedback_id=trial['id'])
        self.assertEqual(r['change']['variable'],'water')
        self.assertIsNone(r['candidate']['context'].get('dilution_ml'))
        self.assertTrue(learning.improve(feedback_id=trial['id'],avoid='水')['blocked'])

    def test_completion_self_review_detects_kept_bad_ratio(self):
        r=engine.complete('sour','金酒 45ml, 柠檬汁 60ml, 原味糖浆 5ml')
        self.assertIsNotNone(r['refinement']);self.assertFalse(r['refinement']['blocked'])
        self.assertEqual(next(i['amount'] for i in r['recipe'] if i['slot']=='acid'),60)
        self.assertEqual(next(i['amount'] for i in r['refinement']['candidate']['recipe'] if i['name']=='lemon_juice'),57.5)

    def test_new_cli_dispatch_actions(self):
        r=dispatch({'action':'judge','frame':'sour','recipe':SOUR,'method':'shake'})
        self.assertIn('judge',r)
        r=dispatch({'action':'knowledge','name':'牛奶'})
        self.assertIn('casein',r['profile']['component_ids'])
        trial=dispatch({'action':'feedback','frame':'sour','recipe':SOUR,'method':'shake','tasting':{'tasted':True,'descriptors':['too_sour']}})
        r=dispatch({'action':'improve','feedback_id':trial['id']})
        self.assertEqual(r['candidate']['frame'],'sour')


if __name__=='__main__':unittest.main()
