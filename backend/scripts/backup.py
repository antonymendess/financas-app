"""Backup dos DADOS do banco em CSV (uma planilha por tabela) e restauração.

A estrutura das tabelas está nas migrações (sql/), então o backup guarda só os
dados. Funciona com qualquer versão do PostgreSQL (não depende de pg_dump).

Uso (dentro da pasta backend):
    python -m scripts.backup salvar                       # banco do DATABASE_URL
    python -m scripts.backup salvar --url URL --pasta X   # outro banco / outra pasta
    python -m scripts.backup restaurar PASTA --url URL_DO_BANCO_DE_TESTES

`restaurar` APAGA os dados do banco de destino e põe os do backup no lugar. O
destino precisa já ter as migrações aplicadas (python -m scripts.migrar --url ...).
Use para testar o backup num banco de testes, nunca direto em produção sem backup.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import psycopg

from core.config import obter_configuracoes
from scripts.migrar import conectar, descrever_destino

PASTA_PADRAO = Path(__file__).resolve().parents[2] / "backups"
IGNORAR = {"migracoes_aplicadas"}  # controle das migrações: é do banco, não dos dados


def _tabelas(conexao: psycopg.Connection) -> list[str]:
    """Tabelas do schema public em ordem de dependência (pais antes dos filhos)."""
    nomes = [r[0] for r in conexao.execute(
        "select tablename from pg_tables where schemaname = 'public' order by tablename"
    )]
    nomes = [n for n in nomes if n not in IGNORAR]
    dependencias = {n: set() for n in nomes}
    for filho, pai in conexao.execute("""
        select c.conrelid::regclass::text, c.confrelid::regclass::text
        from pg_constraint c
        join pg_namespace n on n.oid = c.connamespace
        where c.contype = 'f' and n.nspname = 'public'
    """):
        if filho in dependencias and pai in dependencias and pai != filho:
            dependencias[filho].add(pai)
    ordem, restantes = [], dict(dependencias)
    while restantes:
        prontas = sorted(n for n, pais in restantes.items() if not pais - set(ordem))
        if not prontas:
            raise SystemExit("Dependência circular entre tabelas; não sei a ordem de restauração.")
        ordem += prontas
        for n in prontas:
            del restantes[n]
    return ordem


def _colunas(conexao: psycopg.Connection, tabela: str) -> list[str]:
    """Colunas gravadas (sem as calculadas pelo banco, ex.: valor_comissao)."""
    return [r[0] for r in conexao.execute(
        "select column_name from information_schema.columns "
        "where table_schema = 'public' and table_name = %s and is_generated = 'NEVER' "
        "order by ordinal_position",
        (tabela,),
    )]


def _lista(colunas: list[str]) -> str:
    return ", ".join(f'"{c}"' for c in colunas)


def salvar(url: str, pasta_base: Path = PASTA_PADRAO) -> Path:
    destino = pasta_base / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino.mkdir(parents=True, exist_ok=False)
    resumo = {}
    with conectar(url) as conexao:
        with conexao.transaction():
            # Foto consistente de todas as tabelas no mesmo instante
            conexao.execute("set transaction isolation level repeatable read, read only")
            for tabela in _tabelas(conexao):
                colunas = _colunas(conexao, tabela)
                arquivo = destino / f"{tabela}.csv"
                with conexao.cursor().copy(
                    f'copy (select {_lista(colunas)} from "{tabela}" order by 1) '
                    "to stdout with (format csv, header true)"
                ) as copia, arquivo.open("wb") as saida:
                    for bloco in copia:
                        saida.write(bloco)
                linhas = conexao.execute(f'select count(*) from "{tabela}"').fetchone()[0]
                resumo[tabela] = linhas
    (destino / "resumo.json").write_text(
        json.dumps({"origem": descrever_destino(url), "criado_em": datetime.now().isoformat(),
                    "linhas": resumo}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return destino


def restaurar(url: str, pasta: Path) -> dict[str, int]:
    """Apaga os dados do destino e carrega os CSVs do backup. Tudo numa transação só."""
    resumo = json.loads((pasta / "resumo.json").read_text(encoding="utf-8"))
    contagens = {}
    with conectar(url) as conexao:
        with conexao.transaction():
            tabelas = _tabelas(conexao)
            faltando = set(resumo["linhas"]) - set(tabelas)
            if faltando:
                raise SystemExit(f"O destino não tem as tabelas {sorted(faltando)}: rode as migrações.")
            conexao.execute(
                "truncate " + ", ".join(f'"{t}"' for t in tabelas) + " restart identity cascade"
            )
            for tabela in tabelas:
                arquivo = pasta / f"{tabela}.csv"
                if not arquivo.exists():
                    continue  # tabela criada depois do backup: fica vazia
                with arquivo.open("rb") as entrada:
                    cabecalho = entrada.readline().decode("utf-8").strip()
                    colunas = [c.strip('"') for c in cabecalho.split(",")]
                    entrada.seek(0)
                    with conexao.cursor().copy(
                        f'copy "{tabela}" ({_lista(colunas)}) from stdin with (format csv, header true)'
                    ) as copia:
                        while bloco := entrada.read(65536):
                            copia.write(bloco)
                # Próximo id gerado continua depois do maior restaurado
                if "id" in colunas:
                    conexao.execute(
                        f"select setval(pg_get_serial_sequence('\"{tabela}\"', 'id'), "
                        f'coalesce((select max(id) from "{tabela}"), 0) + 1, false)'
                    )
                contagens[tabela] = conexao.execute(f'select count(*) from "{tabela}"').fetchone()[0]
            diferentes = {t: (n, contagens.get(t)) for t, n in resumo["linhas"].items()
                          if contagens.get(t) != n}
            if diferentes:
                raise SystemExit(f"Contagens não batem (backup, restaurado): {diferentes}")
    return contagens


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backup dos dados em CSV e restauração.")
    sub = parser.add_subparsers(dest="comando", required=True)
    p_salvar = sub.add_parser("salvar", help="exporta os dados para uma pasta")
    p_salvar.add_argument("--url", help="URL do banco (padrão: DATABASE_URL)")
    p_salvar.add_argument("--pasta", type=Path, default=PASTA_PADRAO)
    p_rest = sub.add_parser("restaurar", help="APAGA o destino e carrega um backup")
    p_rest.add_argument("pasta", type=Path)
    p_rest.add_argument("--url", required=True, help="URL do banco de DESTINO (obrigatória)")
    p_rest.add_argument("--sim", action="store_true", help="não pedir confirmação")
    args = parser.parse_args(argumentos)

    if args.comando == "salvar":
        url = args.url or obter_configuracoes().database_url
        if not url:
            print("Defina DATABASE_URL no .env ou use --url.", file=sys.stderr)
            return 1
        print(f"Banco: {descrever_destino(url)}")
        pasta = salvar(url, args.pasta)
        resumo = json.loads((pasta / "resumo.json").read_text(encoding="utf-8"))
        for tabela, n in resumo["linhas"].items():
            print(f"  {tabela:<24} {n:>6} linhas")
        print(f"Backup salvo em {pasta}")
        print("Guarde essa pasta num lugar seguro (tem seus dados financeiros).")
        return 0

    destino = descrever_destino(args.url)
    print(f"ATENÇÃO: os dados de {destino} serão APAGADOS e trocados pelos de {args.pasta}.")
    if not args.sim and input('Digite RESTAURAR para continuar: ').strip() != "RESTAURAR":
        print("Cancelado.")
        return 1
    contagens = restaurar(args.url, args.pasta)
    print(f"Restaurado: {sum(contagens.values())} linhas em {len(contagens)} tabelas. Contagens conferidas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
