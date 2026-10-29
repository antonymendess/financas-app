-- =====================================================================
-- 012: quem paga a conta muda a partir de um mês
--
-- Ex.: o aluguel de outubro foi pago por uma pessoa e, de novembro em diante
-- (ou só em novembro), por outra. Cada linha diz quem paga a partir daquele mês,
-- até a próxima troca; antes da primeira troca vale o responsável da própria
-- despesa. Assim os meses que já passaram não mudam.
-- Somente ADICIONA uma tabela: nada existente é alterado.
-- =====================================================================

create table if not exists despesa_responsaveis (
    id              bigint generated always as identity primary key,
    casa_id         bigint not null references casas (id) on delete cascade,
    despesa_id      bigint not null references despesas (id) on delete cascade,
    a_partir_de     date not null,  -- 1º dia do mês
    -- null = Conjunto (pessoa excluída também volta para o Conjunto)
    responsavel_id  bigint references responsaveis (id) on delete set null,
    unique (despesa_id, a_partir_de)
);

create index if not exists ix_despesa_responsaveis_casa on despesa_responsaveis (casa_id);

alter table despesa_responsaveis enable row level security;
revoke all on despesa_responsaveis from anon, authenticated;

-- Mesmo isolamento por casa das outras tabelas (sql/011)
do $$
begin
    if exists (select from pg_roles where rolname = 'app_api') then
        grant select, insert, update, delete on despesa_responsaveis to app_api;
        drop policy if exists casa_isolada on despesa_responsaveis;
        create policy casa_isolada on despesa_responsaveis for all to app_api
            using (casa_id = nullif(current_setting('app.casa_id', true), '')::bigint)
            with check (casa_id = nullif(current_setting('app.casa_id', true), '')::bigint);
    end if;
end $$;
