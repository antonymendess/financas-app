-- =====================================================================
-- 006: pessoas da casa (responsáveis) para separar de quem é cada dinheiro
--
-- Somente ADICIONA estrutura: nenhuma linha existente é alterada.
-- responsavel_id nulo = "Conjunto" (dinheiro/conta do casal).
-- Despesa ou gasto no cartão sem responsável herda o responsável do cartão.
-- =====================================================================

create table if not exists responsaveis (
    id          bigint generated always as identity primary key,
    nome        text not null unique check (length(trim(nome)) > 0),
    created_at  timestamptz not null default now()
);

alter table receitas       add column if not exists responsavel_id bigint
    references responsaveis (id) on delete set null;
alter table despesas       add column if not exists responsavel_id bigint
    references responsaveis (id) on delete set null;
alter table cartoes        add column if not exists responsavel_id bigint
    references responsaveis (id) on delete set null;
alter table gastos_cartao  add column if not exists responsavel_id bigint
    references responsaveis (id) on delete set null;
alter table comissoes      add column if not exists responsavel_id bigint
    references responsaveis (id) on delete set null;

alter table responsaveis enable row level security;
revoke all on responsaveis from anon, authenticated;
