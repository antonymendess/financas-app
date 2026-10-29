-- =====================================================================
-- 005: mês fechado em uma meta: o valor guardado abaixo da regra encerra o mês
-- e a diferença deixa de ficar pendente
-- =====================================================================

create table if not exists meta_meses_fechados (
    id           bigint generated always as identity primary key,
    meta_id      bigint not null references metas (id) on delete cascade,
    competencia  date not null check (extract(day from competencia) = 1),
    created_at   timestamptz not null default now(),
    unique (meta_id, competencia)
);

alter table meta_meses_fechados enable row level security;
revoke all on meta_meses_fechados from anon, authenticated;
