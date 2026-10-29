-- =====================================================================
-- COLE TUDO NO SQL EDITOR DO SUPABASE E CLIQUE EM "RUN"
--
-- Aplica as migrações 009, 010 e 011 de uma vez (casas, convites e RLS).
-- Roda numa transação só: se der qualquer erro, NADA é alterado.
-- Gerado a partir de sql/009, 010 e 011 (não edite aqui, edite os originais).
-- =====================================================================

begin;

-- Conferência: o banco precisa estar na versão 008 (você já usa conferência e metas cofrinho)
do $$
begin
    if to_regclass('public.conferencias') is null then
        raise exception 'Falta a migração 008 (conferencias). Rode 006, 007 e 008 antes.';
    end if;
    if to_regclass('public.responsaveis') is null then
        raise exception 'Falta a migração 006 (responsaveis).';
    end if;
    if exists (select 1 from information_schema.columns where table_schema = 'public'
               and table_name = 'metas' and column_name = 'regra_valor' and is_nullable = 'NO') then
        raise exception 'Falta a migração 007 (metas cofrinho).';
    end if;
end $$;

-- =====================================================================
-- 009: casas (clientes), membros e convites + casa_id em todas as tabelas
--
-- Cada cliente é uma "casa" com até 2 logins. Os dados que já existem são
-- colocados numa casa criada aqui (legado = true); o dono atual é ligado a ela
-- no primeiro login (e-mail do ALLOWED_EMAIL). Somente ADICIONA estrutura e
-- preenche casa_id: nenhum dado é apagado.
-- =====================================================================

create table if not exists casas (
    id                 bigint generated always as identity primary key,
    nome               text not null check (length(trim(nome)) > 0),
    legado             boolean not null default false,  -- casa dos dados de antes da 009
    assinatura_status  text not null default 'teste'
                       check (assinatura_status in ('teste', 'ativa', 'atrasada', 'cancelada')),
    assinatura_ate     date,
    criada_em          timestamptz not null default now()
);

-- Login (usuário do Supabase Auth) ligado a uma casa. Cada login pertence a uma casa só.
create table if not exists membros (
    id          bigint generated always as identity primary key,
    casa_id     bigint not null references casas (id) on delete cascade,
    usuario_id  uuid not null unique,
    email       text not null,
    papel       text not null default 'membro' check (papel in ('dono', 'membro')),
    criado_em   timestamptz not null default now()
);

create index if not exists ix_membros_casa on membros (casa_id);

-- Convite por link: 'nova_casa' (cliente novo, criado pelo administrador) ou
-- 'membro' (dono chama mais uma pessoa para a casa dele)
create table if not exists convites (
    id          bigint generated always as identity primary key,
    token       text not null unique,
    tipo        text not null check (tipo in ('nova_casa', 'membro')),
    casa_id     bigint references casas (id) on delete cascade,
    email       text not null,
    nome_casa   text,
    criado_por  uuid not null,
    criado_em   timestamptz not null default now(),
    expira_em   timestamptz not null,
    aceito_em   timestamptz,
    aceito_por  uuid,
    check ((tipo = 'membro') = (casa_id is not null))
);

-- Casa que recebe os dados existentes (só se ainda não houver nenhuma casa)
insert into casas (nome, legado)
select 'Minha casa', true
where not exists (select 1 from casas);

do $$
declare
    tabela text;
    casa   bigint;
begin
    select id into casa from casas where legado order by id limit 1;
    foreach tabela in array array[
        'cartoes', 'categorias', 'formas_pagamento', 'despesas', 'receitas', 'comissoes',
        'comissao_parcelas', 'gastos_cartao', 'anotacoes', 'despesa_pagamentos',
        'fatura_pagamentos', 'negociacoes', 'metas', 'meta_movimentos', 'meta_meses_fechados',
        'responsaveis', 'conferencias', 'conferencia_saldos'
    ] loop
        execute format(
            'alter table %I add column if not exists casa_id bigint references casas (id) on delete cascade',
            tabela
        );
        if casa is not null then
            execute format('update %I set casa_id = %s where casa_id is null', tabela, casa);
        end if;
        execute format('create index if not exists %I on %I (casa_id)', 'ix_' || tabela || '_casa', tabela);
    end loop;
end $$;

alter table casas     enable row level security;
alter table membros   enable row level security;
alter table convites  enable row level security;
revoke all on casas, membros, convites from anon, authenticated;

-- =====================================================================
-- 010: casa_id obrigatório e nomes únicos por casa
--
-- Roda depois da 009 (que preencheu casa_id em tudo). Nomes de cartão, categoria,
-- forma de pagamento e pessoa passam a ser únicos dentro de cada casa (duas casas
-- podem ter a categoria "Casa", por exemplo). Nenhum dado é alterado.
-- =====================================================================

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
        execute format('alter table %I alter column casa_id set not null', tabela);
    end loop;

    foreach tabela in array array['cartoes', 'categorias', 'formas_pagamento', 'responsaveis'] loop
        execute format('alter table %I drop constraint if exists %I', tabela, tabela || '_nome_key');
        if not exists (select 1 from pg_constraint where conname = tabela || '_casa_nome_key') then
            execute format('alter table %I add constraint %I unique (casa_id, nome)',
                           tabela, tabela || '_casa_nome_key');
        end if;
    end loop;
end $$;

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

-- Registro das migrações aplicadas (usado pelo scripts/migrar.py no futuro)
create table if not exists migracoes_aplicadas (
    nome         text primary key,
    aplicada_em  timestamptz not null default now(),
    executada    boolean not null default true
);
alter table migracoes_aplicadas enable row level security;
revoke all on migracoes_aplicadas from anon, authenticated;
insert into migracoes_aplicadas (nome, executada) values
    ('001_schema.sql', false), ('002_pagamentos_negociacoes.sql', false),
    ('003_receita_de_comissao.sql', false), ('004_metas.sql', false),
    ('005_metas_meses_fechados.sql', false), ('006_responsaveis.sql', false),
    ('007_metas_cofrinho.sql', false), ('008_conferencias_saldo.sql', false),
    ('009_casas.sql', true), ('010_casa_obrigatoria.sql', true), ('011_rls_por_casa.sql', true)
on conflict (nome) do nothing;

commit;

-- Resultado esperado: uma linha "Minha casa" com legado = true
select id, nome, legado from casas;
