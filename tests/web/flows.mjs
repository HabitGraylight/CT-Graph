// Isolated DOM logic tests, not browser rendering or live Supabase verification.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
const {Window}=await import(process.env.HAPPY_DOM_MODULE||'happy-dom');
const py=spawnSync('python',['-c',`import json
from cocktail.runtime import public_runtime
from cocktail import engine
from cloud.service import advise
with public_runtime():
 print(json.dumps({'catalog':engine.catalog(),'evaluate':advise('evaluate',{'frame':'sour','recipe':'gin 45 ml, lemon juice 25 ml, simple syrup 20 ml','method':'shake'}),'recommend':advise('recommend',{'frame':'sour','recipe':'gin 45 ml, lemon juice 25 ml, simple syrup 20 ml','method':'shake'})}))
`],{cwd:new URL('../../',import.meta.url),encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'}});
assert.equal(py.status,0,py.stderr);
const fixture=JSON.parse(py.stdout);fixture.catalog.configured=true;
const names={sweet:'甜感',sour:'酸感',bitter:'苦感',strength:'酒精感',body:'厚重感',aroma:'香气强度'};
const target={liked_recipes:0,tasted_recipes:0,confidence:'待积累实饮',method:'Synthetic test',targets:Object.fromEntries(Object.entries(names).map(([k,label])=>[k,{label,value:null}]))};
const account={configured:true,user:{id:'synthetic-user',email:'person@example.invalid'},profile:{display_name:'Synthetic',preferences:{}},recipes:[],tastings:[],baseline:target,baselines:Object.fromEntries(fixture.catalog.frameworks.map(f=>[f.id,target]))};
const calls=[];let signedIn=false;
const w=new Window({url:'https://synthetic.example/',settings:{disableJavaScriptFileLoading:true,disableCSSFileLoading:true}});
const errors=[];w.addEventListener('error',e=>errors.push(e.message));
w.HTMLElement.prototype.scrollIntoView=function(){};
w.fetch=async(url,options={})=>{
  const body=options.body?JSON.parse(options.body):null;
  calls.push({url,body});let result;
  if(url.includes('resource=catalog'))result=fixture.catalog;
  else if(url.includes('resource=state'))result=signedIn?account:{configured:true,user:null};
  else if(url.includes('resource=community'))result={configured:true,recipes:account.recipes.filter(r=>r.visibility==='public').map(r=>({...r,author:'Synthetic',voters:0,average_liking:null,ranking_score:null,qualified:false,intensities:{}}))};
  else if(body.action==='login'){signedIn=true;result={message:'登录成功'};}
  else if(body.action==='logout'){signedIn=false;result={message:'已退出'};}
  else if(body.action==='evaluate')result=fixture.evaluate;
  else if(body.action==='recommend')result=fixture.recommend;
  else if(body.action==='profile'){account.profile={display_name:body.display_name,preferences:body.preferences};result=[];}
  else if(body.action==='save_recipe'){const row={...body,id:'20000000-0000-4000-8000-000000000001',visibility:'private',created_at:'2026-01-01T00:00:00Z'};account.recipes.push(row);result=[row];}
  else if(body.action==='taste'){account.tastings=[{...body,id:'synthetic-taste',title:'Synthetic',frame:'sour',updated_at:'2026-01-01T00:00:00Z'}];result=[];}
  else if(body.action==='visibility'){account.recipes[0].visibility=body.visibility;result=[];}
  else throw new Error('Unexpected request '+JSON.stringify({url,body}));
  return {ok:true,json:async()=>structuredClone(result)};
};
w.document.write(await readFile(new URL('../../cloud/web/index.html',import.meta.url),'utf8'));
w.eval(await readFile(new URL('../../cloud/web/app.js',import.meta.url),'utf8'));
const $=id=>w.document.getElementById(id);
const flush=async()=>{for(let i=0;i<15;i++)await new Promise(setImmediate);};
const submit=id=>$(id).dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:$(id).querySelector('[type=submit]')}));
let count=0;const ok=(v,msg)=>{assert.ok(v,msg);count++;};
await flush();
ok(w.document.querySelectorAll('.frame-button').length===12,'All frameworks render');
ok($('personalize').disabled,'Anonymous personal mode unavailable');
$('try-sour').click();await flush();
ok($('result').textContent.includes('100')&&$('recipe').value.includes('simple_syrup'),'Live engine fixture renders in evaluator: '+$('notice').textContent);
$('recommend').click();await flush();
ok(w.document.querySelectorAll('[data-candidate]').length===3,'Three Sour alternatives rendered');
w.document.querySelector('[data-candidate="1"]').click();await flush();
ok($('recipe').value.includes('17.5'),'Candidate explicitly loads recipe');
$('account-button').click();ok($('auth-dialog').open,'Login dialog opens');
$('auth-switch').click();ok($('auth-title').textContent.includes('味蕾'),'Signup mode exists');
$('auth-recover').click();ok($('password-label').hidden,'Recovery does not request old password');
$('auth-switch').click();$('auth-switch').click();
$('auth-email').value='person@example.invalid';$('auth-password').value='synthetic-password';submit('auth-form');await flush();
ok(!$('personalize').disabled,'Signed-in preferences enabled');
$('account-button').click();await flush();
ok($('profile-chart')===null&&w.document.querySelector('svg.profile-chart'),'Baseline chart rendered');
$('baseline-frame').value='sour';$('baseline-frame').dispatchEvent(new w.Event('change'));ok($('baseline-note').textContent.includes('0 个'),'Frame-specific empty baseline explicit');
$('pref-sweet').value='0';submit('profile-form');await flush();
ok(calls.findLast(c=>c.body?.action==='profile').body.preferences.sweet===0,'Zero preference is preserved');
w.document.querySelector('[data-view="studio"]').click();$('recipe-title').value='<img src=x onerror=alert(1)>';
$('evaluate').click();await flush();$('save-recipe').click();await flush();
ok($('taste-dialog').open,'Saving private version opens real tasting form');
$('actually-tasted').checked=true;$('as-recipe').checked=true;$('taste-liking').value='8';$('taste-sweet').value='3';$('public-vote').checked=true;submit('taste-form');await flush();
const tasting=calls.findLast(c=>c.body?.action==='taste').body;
ok(tasting.tasted&&tasting.intensities.sweet===3&&tasting.public_vote,'Actual tasting and consent sent separately');
w.document.querySelector('[data-view="profile"]').click();await flush();
ok($('my-recipes').querySelectorAll('img').length===0&&$('my-recipes').textContent.includes('<img'),'Recipe title safely escaped');
w.document.querySelector('[data-publish]').click();ok($('publish-dialog').open,'Publication has review step');
$('publish-consent').checked=true;submit('publish-form');await flush();
ok(calls.findLast(c=>c.body?.action==='visibility').body.consent===true,'Publication requires explicit consent');
w.document.querySelector('[data-view="community"]').click();await flush();
ok($('community-list').textContent.includes('不足 3 位'),'Small sample has no manufactured mean');
$('show-qualified').click();ok($('community-list').textContent.includes('还没有达到'),'Qualified-only filter has truthful empty state');
w.document.querySelector('[data-view="profile"]').click();$('logout').click();await flush();
ok($('profile-content').textContent.includes('还差一个开始'),'Logout removes private UI');
ok($('recipe').value===''&&$('recipe-title').value==='','Logout clears private workbench drafts');
ok(errors.length===0,'No DOM runtime errors: '+errors.join(', '));
await w.happyDOM.abort();await w.happyDOM.close();
console.log(`PASS: ${count} isolated DOM assertions; no real browser layout or live Auth claims.`);
