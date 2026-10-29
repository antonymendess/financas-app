-- =====================================================================
-- 001: schema inicial do controle financeiro (idempotente)
-- =====================================================================

-- ---------------------------------------------------------------------
-- Cartões de crédito (dias nulos = preencher depois pela tela)
-- ---------------------------------------------------------------------
create table if not exists cartoes (
    id              bigint generated always as identity primary key,
    nome            text not null unique check (length(trim(nome)) > 0),
    dia_fechamento  smallint check (dia_fechamento between 1 and 31),
    dia_vencimento  smallint check (dia_vencimento between 1 and 31),
    created_at      timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Categorias de gasto
-- ---------------------------------------------------------------------
create table if not exists categorias (
    id          bigint generated always as identity primary key,
    nome        text not null unique check (length(trim(nome)) > 0),
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Formas de pagamento (as ligadas a um cartão têm cartao_id preenchido)
-- ---------------------------------------------------------------------
create table if not exists formas_pagamento (
    id          bigint generated always as identity primary key,
    nome        text not null unique check (length(trim(nome)) > 0),
    cartao_id   bigint references cartoes (id) on delete restrict,
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Despesas: UMA linha por compromisso (as parcelas são calculadas no backend)
--   num_parcelas nulo = conta fixa sem fim
-- ---------------------------------------------------------------------
create table if not exists despesas (
    id                  bigint generated always as identity primary key,
    descricao           text not null check (length(trim(descricao)) > 0),
    categoria_id        bigint not null references categorias (id) on delete restrict,
    forma_pagamento_id  bigint not null references formas_pagamento (id) on delete restrict,
    valor_mensal        numeric(12, 2) not null check (valor_mensal > 0),
    num_parcelas        integer check (num_parcelas is null or num_parcelas > 0),
    primeira_cobranca   date not null,
    cancelada_em        date,
    dia_vencimento      smallint check (dia_vencimento between 1 and 31),
    observacao          text,
    created_at          timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Receitas (recorrente entra todo mês; não recorrente só no mês de data_inicio)
-- ---------------------------------------------------------------------
create table if not exists receitas (
    id               bigint generated always as identity primary key,
    descricao        text not null check (length(trim(descricao)) > 0),
    tipo             text not null default 'Salário'
                     check (tipo in ('Salário', 'Extra', 'Outros')),
    valor            numeric(12, 2) not null check (valor > 0),
    recorrente       boolean not null default true,
    dia_recebimento  smallint check (dia_recebimento between 1 and 31),
    data_inicio      date not null default current_date,
    data_fim         date,
    created_at       timestamptz not null default now(),
    check (data_fim is null or data_fim >= data_inicio)
);

-- ---------------------------------------------------------------------
-- Comissões de vendas (mensalidade é apenas informativa)
-- ---------------------------------------------------------------------
create table if not exists comissoes (
    id                     bigint generated always as identity primary key,
    cliente                text not null check (length(trim(cliente)) > 0),
    telefone               text,
    mes_fechamento         date not null default date_trunc('month', current_date)::date,
    valor_implantacao      numeric(12, 2) not null check (valor_implantacao > 0),
    mensalidade            numeric(12, 2) check (mensalidade is null or mensalidade >= 0),
    percentual             numeric(5, 2) not null default 25
                           check (percentual > 0 and percentual <= 100),
    valor_comissao         numeric(12, 2) generated always as
                           (round(valor_implantacao * percentual / 100, 2)) stored,
    num_parcelas           integer not null default 1 check (num_parcelas > 0),
    data_primeira_parcela  date not null,
    observacao             text,
    created_at             timestamptz not null default now()
);

create table if not exists comissao_parcelas (
    id             bigint generated always as identity primary key,
    comissao_id    bigint not null references comissoes (id) on delete cascade,
    numero         integer not null check (numero > 0),
    data_prevista  date not null,
    valor          numeric(12, 2) not null check (valor > 0),
    paga           boolean not null default false,
    paga_em        date,
    created_at     timestamptz not null default now(),
    unique (comissao_id, numero)
);

create index if not exists ix_comissao_parcelas_data on comissao_parcelas (data_prevista);

-- ---------------------------------------------------------------------
-- Gastos avulsos no cartão
-- ---------------------------------------------------------------------
create table if not exists gastos_cartao (
    id            bigint generated always as identity primary key,
    data_compra   date not null default current_date,
    descricao     text not null check (length(trim(descricao)) > 0),
    categoria_id  bigint references categorias (id) on delete set null,
    cartao_id     bigint not null references cartoes (id) on delete restrict,
    valor_total   numeric(12, 2) not null check (valor_total > 0),
    num_parcelas  integer not null default 1 check (num_parcelas > 0),
    created_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Anotações: lembretes e dívidas informais
-- ---------------------------------------------------------------------
create table if not exists anotacoes (
    id              bigint generated always as identity primary key,
    texto           text not null check (length(trim(texto)) > 0),
    data            date,
    valor           numeric(12, 2) check (valor is null or valor > 0),
    pessoa          text,
    tipo            text not null default 'Lembrete'
                    check (tipo in ('A pagar', 'A receber', 'Lembrete')),
    concluida       boolean not null default false,
    entra_no_saldo  boolean not null default false,
    created_at      timestamptz not null default now()
);

-- =====================================================================
-- Segurança: Row Level Security em TODAS as tabelas, SEM policies.
-- Assim a chave pública (anon) do front não lê nem grava nada direto.
-- O backend conecta com o usuário dono das tabelas, que não é afetado.
-- =====================================================================
alter table cartoes            enable row level security;
alter table categorias         enable row level security;
alter table formas_pagamento   enable row level security;
alter table despesas           enable row level security;
alter table receitas           enable row level security;
alter table comissoes          enable row level security;
alter table comissao_parcelas  enable row level security;
alter table gastos_cartao      enable row level security;
alter table anotacoes          enable row level security;

-- Defesa extra: remove qualquer permissão dos papéis usados pela API pública
revoke all on cartoes, categorias, formas_pagamento, despesas, receitas,
              comissoes, comissao_parcelas, gastos_cartao, anotacoes
    from anon, authenticated;

-- =====================================================================
-- Dados iniciais
-- =====================================================================
-- A partir da 009 os dados iniciais são criados por casa (no cadastro da casa).
-- Este bloco só roda num banco que ainda não tem casas, para continuar idempotente.
do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = 'categorias' and column_name = 'casa_id'
    ) then
        return;
    end if;

    insert into categorias (nome) values
        ('Casa'), ('Alimentação'), ('Transporte'), ('Saúde'), ('Educação'),
        ('Lazer'), ('Tecnologia'), ('Vestuário'), ('Pets'), ('Financeiro'), ('Outros')
    on conflict (nome) do nothing;

    insert into cartoes (nome) values
        ('Cartão de Crédito')
    on conflict (nome) do nothing;

    insert into formas_pagamento (nome) values
        ('Pix'), ('Boleto'), ('Débito Automático'), ('Carnê / Loja'), ('Dinheiro')
    on conflict (nome) do nothing;

    -- Uma forma de pagamento para cada cartão (mesmo nome do cartão)
    insert into formas_pagamento (nome, cartao_id)
    select c.nome, c.id from cartoes c
    on conflict (nome) do nothing;
end $$;
