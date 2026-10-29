-- =====================================================================
-- 004: metas de economia e o dinheiro guardado em cada uma
-- =====================================================================

-- Regra de quanto guardar por mês:
--   pct_sobra   = % do que sobra (receitas - despesas do mês)
--   pct_receita = % de tudo o que entra no mês
--   valor_fixo  = um valor fixo por mês
create table if not exists metas (
    id            bigint generated always as identity primary key,
    nome          text not null check (length(trim(nome)) > 0),
    valor_alvo    numeric(12, 2) check (valor_alvo is null or valor_alvo > 0),
    data_alvo     date,
    regra         text not null default 'pct_sobra'
                  check (regra in ('pct_sobra', 'pct_receita', 'valor_fixo')),
    regra_valor   numeric(12, 2) not null check (regra_valor > 0),
    ativa         boolean not null default true,
    created_at    timestamptz not null default now(),
    check (regra = 'valor_fixo' or regra_valor <= 100)
);

-- Cada vez que guarda (valor positivo) ou retira (valor negativo) de uma meta
create table if not exists meta_movimentos (
    id          bigint generated always as identity primary key,
    meta_id     bigint not null references metas (id) on delete cascade,
    data        date not null default current_date,
    valor       numeric(12, 2) not null check (valor <> 0),
    descricao   text,
    created_at  timestamptz not null default now()
);

create index if not exists ix_meta_movimentos_meta on meta_movimentos (meta_id, data);

alter table metas            enable row level security;
alter table meta_movimentos  enable row level security;
revoke all on metas, meta_movimentos from anon, authenticated;
