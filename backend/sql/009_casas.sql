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
