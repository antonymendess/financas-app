"""Importa a planilha "comissoes.xlsx".

- Aba "Comissões": cada linha vira uma comissão; as parcelas marcadas com "x"
  (colunas 1 a 12) entram como recebidas.
- Aba "Possíveis Fechamentos": cada linha vira uma negociação.

Uso (dentro da pasta backend, com o .env preenchido):
    python -m scripts.importar_comissoes --casa 1 --simular
    python -m scripts.importar_comissoes --casa 1 [caminho.xlsx]   # --casa: id em "casas"

Não duplica: comissão com o mesmo cliente e mês de fechamento, ou negociação com
o mesmo cliente, é ignorada (para não sobrescrever o que já foi alterado no app).
A 1ª parcela de cada comissão fica no primeiro dia 15/30 depois do fechamento.
"""

import argparse
import sys
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.db import obter_engine
from repositories.modelos import Comissao, Negociacao
from schemas.comissoes import ComissaoEntrada, NegociacaoEntrada
from scripts.importar_planilha import converter_data, converter_inteiro, converter_valor
from services import comissoes
from services.regras_comissao import proxima_data_pagamento

CAMINHO_PADRAO = Path(__file__).resolve().parents[2] / "comissoes.xlsx"
LINHA_CABECALHO = 4

ETAPAS = {
    "contato inicial": "Contato inicial",
    "proposta enviada": "Proposta enviada",
    "em negociação": "Em negociação",
    "aguardando assinatura": "Aguardando assinatura",
    "fechado": "Fechado",
    "perdido": "Perdido",
}


def _texto(valor) -> str | None:
    texto = str(valor).strip() if valor is not None else ""
    return texto or None


def _linhas(aba):
    """Devolve (número da linha, dicionário cabeçalho -> valor) das linhas preenchidas."""
    linhas = aba.iter_rows(min_row=LINHA_CABECALHO, values_only=True)
    cabecalho = [str(c).strip().lower() if c is not None else "" for c in next(linhas)]
    for numero, linha in enumerate(linhas, start=LINHA_CABECALHO + 1):
        if linha and _texto(linha[0]):
            yield numero, cabecalho, linha


def _valor_coluna(cabecalho, linha, titulo):
    return linha[cabecalho.index(titulo)] if titulo in cabecalho else None


def importar_comissoes(sessao: Session, aba) -> tuple[int, int]:
    criadas = ignoradas = 0
    for numero, cab, linha in _linhas(aba):
        cliente = _texto(linha[0])
        fechamento = converter_data(_valor_coluna(cab, linha, "mês fechamento"))
        implantacao = converter_valor(_valor_coluna(cab, linha, "valor implantação"))
        if fechamento is None or not implantacao:
            print(f"  Linha {numero} ({cliente}) ignorada: falta mês de fechamento ou implantação")
            ignoradas += 1
            continue
        mes = fechamento.replace(day=1)
        existe = sessao.scalar(select(func.count()).where(
            func.lower(Comissao.cliente) == cliente.lower(), Comissao.mes_fechamento == mes
        ))
        if existe:
            ignoradas += 1
            continue

        entrada = ComissaoEntrada(
            cliente=cliente,
            telefone=_texto(_valor_coluna(cab, linha, "telefone")),
            mes_fechamento=mes,
            valor_implantacao=implantacao,
            mensalidade=converter_valor(_valor_coluna(cab, linha, "mensalidade (ref.)")),
            num_parcelas=converter_inteiro(_valor_coluna(cab, linha, "nº parcelas")) or 1,
            data_primeira_parcela=proxima_data_pagamento(fechamento),
        )
        comissao = comissoes.criar(sessao, entrada)

        # Colunas "1" a "12": "x" (ou caixa marcada) = parcela recebida
        for parcela in comissao["parcelas"]:
            marcado = _valor_coluna(cab, linha, f"{parcela.numero}.0") or _valor_coluna(
                cab, linha, str(parcela.numero)
            )
            if marcado is True or str(marcado or "").strip().lower() == "x":
                parcela.paga = True
                parcela.paga_em = parcela.data_prevista
        sessao.commit()
        print(f"  Comissão: {cliente} ({entrada.num_parcelas}x)")
        criadas += 1
    return criadas, ignoradas


def importar_negociacoes(sessao: Session, aba) -> tuple[int, int]:
    criadas = ignoradas = 0
    for _numero, cab, linha in _linhas(aba):
        cliente = _texto(linha[0])
        existe = sessao.scalar(
            select(func.count()).where(func.lower(Negociacao.cliente) == cliente.lower())
        )
        if existe:
            ignoradas += 1
            continue
        etapa = ETAPAS.get(str(_valor_coluna(cab, linha, "etapa") or "").strip().lower(),
                           "Contato inicial")
        probabilidade = converter_inteiro(_valor_coluna(cab, linha, "probabilidade"))
        entrada = NegociacaoEntrada(
            cliente=cliente,
            telefone=_texto(_valor_coluna(cab, linha, "telefone")),
            etapa=etapa,
            probabilidade=probabilidade if probabilidade in (10, 25, 50, 75, 90) else None,
            valor_implantacao=converter_valor(_valor_coluna(cab, linha, "valor implantação")),
            mensalidade=converter_valor(_valor_coluna(cab, linha, "mensalidade (ref.)")),
            num_parcelas=converter_inteiro(_valor_coluna(cab, linha, "nº parcelas")) or 1,
            previsao_fechamento=converter_data(_valor_coluna(cab, linha, "previsão fechamento")),
            ultimo_contato=converter_data(_valor_coluna(cab, linha, "último contato")),
            proxima_acao=_texto(_valor_coluna(cab, linha, "próxima ação")),
        )
        sessao.add(Negociacao(**entrada.model_dump()))
        sessao.commit()
        print(f"  Negociação: {cliente} ({etapa})")
        criadas += 1
    return criadas, ignoradas


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa comissões e negociações da planilha.")
    parser.add_argument("arquivo", nargs="?", default=str(CAMINHO_PADRAO))
    parser.add_argument("--simular", action="store_true", help="não grava nada no banco")
    parser.add_argument("--casa", type=int, required=True,
                        help="id da casa que recebe os dados (tabela casas)")
    args = parser.parse_args()
    caminho = Path(args.arquivo)
    if not caminho.exists():
        sys.exit(f"Arquivo não encontrado: {caminho}")

    planilha = load_workbook(caminho, data_only=False)
    conexao = obter_engine().connect()
    transacao = conexao.begin()
    # Os commits dos serviços viram savepoints; no fim confirmamos (ou desfazemos) tudo
    sessao = Session(bind=conexao, join_transaction_mode="create_savepoint")
    sessao.info["casa_id"] = args.casa  # tudo o que for criado fica nessa casa
    try:
        c = importar_comissoes(sessao, planilha["Comissões"])
        n = importar_negociacoes(sessao, planilha["Possíveis Fechamentos"])
        if args.simular:
            transacao.rollback()
            print("Modo simulação: nada foi gravado.")
        else:
            transacao.commit()
        print(f"Comissões: {c[0]} novas, {c[1]} ignoradas | "
              f"Negociações: {n[0]} novas, {n[1]} ignoradas")
    except Exception:
        transacao.rollback()
        raise
    finally:
        sessao.close()
        conexao.close()


if __name__ == "__main__":
    main()
