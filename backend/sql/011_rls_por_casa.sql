-- =====================================================================
-- 011: segunda trava de isolamento (Row Level Security por casa)
--
-- Cria o papel `app_api`, que a API passa a usar no dia a dia. Para ele, o próprio
-- banco só devolve e só aceita linhas da casa informada em `app.casa_id` (a API
-- define isso no início de cada transação). Mesmo que o código esqueça um filtro,
-- o banco não mostra dados de outra casa.
--
-- O dono das tabelas (postgres) NÃO é afetado: migrações, backups e as operações de
-- sistema (login, convites) continuam com ele. Nada aqui altera dados.
--
-- Depois de rodar, defina a senha do papel no SQL Editor do Supabase (fora do git):
--     alter role app_api with login password 'UMA_SENHA_FORTE';
-- e configure DATABASE_URL (usuário app_api) e DATABASE_URL_SISTEMA (usuário postgres).
-- =====================================================================

do $$
begin
    if not exists (select from pg_roles where rolname = 'app_api') then
        create role app_api nologin;
    end if;
end $$;

grant usage on schema public to app_api;
grant usage, select on all sequences in schema public to app_api;
alter default privileges in schema public grant usage, select on sequences to app_api;

do $$
declare
    tabela text;
begin
    foreach tabela in array array[
        'cartoes', 'categorias', 'formas_pagamento', 'despesas', 'receitas', 'comissoes',
        'comissao_parcelas', 'gastos_cartao', 'anotacoes', 'despesa_pagamentos',
        'fatura_pagamentos', 'negociacoes', 'metas', 'meta_movimentos', 'meta_meses_fechados',
        'responsaveis', 'conferencias', 'conferencia_saldos'
    ] loop
        execute format('grant select, insert, update, delete on %I to app_api', tabela);
        execute format('drop policy if exists casa_isolada on %I', tabela);
        execute format(
            'create policy casa_isolada on %I for all to app_api '
            'using (casa_id = nullif(current_setting(''app.casa_id'', true), '''')::bigint) '
            'with check (casa_id = nullif(current_setting(''app.casa_id'', true), '''')::bigint)',
            tabela
        );
    end loop;
end $$;

-- A própria casa: ver e renomear
grant select, update on casas to app_api;
drop policy if exists casa_propria on casas;
create policy casa_propria on casas for all to app_api
    using (id = nullif(current_setting('app.casa_id', true), '')::bigint)
    with check (id = nullif(current_setting('app.casa_id', true), '')::bigint);

-- Membros da própria casa
grant select, delete on membros to app_api;
drop policy if exists membros_da_casa on membros;
create policy membros_da_casa on membros for all to app_api
    using (casa_id = nullif(current_setting('app.casa_id', true), '')::bigint);

-- Convites da própria casa e os criados pelo próprio usuário (administrador)
grant select, insert, delete on convites to app_api;
drop policy if exists convites_da_casa on convites;
create policy convites_da_casa on convites for all to app_api
    using (
        casa_id = nullif(current_setting('app.casa_id', true), '')::bigint
        or criado_por::text = current_setting('app.usuario_id', true)
    )
    with check (
        casa_id = nullif(current_setting('app.casa_id', true), '')::bigint
        or criado_por::text = current_setting('app.usuario_id', true)
    );
