'use strict';
let judgeCatalog=null, trialParent=null, judgeExtraContext={};
const descriptorNames={too_sweet:'偏甜',too_sour:'偏酸',too_bitter:'偏苦',too_strong:'酒精刺激突兀',watery:'水感过重',flat:'气泡不足',aroma_weak:'香气弱',astringent:'过涩',foam_unstable:'泡沫不稳',balanced:'平衡合意'};
function judgeContext(){
  const c={...judgeExtraContext,intent:$('judge-intent').value,appearance_target:$('judge-appearance').value};
  if($('judge-theme').value.trim())c.theme=$('judge-theme').value.trim();
  for(const [input,key] of [['judge-water','dilution_ml'],['judge-temperature','temperature_c']])if($(input).value!=='')c[key]=Number($(input).value);
  return c;
}
function restoreJudgeContext(c={}){
  judgeExtraContext={...c};for(const key of ['intent','appearance_target','theme','dilution_ml','temperature_c'])delete judgeExtraContext[key];
  $('judge-intent').value=c.intent||'classic';$('judge-appearance').value=c.appearance_target||'any';
  $('judge-theme').value=c.theme||'';$('judge-water').value=c.dilution_ml??'';$('judge-temperature').value=c.temperature_c??'';
}
function evidenceLinks(list){return '<div class="source-links">'+list.map(s=>link(s.url,s.title)).join('')+'</div>';}
function judgeHTML(j){
  return `<section class="judge-review"><div class="section-label"><span>JUDGE / 七维复核</span><span class="pill">${esc(j.version)}</span></div><h3>${esc(j.verdict)}</h3><p class="fine">设计检查有分数的项目标为「设计」。实际品鉴七项各 10 分，试饮前留空。</p>
    <div class="judge-dimensions">${j.dimensions.map(d=>`<article class="judge-dimension"><div><strong>${esc(d.name)}</strong><span>${d.plan_score!==null?'设计 '+d.plan_score+'/10':'待观察'}</span></div><p>${esc(d.basis.join(' '))}</p><small>实饮 — /10 · ${esc(d.tasting_prompt)}</small></article>`).join('')}</div>
    ${j.risks.length?`<h4>这一杯先关注</h4><ul class="recommendations">${j.risks.map(r=>`<li>${esc(r.message)}</li>`).join('')}</ul>`:''}
    <details class="evidence"><summary>成分为什么会互相影响？ · ${j.interactions.length} 条提示</summary>${j.interactions.map(r=>`<article class="mechanism"><h4>${esc(r.title)}</h4><p>${esc(r.effect)}</p><p class="fine">适用条件：${esc(r.conditions)}</p><p class="fine">${esc(r.application)}</p><p>验证：${esc(r.verification)}</p>${evidenceLinks(j.sources.filter(s=>r.source_ids.includes(s.id)))}</article>`).join('')||'<p>暂未命中已建模机制，不代表不存在相互作用。</p>'}</details>
    <details class="evidence"><summary>浓度、稀释与证据边界</summary><p class="fine">${esc(j.composition.note)}</p><p>已计量液体 ${j.composition.measured_liquid_ml} ml；额外水 ${j.composition.additional_water_ml??'未知'} ${j.composition.additional_water_ml!==null?'ml':''}。</p>${Object.entries(j.composition.estimates).map(([k,v])=>`<p>${esc({abv:'酒精浓度',sugar_g_l:'糖浓度',acid_g_l:'可滴定酸度（以柠檬酸计）'}[k])}：${v.value===null?'资料不足':v.value+' '+v.unit} · ${esc(v.stage)}</p>`).join('')}<p class="fine">${esc(j.self_review)}</p>${evidenceLinks(j.sources)}</details>
    ${j.design_review?`<details class="evidence"><summary>结构、替换与出杯检查 · ${esc(j.design_review.version)}</summary><p class="fine">${esc(j.design_review.mapping_policy)}</p><p>${j.design_review.roots.map(r=>esc(r.name)).join(' / ')}</p>${j.design_review.prompts.map(p=>`<article class="mechanism"><h4>${esc(p.message)}</h4><p>验证：${esc(p.verification)}</p></article>`).join('')}${evidenceLinks(j.design_review.sources)}</details>`:''}
    <button id="judge-improve" class="secondary">生成一个小改动，比较前后</button><div id="judge-improvement" aria-live="polite"></div>
    <details class="evidence"><summary>试饮后，给这杯酒反馈</summary><p class="fine">这份反馈绑定上面的配方与条件。实际用了不同用量，请先重新评价。</p>
    <label class="check-label"><input id="judge-tasted" type="checkbox"> 我已经实际调制并试饮</label>
    <div class="rating-inputs">${j.dimensions.map(d=>`<label>${esc(d.name)}<input class="sensory-rating" data-dimension="${d.id}" type="number" min="0" max="10" step="0.5" placeholder="待评" disabled></label>`).join('')}</div><p class="fine">0 = 严重不合目标，5 = 可接受但有明显问题，8 = 完成良好，10 = 该目标下的出色表现。未评项留空。</p>
    <div class="descriptor-grid">${Object.entries(descriptorNames).map(([id,name])=>`<label class="check-label"><input class="trial-descriptor" type="checkbox" value="${id}">${esc(name)}</label>`).join('')}</div>
    <label>入口 → 中段 → 余韵，以及下次想改什么<textarea id="judge-trial-notes" rows="3" placeholder="例如：第一口偏甜，2 分钟后仍甜，香气清楚；下次只改糖浆。"></textarea></label>
    <button id="judge-save-feedback" class="primary">保存反馈到项目</button><p id="judge-feedback-status" class="fine" role="status"></p></details></section>`;
}
function bindJudge(){
  if(!lastEvaluation?.judge)return;
  const j=lastEvaluation.judge;
  const holder=document.createElement('div');holder.innerHTML=judgeHTML(j);$('save-note').parentElement.before(holder);
  $('judge-improve').onclick=()=>showImprovement(j.snapshot);
  $('judge-tasted').onchange=()=>document.querySelectorAll('.sensory-rating').forEach(input=>{input.disabled=!$('judge-tasted').checked;if(input.disabled)input.value='';});
  const requestId=crypto.randomUUID();let saved=false;
  $('judge-save-feedback').onclick=async()=>{
    if(saved)return;
    const tasting={tasted:$('judge-tasted').checked,ratings:{},descriptors:[...document.querySelectorAll('.trial-descriptor:checked')].map(i=>i.value),notes:$('judge-trial-notes').value,taster:'local'};
    document.querySelectorAll('.sensory-rating').forEach(i=>{if(i.value!=='')tasting.ratings[i.dataset.dimension]=Number(i.value);});
    $('judge-save-feedback').disabled=true;
    try{
      const r=await api('/api/feedback',{...j.snapshot,tasting,request_id:requestId,parent_trial_id:trialParent});saved=true;
      $('judge-feedback-status').textContent=tasting.tasted?`已保存真实试饮 ${r.input.sensory.rated_dimensions}/7 项；总分 ${r.input.sensory.total??'待补齐七项'} /70。可用下面按钮生成下一版。`:'已保存为未试饮设计笔记，不参与口味学习。';
      if(tasting.tasted){const b=document.createElement('button');b.className='secondary';b.textContent='根据这次反馈改进';b.onclick=()=>showImprovement({feedback_id:r.id});$('judge-feedback-status').after(b);}
    }catch(e){$('judge-feedback-status').textContent=e.message;$('judge-save-feedback').disabled=false;}
  };
}
async function showImprovement(request){
  const output=$('judge-improvement');output.innerHTML='<p class="fine">正在复核候选配方…</p>';
  try{
    const r=await api('/api/improve',{...request,avoid:$('avoid').value});
    if(r.blocked){output.innerHTML=`<p>${esc(r.reason)}</p>`;return;}
    output.innerHTML=`<article class="trial-candidate"><h4>下一杯只改 ${esc(nameOf(r.change.variable))}</h4><p>${esc(r.change.reason)}</p><p><strong>${esc(r.change.before)} → ${esc(r.change.after)} ${esc(r.change.unit||'')}</strong></p><pre>${esc(recipeText(r.candidate.recipe))}</pre><p class="fine">框架分 ${r.before.score??'—'} → ${r.after.score??'—'}；不预测实饮加分。</p><p>${esc(r.verification)}</p><p class="fine">改后复核：${esc(r.after.judge.verdict)}</p><button id="use-trial-candidate" class="primary">载入候选配方，再评价</button></article>`;
    $('use-trial-candidate').onclick=()=>{setFrame(r.candidate.frame,false);$('recipe').value=recipeText(r.candidate.recipe);$('method').value=r.candidate.method||'';restoreJudgeContext(r.candidate.context);trialParent=r.feedback_id||null;storeDraft();evaluate();};
  }catch(e){output.innerHTML=`<p>${esc(e.message)}</p>`;}
}
async function renderTrialHistory(){
  const holder=$('trial-history');
  try{
    const r=await api('/api/history');const superseded=new Set(r.trials.map(t=>t.input.supersedes_trial_id));
    holder.innerHTML=`<h3>项目中的试饮与版本记录</h3><p class="fine">配方、七维分数、设计依据与父版本保存在本机项目。下面的旧版浏览器手记仍可保留。</p>${r.trials.length?r.trials.map(t=>{const p=t.input;return `<article class="panel note-card"><h4>${esc(data.frameworks.find(f=>f.id===p.snapshot.frame)?.zh||p.snapshot.frame)} · ${p.tasting.tasted?'已试饮':'设计笔记'}${superseded.has(t.id)?' · 已有更正，排除于偏好统计':''}</h4><p class="fine">${esc(new Date(t.created_at).toLocaleString())} · 实饮 ${p.sensory.total??'未评齐'} /70 · ${esc(p.knowledge_version)}</p><pre>${esc(recipeText(p.snapshot.recipe))}</pre><p>${esc(p.tasting.notes||'暂无文字反馈')}</p><p>${p.tasting.descriptors.map(d=>esc(descriptorNames[d])).join(' / ')}</p><p class="fine">${p.sensory.dimensions.map(d=>esc(d.name)+' '+(d.score??'—')).join(' · ')}</p><button class="text-button load-trial" data-id="${esc(t.id)}">载入此版本 ↗</button></article>`;}).join(''):'<p class="fine">还没有项目反馈。先评价一杯，再展开「试饮后，给这杯酒反馈」。</p>'}`;
    holder.querySelectorAll('.load-trial').forEach(b=>b.onclick=()=>{const t=r.trials.find(t=>t.id===b.dataset.id);const s=t.input.snapshot;setFrame(s.frame,false);$('recipe').value=recipeText(s.recipe);$('method').value=s.method||'';restoreJudgeContext(s.context);trialParent=t.id;view('studio');storeDraft();evaluate();});
  }catch(e){holder.textContent=e.message;}
}
async function loadIngredientScience(){
  try{
    const r=await api('/api/knowledge?name='+encodeURIComponent($('science-select').value));
    $('science-result').innerHTML=`<h3>${esc(r.profile.name)}</h3><p class="fine">${esc(r.profile.note)} 当前没有该产品的实测浓度。</p><div class="science-components">${r.components.map(c=>`<article class="ingredient-card"><h4>${esc(c.name)}</h4><p>${esc(c.mechanism)}</p><small>影响：${c.dimensions.map(id=>esc(judgeCatalog?.dimensions.find(d=>d[0]===id)?.[1]||id)).join('、')}</small></article>`).join('')}</div><details class="evidence"><summary>可能参与的相互作用（须满足所有条件）</summary>${r.potential_interactions.map(i=>`<p><strong>${esc(i.title)}</strong>：${esc(i.conditions)}</p>`).join('')}</details>${evidenceLinks(r.sources)}`;
  }catch(e){$('science-result').textContent=e.message;}
}
async function initJudge(){
  try{
    judgeCatalog=await api('/api/judge-catalog');
    $('science-status').innerHTML=`${judgeCatalog.counts.profiles} 种原料 · ${judgeCatalog.counts.components} 类成分 · ${judgeCatalog.counts.rules} 条相互作用 · ${judgeCatalog.counts.sources} 个来源 <br>知识版本 ${esc(judgeCatalog.version)}；${judgeCatalog.sources.filter(s=>s.needs_review).length} 个来源待复查。`;
    $('science-sources').innerHTML=judgeCatalog.sources.map(s=>`<article class="mechanism"><strong>${link(s.url,s.title)}</strong><p>${esc(s.scope)}</p><small>复核 ${esc(s.reviewed_at)} · 下次 ${esc(s.review_due)}</small></article>`).join('');
    const catalog=await api('/api/catalog');$('science-select').innerHTML=catalog.ingredients.map(i=>`<option value="${esc(i.id)}">${esc(i.zh)} / ${esc(i.en)}</option>`).join('');$('science-select').value='lemon_juice';$('science-select').onchange=loadIngredientScience;await loadIngredientScience();
    for(const id of ['judge-intent','judge-appearance','judge-theme','judge-water','judge-temperature'])$(id).addEventListener('input',storeDraft);
  }catch(e){$('science-status').textContent=e.message;}
}
initJudge();
