-- =====================================================================
-- 003: receita lançada a partir de uma parcela de comissão recebida
-- =====================================================================

-- Novo tipo de receita: Comissão
alter table receitas drop constraint if exists receitas_tipo_check;
alter table receitas add constraint receitas_tipo_check
    check (tipo in ('Salário', 'Extra', 'Comissão', 'Outros'));

-- Liga a receita à parcela que a originou (uma receita por parcela).
-- Se a comissão for excluída, a receita continua (o dinheiro entrou).
alter table receitas add column if not exists comissao_parcela_id bigint
    unique references comissao_parcelas (id) on delete set null;
