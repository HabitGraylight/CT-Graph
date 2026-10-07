// PostgreSQL executes the real migration and RLS policies. Auth itself is stubbed.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const { PGlite } = await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
const db = new PGlite();
let count=0;
const ok=(value,message)=>{assert.ok(value,message);count++;};
const A='10000000-0000-4000-8000-000000000001';
const B='10000000-0000-4000-8000-000000000002';
const C='10000000-0000-4000-8000-000000000003';
const D='10000000-0000-4000-8000-000000000004';
const R='20000000-0000-4000-8000-000000000001';
await db.exec(`create role anon; create role authenticated; create schema auth;
  create table auth.users(id uuid primary key);
  create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
  grant usage on schema auth to anon,authenticated;
  grant execute on function auth.uid() to anon,authenticated;
  insert into auth.users values ('${A}'),('${B}'),('${C}'),('${D}');`);
await db.exec(await readFile(new URL('../../cloud/schema.sql',import.meta.url),'utf8'));
const asUser=(uid,sql,params=[])=>db.transaction(async tx=>{
  await tx.exec(`set local role ${uid?'authenticated':'anon'}`);
  await tx.query("select set_config('request.jwt.claim.sub',$1,true)",[uid||'']);
  return (await tx.query(sql,params)).rows;
});
async function denied(uid,sql,params=[]) {
  await assert.rejects(()=>asUser(uid,sql,params));count++;
}
await asUser(A,'insert into public.profiles(user_id,display_name) values ($1,$2)',[A,'Synthetic author']);
await asUser(A,"update public.profiles set preferences='{\"sweet\":0}' where user_id=$1",[A]);
ok((await asUser(A,'select preferences from public.profiles'))[0].preferences.sweet===0,'Zero is valid');
ok((await asUser(B,'select * from public.profiles')).length===0,'Other profile is private');
await denied(B,'insert into public.profiles(user_id,display_name) values ($1,$2)',[A,'Forged']);
await denied(A,"update public.profiles set preferences='{\"sweet\":11}'");
await denied(A,"update public.profiles set preferences='{\"sweet\":\"9\"}'");
await denied(A,"update public.profiles set preferences='{\"secret\":5}'");
await asUser(A,"insert into public.recipes(id,title,frame,recipe) values ($1,'Synthetic recipe','sour','gin 45 ml, lemon juice 25 ml, simple syrup 20 ml')",[R]);
ok((await asUser(B,'select * from public.recipes')).length===0,'Private recipe hidden across accounts');
await denied(null,'select * from public.recipes');
ok((await asUser(null,'select * from public.community_cards()')).length===0,'Private recipe never in community RPC');
await denied(B,"insert into public.recipes(owner_id,title,frame,recipe) values ($1,'Forged','sour','gin')",[A]);
await denied(B,'insert into public.tastings(recipe_id,tasted,as_recipe,liking) values ($1,true,true,9)',[R]);
await denied(A,"update public.recipes set recipe='changed' where id=$1",[R]);
await asUser(A,"update public.recipes set visibility='public' where id=$1",[R]);
ok((await asUser(B,'select * from public.recipes')).length===1,'Published recipe is readable');
ok((await asUser(B,"update public.recipes set visibility='private' returning id")).length===0,'Other user cannot withdraw');
await asUser(A,'insert into public.tastings(recipe_id,tasted,as_recipe,liking,public_vote) values ($1,true,true,10,true)',[R]);
ok(Number((await asUser(null,'select * from public.community_cards()'))[0].voters)===0,'Author vote excluded');
for(const [uid,liking,aroma] of [[B,9,true],[C,8,true],[D,7,false]]) {
  await asUser(uid,'insert into public.tastings(recipe_id,tasted,as_recipe,liking,intensities,notes,public_vote) values ($1,true,true,$2,$3,$4,true)',
    [R,liking,JSON.stringify(aroma?{sweet:5,aroma:7}:{sweet:4}),'SYNTHETIC PRIVATE NOTE']);
  const row=(await asUser(null,'select * from public.community_cards()'))[0];
  if(uid!==D)ok(row.average_liking===null,'Small sample average withheld');
}
const card=(await asUser(null,'select * from public.community_cards()'))[0];
ok(Number(card.voters)===3 && Number(card.average_liking)===8,'Three distinct users, exact average');
ok(Number(card.ranking_score)===6.75 && card.qualified,'Shrinkage and qualification');
ok(card.intensities.aroma===null && card.intensities.sweet!==null,'Per-dimension minimum sample enforced');
ok(!JSON.stringify(card).includes('PRIVATE NOTE') && !('owner_id' in card),'RPC contains no notes or account IDs');
ok((await asUser(B,'select * from public.tastings')).length===1,'Raw tastings restricted to self');
await denied(null,'select * from public.tastings');
await denied(B,'insert into public.tastings(user_id,recipe_id,tasted,as_recipe,liking) values ($1,$2,true,true,7)',[C,R]);
await denied(B,'update public.tastings set tasted=false');
await denied(B,'update public.tastings set as_recipe=false');
await denied(B,'update public.tastings set liking=11');
await denied(B,"update public.tastings set intensities='{\"sweet\":null}'");
await denied(B,'update public.tastings set user_id=$1',[C]);
await asUser(B,'insert into public.tastings(recipe_id,tasted,as_recipe,liking,public_vote) values ($1,true,true,10,true) on conflict(user_id,recipe_id) do update set liking=excluded.liking',[R]);
const updated=(await asUser(null,'select * from public.community_cards()'))[0];
ok(Number(updated.voters)===3 && Number(updated.average_liking)===8.33,'Repeat tasting updates one vote');
await asUser(D,'update public.tastings set public_vote=false');
ok((await asUser(null,'select * from public.community_cards()'))[0].average_liking===null,'Withdrawal removes aggregate contribution');
await asUser(A,"update public.recipes set visibility='private' where id=$1",[R]);
ok((await asUser(null,'select * from public.community_cards()')).length===0,'Recipe withdrawal removes public result');
ok((await asUser(B,'select * from public.recipes')).length===0,'Withdrawal removes public detail');
ok((await asUser(B,'delete from public.tastings returning id')).length===1,'Can delete own tasting after withdrawal');
await db.close();
console.log(`PASS: ${count} database assertions; synthetic users only; actual PostgreSQL RLS and triggers.`);
