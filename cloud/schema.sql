-- Run once in a new Supabase project's SQL editor. No personal seed data.
begin;

create function public.valid_score_map(value jsonb, allowed text[])
returns boolean language plpgsql immutable set search_path = '' as $$
declare item record;
begin
  if jsonb_typeof(value) is distinct from 'object' then return false; end if;
  for item in select * from jsonb_each(value) loop
    if not (item.key = any(allowed)) or jsonb_typeof(item.value) <> 'number' then return false; end if;
    if (item.value::text)::numeric < 0 or (item.value::text)::numeric > 10 then return false; end if;
  end loop;
  return true;
end $$;

create table public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade default auth.uid(),
  display_name text not null check (length(btrim(display_name)) between 1 and 40),
  preferences jsonb not null default '{}' check (public.valid_score_map(preferences, array['sweet','sour','bitter','strength','body','aroma'])),
  updated_at timestamptz not null default now()
);

create table public.recipes (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  title text not null check (length(btrim(title)) between 1 and 80),
  frame text not null check (frame in ('sour','daisy','old_fashioned','martini','manhattan','negroni','highball','collins','mule','spritz','tropical','julep')),
  method text not null default '' check (length(method)<=40),
  recipe text not null check (length(btrim(recipe)) between 1 and 6000),
  context jsonb not null default '{}' check (jsonb_typeof(context)='object' and octet_length(context::text)<=20000),
  visibility text not null default 'private' check (visibility in ('private','public')),
  created_at timestamptz not null default now()
);
create index recipes_owner on public.recipes(owner_id, created_at desc);
create index recipes_visibility on public.recipes(visibility, created_at desc);

create table public.tastings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  recipe_id uuid not null references public.recipes(id) on delete cascade,
  tasted boolean not null check (tasted is true),
  as_recipe boolean not null check (as_recipe is true),
  liking numeric not null check (liking between 0 and 10),
  quality jsonb not null default '{}' check (public.valid_score_map(quality, array['appearance','aroma','balance','structure','texture','execution','expression'])),
  intensities jsonb not null default '{}' check (public.valid_score_map(intensities, array['sweet','sour','bitter','strength','body','aroma'])),
  notes text not null default '' check (length(notes)<=2000),
  public_vote boolean not null default false,
  updated_at timestamptz not null default now(),
  unique(user_id, recipe_id)
);
create index tastings_user on public.tastings(user_id, updated_at desc);
create index tastings_recipe on public.tastings(recipe_id);

create function public.touch_owned_record() returns trigger
language plpgsql set search_path = '' as $$
begin
  if new.user_id is distinct from old.user_id then raise exception 'Owner cannot change'; end if;
  if tg_table_name='tastings' then
    if new.recipe_id is distinct from old.recipe_id then raise exception 'Version cannot change'; end if;
  end if;
  new.updated_at=now();
  return new;
end $$;
create trigger profiles_touch before update on public.profiles for each row execute function public.touch_owned_record();
create trigger tastings_touch before update on public.tastings for each row execute function public.touch_owned_record();

create function public.immutable_recipe() returns trigger
language plpgsql set search_path = '' as $$
begin
  if (to_jsonb(new)-'visibility') is distinct from (to_jsonb(old)-'visibility') then
    raise exception 'Recipe versions are immutable; create a new version';
  end if;
  return new;
end $$;
create trigger recipe_version_lock before update on public.recipes for each row execute function public.immutable_recipe();

alter table public.profiles enable row level security;
alter table public.recipes enable row level security;
alter table public.tastings enable row level security;

create policy profiles_read on public.profiles for select to authenticated using (user_id=(select auth.uid()));
create policy profiles_insert on public.profiles for insert to authenticated with check (user_id=(select auth.uid()));
create policy profiles_update on public.profiles for update to authenticated using (user_id=(select auth.uid())) with check (user_id=(select auth.uid()));
create policy profiles_delete on public.profiles for delete to authenticated using (user_id=(select auth.uid()));

-- Direct recipe reads stay private. Public, owner-free projections are returned by the RPC below.
create policy recipes_read on public.recipes for select to authenticated using (owner_id=(select auth.uid()) or visibility='public');
create policy recipes_insert on public.recipes for insert to authenticated with check (owner_id=(select auth.uid()) and visibility='private');
create policy recipes_update on public.recipes for update to authenticated using (owner_id=(select auth.uid())) with check (owner_id=(select auth.uid()));
create policy recipes_delete on public.recipes for delete to authenticated using (owner_id=(select auth.uid()));

create policy tastings_read on public.tastings for select to authenticated using (user_id=(select auth.uid()));
create policy tastings_insert on public.tastings for insert to authenticated with check (
  user_id=(select auth.uid()) and exists (select 1 from public.recipes r where r.id=recipe_id and (r.owner_id=(select auth.uid()) or r.visibility='public'))
);
create policy tastings_update on public.tastings for update to authenticated using (user_id=(select auth.uid())) with check (
  user_id=(select auth.uid()) and exists (select 1 from public.recipes r where r.id=recipe_id and (r.owner_id=(select auth.uid()) or r.visibility='public'))
);
create policy tastings_delete on public.tastings for delete to authenticated using (user_id=(select auth.uid()));

revoke all on public.profiles, public.recipes, public.tastings from anon, authenticated;
grant select, insert, update, delete on public.profiles, public.recipes, public.tastings to authenticated;

-- Only opt-in votes on public versions, no author self-votes, one row per voter/version.
-- Fewer than 3 voters: no individual score or intensity is disclosed.
create function public.community_cards()
returns table (
  id uuid, title text, frame text, method text, recipe text, context jsonb,
  author text, created_at timestamptz, voters bigint, average_liking numeric,
  ranking_score numeric, qualified boolean, intensities jsonb
) language sql stable security definer set search_path = '' as $$
  select r.id,r.title,r.frame,r.method,r.recipe,r.context,
    coalesce(p.display_name,'调酒同好'),r.created_at,count(t.id),
    case when count(t.id)>=3 then round(avg(t.liking),2) end,
    case when count(t.id)>=3 then round((sum(t.liking)+5*6)/(count(t.id)+5),2) end,
    count(t.id)>=3 and coalesce(avg(t.liking),0)>=7,
    case when count(t.id)>=3 then jsonb_build_object(
      'sweet',case when count(t.intensities->>'sweet')>=3 then round(avg((t.intensities->>'sweet')::numeric),2) end,
      'sour',case when count(t.intensities->>'sour')>=3 then round(avg((t.intensities->>'sour')::numeric),2) end,
      'bitter',case when count(t.intensities->>'bitter')>=3 then round(avg((t.intensities->>'bitter')::numeric),2) end,
      'strength',case when count(t.intensities->>'strength')>=3 then round(avg((t.intensities->>'strength')::numeric),2) end,
      'body',case when count(t.intensities->>'body')>=3 then round(avg((t.intensities->>'body')::numeric),2) end,
      'aroma',case when count(t.intensities->>'aroma')>=3 then round(avg((t.intensities->>'aroma')::numeric),2) end
    ) else '{}'::jsonb end
  from public.recipes r
  left join public.profiles p on p.user_id=r.owner_id
  left join public.tastings t on t.recipe_id=r.id and t.public_vote and t.user_id<>r.owner_id
  where r.visibility='public'
  group by r.id,p.display_name
  order by (count(t.id)>=3 and coalesce(avg(t.liking),0)>=7) desc,
    case when count(t.id)>=3 then (sum(t.liking)+30)/(count(t.id)+5) end desc nulls last,
    r.created_at desc
  limit 100;
$$;
revoke all on function public.community_cards() from public;
grant execute on function public.community_cards() to anon, authenticated;
revoke all on function public.touch_owned_record(), public.immutable_recipe() from public;
revoke all on function public.valid_score_map(jsonb,text[]) from public;
grant execute on function public.valid_score_map(jsonb,text[]) to authenticated;
commit;
