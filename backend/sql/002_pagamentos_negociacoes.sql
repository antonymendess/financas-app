-- =====================================================================
-- 002: pagamentos de contas/faturas e negociações (possíveis fechamentos)
-- =====================================================================

-- Conta (despesa) marcada como paga em um mês. competencia = 1º dia do mês.
create table if not exists despesa_pagamentos (
    id           bigint generated always as identity primary key,
    despesa_id   bigint not null references despesas (id) on delete cascade,
    competencia  date not null check (extract(day from competencia) = 1),
    pago_em      date not null default current_date,
    created_at   timestamptz not null default now(),
    unique (despesa_id, competencia)
);

-- Fatura de cartão marcada como paga em um mês
create table if not exists fatura_pagamentos (
    id           bigint generated always as identity primary key,
    cartao_id    bigint not null references cartoes (id) on delete cascade,
    competencia  date not null check (extract(day from competencia) = 1),
    pago_em      date not null default current_date,
    created_at   timestamptz not null default now(),
    unique (cartao_id, competencia)
);

-- Negociações em andamento; ao fechar, viram uma comissão (comissao_id)
create table if not exists negociacoes (
    id                   bigint generated always as identity primary key,
    cliente              text not null check (length(trim(cliente)) > 0),
    telefone             text,
    etapa                text not null default 'Contato inicial'
                         check (etapa in ('Contato inicial', 'Proposta enviada', 'Em negociação',
                                          'Aguardando assinatura', 'Fechado', 'Perdido')),
    probabilidade        smallint check (probabilidade in (10, 25, 50, 75, 90)),
    valor_implantacao    numeric(12, 2) check (valor_implantacao is null or valor_implantacao > 0),
    mensalidade          numeric(12, 2) check (mensalidade is null or mensalidade >= 0),
    percentual           numeric(5, 2) not null default 25
                         check (percentual > 0 and percentual <= 100),
    num_parcelas         integer not null default 1 check (num_parcelas > 0),
    previsao_fechamento  date,
    ultimo_contato       date,
    proxima_acao         text,
    observacao           text,
    comissao_id          bigint references comissoes (id) on delete set null,
    transferido_em       date,
    created_at           timestamptz not null default now()
);

-- Mesmo padrão de segurança: RLS sem policies e sem permissões para a API pública
alter table despesa_pagamentos enable row level security;
alter table fatura_pagamentos  enable row level security;
alter table negociacoes        enable row level security;

revoke all on despesa_pagamentos, fatura_pagamentos, negociacoes from anon, authenticated;
