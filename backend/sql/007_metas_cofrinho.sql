-- =====================================================================
-- 007: metas viram "cofrinho" (só informativas)
--
-- A meta passa a ser: quanto quero juntar, até quando e quanto já guardei.
-- A regra mensal (% da sobra etc.) deixa de ser obrigatória. Nada é apagado:
-- metas, valores guardados e regras antigas continuam no banco.
-- =====================================================================

alter table metas alter column regra_valor drop not null;
