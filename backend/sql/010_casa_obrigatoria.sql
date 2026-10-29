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
