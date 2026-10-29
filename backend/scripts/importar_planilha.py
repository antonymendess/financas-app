"""Importa as despesas da aba "Cadastro" da planilha despesas.xlsx.

Uso (dentro da pasta backend, com o .env preenchido):
    python -m scripts.importar_planilha                 # usa ../despesas.xlsx
    python -m scripts.importar_planilha caminho.xlsx
    python -m scripts.importar_planilha --simular       # só mostra o que faria

Pode ser executado várias vezes: uma despesa com a mesma descrição e a mesma
1ª cobrança é ATUALIZADA em vez de duplicada.
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import text

from core.db import obter_engine

ABA = "Cadastro"
CAMINHO_PADRAO = Path(__file__).resolve().parents[2] / "despesas.xlsx"

# Cabeçalhos esperados -> nome interno. As demais colunas (fórmulas) são ignoradas.
COLUNAS = {
    "item / descrição": "descricao",
    "categoria": "categoria",
    "cartão / forma": "forma",
    "valor mensal": "valor",
    "nº parcelas": "parcelas",
    "1ª cobrança": "primeira",
    "cancelei em": "cancelada",
}

# O Excel conta os dias a partir de 30/12/1899 (número serial)
_EPOCA_EXCEL = date(1899, 12, 30)


def converter_data(valor) -> date | None:
    """Aceita datetime, date, número serial do Excel ou texto dd/mm/aaaa."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        return _EPOCA_EXCEL + timedelta(days=int(valor))
    texto = str(valor).strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida: {texto!r}")


def converter_valor(valor) -> Decimal | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    texto = str(valor).replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"valor inválido: {valor!r}") from exc


def converter_inteiro(valor) -> int | None:
    if valor is None or valor == "":
        return None
    return int(float(valor))


def _normalizar(nome) -> str:
    return str(nome or "").strip().lower()


def ler_planilha(caminho: Path) -> list[dict]:
    """Lê as linhas válidas da aba Cadastro (linhas vazias são ignoradas)."""
    planilha = load_workbook(caminho, read_only=True, data_only=False)
    if ABA not in planilha.sheetnames:
        raise SystemExit(f'A planilha não tem a aba "{ABA}".')
    linhas = planilha[ABA].iter_rows(values_only=True)

    cabecalho = [_normalizar(c) for c in next(linhas)]
    indices = {}
    for titulo, interno in COLUNAS.items():
        if titulo not in cabecalho:
            raise SystemExit(f'Coluna "{titulo}" não encontrada na aba {ABA}.')
        indices[interno] = cabecalho.index(titulo)

    registros = []
    for numero, linha in enumerate(linhas, start=2):
        dados = {nome: linha[i] if i < len(linha) else None for nome, i in indices.items()}
        descricao = str(dados["descricao"] or "").strip()
        if not descricao:
            continue  # linha vazia
        try:
            registros.append({
                "linha": numero,
                "descricao": descricao,
                "categoria": _normalizar(dados["categoria"]),
                "forma": _normalizar(dados["forma"]),
                "valor": converter_valor(dados["valor"]),
                "parcelas": converter_inteiro(dados["parcelas"]),
                "primeira": converter_data(dados["primeira"]),
                "cancelada": converter_data(dados["cancelada"]),
            })
        except ValueError as erro:
            print(f"  Linha {numero} ignorada: {erro}")
    return registros


def importar(caminho: Path, simular: bool) -> None:
    registros = ler_planilha(caminho)
    print(f"{len(registros)} despesas encontradas na planilha.")

    with obter_engine().begin() as conexao:
        categorias = {
            _normalizar(nome): id_
            for id_, nome in conexao.execute(text("select id, nome from categorias"))
        }
        formas = {
            _normalizar(nome): id_
            for id_, nome in conexao.execute(text("select id, nome from formas_pagamento"))
        }

        inseridas = atualizadas = ignoradas = 0
        for r in registros:
            problema = None
            if r["valor"] is None or r["valor"] <= 0:
                problema = "valor mensal vazio ou inválido"
            elif r["primeira"] is None:
                problema = "1ª cobrança vazia"
            elif r["forma"] not in formas:
                problema = f'forma de pagamento "{r["forma"]}" não cadastrada'
            if problema:
                print(f'  Linha {r["linha"]} ({r["descricao"]}) ignorada: {problema}')
                ignoradas += 1
                continue

            categoria_id = categorias.get(r["categoria"])
            if categoria_id is None:
                print(f'  Linha {r["linha"]}: categoria "{r["categoria"]}" desconhecida, usando "Outros".')
                categoria_id = categorias["outros"]

            parametros = {
                "descricao": r["descricao"],
                "categoria_id": categoria_id,
                "forma_id": formas[r["forma"]],
                "valor": r["valor"],
                "parcelas": r["parcelas"],
                "primeira": r["primeira"],
                "cancelada": r["cancelada"],
                "dia": r["primeira"].day,
            }
            existente = conexao.execute(
                text(
                    "select id from despesas "
                    "where lower(descricao) = lower(:descricao) and primeira_cobranca = :primeira"
                ),
                parametros,
            ).scalar()

            if existente:
                conexao.execute(
                    text(
                        "update despesas set categoria_id = :categoria_id, "
                        "forma_pagamento_id = :forma_id, valor_mensal = :valor, "
                        "num_parcelas = :parcelas, cancelada_em = :cancelada "
                        "where id = :id"
                    ),
                    {**parametros, "id": existente},
                )
                atualizadas += 1
            else:
                conexao.execute(
                    text(
                        "insert into despesas (descricao, categoria_id, forma_pagamento_id, "
                        "valor_mensal, num_parcelas, primeira_cobranca, cancelada_em, "
                        "dia_vencimento) values (:descricao, :categoria_id, :forma_id, "
                        ":valor, :parcelas, :primeira, :cancelada, :dia)"
                    ),
                    parametros,
                )
                inseridas += 1

        if simular:
            conexao.rollback()
            print("Modo simulação: nada foi gravado.")

    print(f"Inseridas: {inseridas} | Atualizadas: {atualizadas} | Ignoradas: {ignoradas}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa a aba Cadastro para a tabela despesas.")
    parser.add_argument("arquivo", nargs="?", default=str(CAMINHO_PADRAO))
    parser.add_argument("--simular", action="store_true", help="não grava nada no banco")
    args = parser.parse_args()

    caminho = Path(args.arquivo)
    if not caminho.exists():
        sys.exit(f"Arquivo não encontrado: {caminho}")
    with obter_engine().connect() as conexao:
        separado = conexao.execute(text("select to_regclass('public.casas') is not null")).scalar()
    if separado:
        # Este importador grava SQL direto, sem casa: depois da migração 009 misturaria dados
        sys.exit("Este importador é da versão de uso pessoal e não funciona com casas "
                 "(migração 009). Cadastre as despesas pelo app.")
    importar(caminho, args.simular)


if __name__ == "__main__":
    main()
