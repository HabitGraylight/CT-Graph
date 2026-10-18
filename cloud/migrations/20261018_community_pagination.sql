-- Upgrade the previous schema without changing tables or user data. Safe to rerun.
begin;
drop function if exists public.community_cards();
create or replace function public.community_cards(
  p_frame text default null, p_qualified boolean default false,
  p_offset integer default 0, p_limit integer default 100
)
returns table (
  id uuid, title text, frame text, method text, recipe text, context jsonb,
  author text, created_at timestamptz, voters bigint, average_liking numeric,
  ranking_score numeric, qualified boolean, intensities jsonb
) language plpgsql stable security definer set search_path = '' as $$
begin
  if p_offset is null or p_offset<0 or p_offset>2000000
     or p_limit is null or p_limit<1 or p_limit>100 or p_qualified is null then
    raise exception 'Invalid pagination';
  end if;
  return query
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
  where r.visibility='public' and (p_frame is null or r.frame=p_frame)
  group by r.id,p.display_name
  having not p_qualified or (count(t.id)>=3 and coalesce(avg(t.liking),0)>=7)
  order by (count(t.id)>=3 and coalesce(avg(t.liking),0)>=7) desc,
    case when count(t.id)>=3 then (sum(t.liking)+30)/(count(t.id)+5) end desc nulls last,
    r.created_at desc, r.id desc
  limit p_limit offset p_offset;
end;
$$;
revoke all on function public.community_cards(text,boolean,integer,integer) from public;
grant execute on function public.community_cards(text,boolean,integer,integer) to anon, authenticated;
notify pgrst, 'reload schema';
commit;
