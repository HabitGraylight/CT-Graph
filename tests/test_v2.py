"""Synthetic fixtures only; all records are isolated from the user's database."""
import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from cocktail import engine, graph, planning, experiments, learning
from cocktail.knowledge import ROOT
from scripts.advise import dispatch

RECIPE='gin 45ml,lemon_juice 25ml,simple_syrup 20ml'
CONTEXT={'dilution_ml':20,'composition':[
    {'name':n,'abv':a,'sugar_g_l':s,'acid_g_l':ac,'basis':'assumption','source':'synthetic fixture'}
    for n,a,s,ac in [('gin',40,0,0),('lemon_juice',0,20,50),('simple_syrup',0,600,0)]]}


class GraphProcessTests(unittest.TestCase):
    def evaluate(self,context,recipe=RECIPE,frame='sour'):
        return engine.evaluate(frame,recipe,'shake',context)

    def test_material_batch_measurement_and_claim_provenance(self):
        context={**CONTEXT,'materials':[{'name':'gin','product_label':'Synthetic gin','variant':'test','batch':'batch-a'}]}
        evaluation=self.evaluate(context); result=graph.from_evaluation(evaluation)
        self.assertEqual(result,graph.from_evaluation(evaluation))
        nodes={n['id']:n for n in result['nodes']}
        self.assertTrue({'Batch','ProductVariant','IngredientUse','CompositionRecord','MechanismClaim','Resolution'} <= {n['type'] for n in nodes.values()})
        self.assertTrue(all(e['source'] in nodes and e['target'] in nodes for e in result['edges']))
        self.assertTrue(any(e['relation']=='SUPPORTED_BY' for e in result['edges']))
        other=copy.deepcopy(context);other['materials'][0]['batch']='batch-b'
        self.assertNotEqual(evaluation['judge']['recipe_id'],self.evaluate(other)['judge']['recipe_id'])

    def test_unknown_identity_remains_a_resolution_without_guessed_material(self):
        result=graph.from_evaluation(self.evaluate({},RECIPE+', unknown_fixture 10ml'))
        node=next(n for n in result['nodes'] if n['type']=='Resolution' and n['status']=='unknown')
        self.assertFalse(any(e['source']==node['id'] and e['relation']=='RESOLVES_TO' for e in result['edges']))

    def test_shared_claims_merge_without_overwriting_recipe_applications(self):
        combined=graph.Graph()
        recipe=RECIPE+', milk 15ml'
        for context in ({},{'intent':'milk_clarified'}):
            projection=graph.from_evaluation(self.evaluate(context,recipe))
            for node in projection['nodes']: combined.node(**node)
            for edge in projection['edges']: combined.edge(**edge)
        result=combined.export()
        applications=[n for n in result['nodes'] if n['type']=='MechanismApplication']
        self.assertGreater(len({n['applicability'] for n in applications}),1)

    def test_steps_control_carbonated_shake_and_completion_preserves_row_binding(self):
        recipe='soda 60ml,gin 45ml,lemon_juice 25ml,simple_syrup 20ml'
        context={'process':{'steps':[{'op':'add','uses':[1,2,3]},{'op':'shake','water_ml':20},{'op':'add','uses':[0]},{'op':'serve'}]}}
        result=self.evaluate(context,recipe,'collins')
        self.assertNotIn('shake_carbonated',{r['id'] for r in result['judge']['risks']})
        completed=engine.complete('collins',recipe,context=context)
        self.assertFalse(completed['blocked'])
        self.assertNotIn('shake_carbonated',{r['id'] for r in completed['evaluation']['judge']['risks']})
        context['process']['steps']=[{'op':'add','uses':[0,1,2,3]},{'op':'shake','water_ml':20},{'op':'serve'}]
        self.assertIn('shake_carbonated',{r['id'] for r in self.evaluate(context,recipe,'collins')['judge']['risks']})

    def test_water_mass_balance_and_unknown_melting(self):
        context=copy.deepcopy(CONTEXT)
        context['process']={'steps':[{'op':'add','uses':[0,1,2]},{'op':'shake','water_ml':20},{'op':'strain'},{'op':'serve'}]}
        c=self.evaluate(context)['judge']['composition']
        self.assertAlmostEqual(c['estimates']['abv']['value'],16.364,places=3)
        self.assertEqual(c['process_trace']['states'][-1]['volume_ml'],110)
        context['dilution_ml']=25
        with self.assertRaises(ValueError): self.evaluate(context)
        context.pop('dilution_ml');context['process']['steps'][1].pop('water_ml')
        c=self.evaluate(context)['judge']['composition']
        self.assertIsNone(c['process_trace']['states'][-1]['volume_ml'])
        self.assertIsNone(c['additional_water_ml'])

    def test_clarification_is_state_transition_even_without_legacy_intent(self):
        context={**CONTEXT,'process':{'steps':[{'op':'add','uses':[0,1,2]},{'op':'clarify'},{'op':'serve'}]}}
        context.pop('dilution_ml')
        c=self.evaluate(context)['judge']['composition']
        self.assertIsNone(c['estimates']['abv']['value'])
        self.assertIsNotNone(c['input_scenario_estimates']['abv']['value'])

    def test_invalid_steps_and_materials_fail_closed(self):
        for process in [
            {'steps':[{'op':'shake'},{'op':'serve'}]},
            {'steps':[{'op':'add','uses':[0,1]},{'op':'serve'}]},
            {'steps':[{'op':'add','uses':[0,1,2]},{'op':'add','uses':[0]},{'op':'serve'}]},
            {'steps':[{'op':'add','uses':[True]},{'op':'serve'}]},
            {'steps':[{'op':'add','uses':[0,1,2]},{'op':'serve'},{'op':'shake'}]},
        ]:
            with self.subTest(process=process),self.assertRaises(ValueError):self.evaluate({'process':process})
        with self.assertRaises(ValueError):self.evaluate({'materials':[{'name':'vodka','batch':'x'}]})


class CandidateExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'data/work')
        self.patch=patch.object(learning,'DB',Path(self.temp.name)/'trials.sqlite');self.patch.start()
    def tearDown(self):self.patch.stop();self.temp.cleanup()

    def plan(self,**kwargs):
        return experiments.create(recipe=RECIPE,context=copy.deepcopy(CONTEXT),**kwargs)

    def observe_pair(self,plan,timepoint=0):
        return [experiments.observe(plan['id'],s['serving_id'],{'tasted':True,'overall_liking':7,'ratings':{'balance':7}},
                                   {'as_planned':True,'timepoint_s':timepoint,'intensities':{'sweet':6}}) for s in plan['input']['samples']]

    def test_candidates_preserve_original_and_show_linked_concentration_changes(self):
        c=copy.deepcopy(CONTEXT);r=planning.recommend(recipe=RECIPE,context=c)
        self.assertFalse(r['blocked']);self.assertEqual(c,CONTEXT)
        candidates={x['id']:x for x in r['candidates']}
        self.assertEqual(candidates['reference']['snapshot']['recipe'][2]['amount'],20)
        self.assertGreater(candidates['less_syrup']['composition_changes']['abv']['delta'],0)
        self.assertEqual(candidates['water_swap']['composition_changes']['abv']['delta'],0)
        self.assertEqual(candidates['water_swap']['composition_changes']['acid_g_l']['delta'],0)
        self.assertLess(candidates['water_swap']['composition_changes']['sugar_g_l']['delta'],0)
        self.assertTrue(candidates['less_syrup']['evidence_ids'])
        self.assertTrue(all(x['taste_prediction'] is None for x in r['candidates']))

    def test_candidates_respect_unknowns_avoid_and_scope(self):
        r=planning.recommend(recipe=RECIPE,avoid='water')
        self.assertEqual(len(r['candidates']),2)
        self.assertTrue(all(x['composition_changes']['abv']['after'] is None for x in r['candidates']))
        self.assertTrue(planning.recommend(frame='martini',recipe=RECIPE)['blocked'])
        self.assertTrue(planning.recommend(recipe=RECIPE,method='stir')['blocked'])
        self.assertTrue(planning.recommend(recipe=RECIPE,context={'intent':'milk_clarified'})['blocked'])

    def test_evidence_status_and_measured_zero_sugar_change_generation(self):
        from cocktail import judge
        kb=judge.knowledge();next(r for r in kb['rules'] if r['id']=='sweet_acid')['status']='retired'
        with patch.object(judge,'knowledge',return_value=kb):
            self.assertTrue(planning.recommend(recipe=RECIPE)['blocked'])
        context=copy.deepcopy(CONTEXT);context['composition'][2]['sugar_g_l']=0
        self.assertTrue(planning.recommend(recipe=RECIPE,context=context)['blocked'])

    def test_plan_retry_and_concurrent_creation_retain_assignment(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.plan(request_id='synthetic-plan-001'),range(2)))
        self.assertEqual(results[0]['input'],results[1]['input'])
        self.assertEqual(len(experiments.history()['experiments']),1)
        self.assertEqual({s['candidate_id'] for s in results[0]['input']['samples']},{'reference','water_swap'})

    def test_observation_and_choice_retries_preserve_original_knowledge_snapshot(self):
        plan=self.plan();samples=plan['input']['samples']
        args=dict(experiment_id=plan['id'],serving_id=samples[0]['serving_id'],tasting={'tasted':True},
                  observation={'as_planned':True,'timepoint_s':0},request_id='retry-observation-001')
        saved=experiments.observe(**args)
        with patch.object(engine,'evaluate',side_effect=AssertionError('Retry must not reevaluate')):
            self.assertEqual(experiments.observe(**args)['input'],saved['input'])
        with self.assertRaises(ValueError):experiments.observe(**{**args,'tasting':{'tasted':True,'overall_liking':2}})
        experiments.observe(plan['id'],samples[1]['serving_id'],{'tasted':True},{'as_planned':True,'timepoint_s':0})
        chosen=experiments.choose(plan['id'],'A',request_id='retry-choice-001')
        experiments.observe(plan['id'],samples[0]['serving_id'],{'tasted':True,'overall_liking':2},
                            {'as_planned':True,'timepoint_s':0},supersedes=saved['id'])
        self.assertEqual(experiments.choose(plan['id'],'A',request_id='retry-choice-001')['input'],chosen['input'])
        self.assertEqual(experiments.preference('local',plan['input']['reference_recipe_id'])['eligible_pairs'],0)

    def test_real_observation_required_and_same_cup_is_not_independent_pair(self):
        plan=self.plan()
        with self.assertRaises(ValueError):experiments.choose(plan['id'],'A')
        s=plan['input']['samples'][0]
        with self.assertRaises(ValueError):experiments.observe(plan['id'],s['serving_id'],{'tasted':False},{'as_planned':True,'timepoint_s':0})
        self.observe_pair(plan);self.observe_pair(plan,120)
        experiments.choose(plan['id'],'A');experiments.choose(plan['id'],'A',120)
        p=experiments.preference('local',plan['input']['reference_recipe_id'])
        self.assertEqual(p['eligible_pairs'],1);self.assertIsNone(p['preferred_intervention'])

    def test_temperature_is_a_timepoint_observation_not_a_new_recipe(self):
        plan=self.plan();s=plan['input']['samples'][0]
        first=experiments.observe(plan['id'],s['serving_id'],{'tasted':True},
                                  {'as_planned':True,'timepoint_s':0,'temperature_c':-3})
        later=experiments.observe(plan['id'],s['serving_id'],{'tasted':True},
                                  {'as_planned':True,'timepoint_s':120,'temperature_c':2})
        self.assertEqual(first['input']['actual_recipe_id'],later['input']['actual_recipe_id'])
        self.assertEqual(later['input']['observed_conditions']['temperature_c'],2)

    def test_synthetic_and_deviating_observations_do_not_teach_preferences(self):
        plan=self.plan(data_kind='synthetic');self.observe_pair(plan);experiments.choose(plan['id'],'A')
        self.assertEqual(experiments.preference('local',plan['input']['reference_recipe_id'])['eligible_pairs'],0)
        plan=self.plan()
        for s in plan['input']['samples']:
            experiments.observe(plan['id'],s['serving_id'],{'tasted':True},{'as_planned':True,'timepoint_s':0,'deviations':'different measured temperature'})
        experiments.choose(plan['id'],'A')
        self.assertEqual(experiments.preference('local',plan['input']['reference_recipe_id'])['eligible_pairs'],0)

    def test_corrections_invalidate_old_pairwise_result(self):
        plan=self.plan();obs=self.observe_pair(plan);experiments.choose(plan['id'],'A')
        original=obs[0]
        experiments.observe(plan['id'],original['input']['serving_id'],{'tasted':True,'overall_liking':3},
                            {'as_planned':True,'timepoint_s':0},supersedes=original['id'])
        self.assertEqual(experiments.preference('local',plan['input']['reference_recipe_id'])['eligible_pairs'],0)
        self.assertEqual(len(experiments.active_observations(plan['id'])),2)

    def test_only_matched_reference_and_taster_feedback_changes_ranking(self):
        for _ in range(3):
            plan=self.plan();self.observe_pair(plan)
            code=next(s['code'] for s in plan['input']['samples'] if s['candidate_id']=='water_swap')
            experiments.choose(plan['id'],code)
        r=planning.recommend(recipe=RECIPE,context=CONTEXT)
        self.assertEqual(r['candidates'][0]['id'],'water_swap')
        self.assertEqual(planning.recommend(recipe=RECIPE,context=CONTEXT,taster='someone-else')['candidates'][0]['id'],'reference')
        self.assertEqual(planning.recommend(recipe=RECIPE.replace('45','50'),context=CONTEXT)['candidates'][0]['id'],'reference')

    def test_cli_actions_and_observation_graph(self):
        result=dispatch({'action':'graph','recipe':RECIPE,'frame':'sour','method':'shake'})
        self.assertEqual(result['schema_version'],'2.0.0')
        plan=dispatch({'action':'experiment_create','recipe':RECIPE,'frame':'sour','data_kind':'synthetic'})
        obs=self.observe_pair(plan)[0]
        self.assertIn('Observation',{n['type'] for n in obs['input']['trace']['nodes']})
        self.assertEqual(len(dispatch({'action':'experiment_history'})['experiments']),1)


if __name__=='__main__':unittest.main()
