-- =====================================================================
-- 008: conferência com o saldo real do banco
--
-- De vez em quando o usuário informa quanto tem na conta (por pessoa ou tudo
-- junto). A previsão do fim do mês passa a partir desse valor real, o que já
-- inclui os gastos pequenos que não foram anotados.
-- Somente ADICIONA tabelas: nada existente é alterado.
-- =====================================================================

create table if not exists conferencias (
    id          bigint generated always as identity primary key,
    data        date not null default current_date,
    junto       boolean not null default false,  -- true = um saldo só para a casa
    total       numeric(12, 2) not null,         -- soma dos saldos (pode ser negativo)
    -- Receitas que já tinham caído antes da data prevista ("origem:id", ex.: receita:3)
    ja_entrou   text[] not null default '{}',
    created_at  timestamptz not null default now()
);

create index if not exists ix_conferencias_data on conferencias (data);

-- Saldo de cada pessoa numa conferência "separado por pessoa"
create table if not exists conferencia_saldos (
    id              bigint generated always as identity primary key,
    conferencia_id  bigint not null references conferencias (id) on delete cascade,
    responsavel_id  bigint not null references responsaveis (id) on delete cascade,
    valor           numeric(12, 2) not null,
    unique (conferencia_id, responsavel_id)
);

alter table conferencias        enable row level security;
alter table conferencia_saldos  enable row level security;
revoke all on conferencias, conferencia_saldos from anon, authenticated;
