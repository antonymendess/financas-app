"""Backup em CSV e restauração: os dados voltam inteiros noutro banco."""

import psycopg

from scripts.backup import restaurar, salvar
from scripts.migrar import aplicar_pendentes

C = "(select min(id) from casas)"  # a casa criada pela migração 009
DADOS = f"""
insert into responsaveis (nome, casa_id) values ('Carla', {C}), ('Bruno', {C});
insert into receitas (descricao, valor, dia_recebimento, data_inicio, responsavel_id, casa_id)
    values ('Salário, com vírgula e "aspas"', 2000.00, 6, '2026-01-01', 1, {C});
insert into comissoes (cliente, valor_implantacao, percentual, num_parcelas, data_primeira_parcela,
                       responsavel_id, casa_id)
    values ('Acme', 6000, 25, 3, '2026-09-30', 2, {C});
insert into comissao_parcelas (comissao_id, numero, data_prevista, valor, paga, casa_id)
    values (1, 1, '2026-09-30', 500.00, true, {C}), (1, 2, '2026-10-15', 500.00, false, {C});
insert into conferencias (data, junto, total, ja_entrou, casa_id)
    values ('2026-10-06', false, 2300, '{{receita:1}}', {C});
insert into conferencia_saldos (conferencia_id, responsavel_id, valor, casa_id)
    values (1, 1, 1200, {C}), (1, 2, 1100, {C});
insert into metas (nome, valor_alvo, casa_id) values ('Viagem', 5000, {C});
"""


def test_backup_e_restauracao_trazem_tudo_de_volta(servidor, tmp_path, banco_vazio):
    origem = banco_vazio
    aplicar_pendentes(origem)
    with psycopg.connect(origem) as conexao:
        conexao.execute(DADOS)

    pasta = salvar(origem, tmp_path)

    destino_nome = "restauracao_" + tmp_path.name[-6:].replace("-", "_")
    servidor.psql(f"create database {destino_nome};")
    destino = servidor.get_uri(destino_nome)
    aplicar_pendentes(destino)
    contagens = restaurar(destino, pasta)

    assert contagens["receitas"] == 1 and contagens["conferencia_saldos"] == 2
    with psycopg.connect(destino) as conexao:
        descricao = conexao.execute("select descricao from receitas").fetchone()[0]
        assert descricao == 'Salário, com vírgula e "aspas"'
        # Coluna calculada pelo banco foi recalculada na restauração
        assert conexao.execute("select valor_comissao from comissoes").fetchone()[0] == 1500
        assert conexao.execute("select ja_entrou from conferencias").fetchone()[0] == ["receita:1"]
        # Categorias padrão vieram do backup (não duplicaram com as da migração)
        origem_n = psycopg.connect(origem).execute("select count(*) from categorias").fetchone()[0]
        assert conexao.execute("select count(*) from categorias").fetchone()[0] == origem_n
        # O próximo id continua depois do maior restaurado
        novo = conexao.execute(
            f"insert into responsaveis (nome, casa_id) values ('Teste', {C}) returning id"
        ).fetchone()[0]
        assert novo == 3
