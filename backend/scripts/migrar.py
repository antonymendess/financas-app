"""Aplica as migrações de sql/ em ordem e registra o que já foi aplicado.

Uso (dentro da pasta backend, com DATABASE_URL no .env ou no ambiente):
    python -m scripts.migrar --status          # mostra aplicadas e pendentes
    python -m scripts.migrar --simular         # mostra o que faria, sem mudar nada
    python -m scripts.migrar                   # aplica as pendentes (pede confirmação)
    python -m scripts.migrar --marcar-ate 008  # banco onde 001..008 já foram rodadas à mão:
                                               # só registra, NÃO executa nada

Cada migração roda numa transação própria: se der erro, nada dela fica aplicado e
as seguintes não rodam. O controle fica na tabela `migracoes_aplicadas`.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import psycopg

from core.config import obter_configuracoes

PASTA_SQL = Path(__file__).resolve().parents[1] / "sql"

TABELA_CONTROLE = """
create table if not exists migracoes_aplicadas (
    nome         text primary key,
    aplicada_em  timestamptz not null default now(),
    executada    boolean not null default true  -- false = só marcada (--marcar-ate)
);
alter table migracoes_aplicadas enable row level security;
revoke all on migracoes_aplicadas from anon, authenticated;
"""


@dataclass(frozen=True)
class Migracao:
    numero: str  # "006"
    nome: str  # "006_responsaveis.sql"
    caminho: Path


def listar_migracoes(pasta: Path = PASTA_SQL) -> list[Migracao]:
    """Arquivos NNN_nome.sql em ordem numérica."""
    migracoes = []
    for caminho in sorted(pasta.glob("[0-9][0-9][0-9]_*.sql")):
        migracoes.append(Migracao(caminho.name[:3], caminho.name, caminho))
    numeros = [m.numero for m in migracoes]
    if len(numeros) != len(set(numeros)):
        raise SystemExit("Há duas migrações com o mesmo número em sql/.")
    return migracoes


def _url_psycopg(url: str) -> str:
    # Aceita também o formato do SQLAlchemy (postgresql+psycopg://)
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def descrever_destino(url: str) -> str:
    """Host e banco, sem usuário nem senha (para confirmar onde vai rodar)."""
    partes = urlsplit(_url_psycopg(url))
    return f"{partes.hostname or 'socket local'}:{partes.port or 5432}{partes.path}"


def conectar(url: str) -> psycopg.Connection:
    # prepare_threshold=None: o pooler do Supabase (modo transaction) não aceita prepared statements
    return psycopg.connect(_url_psycopg(url), prepare_threshold=None, autocommit=False)


def _garantir_controle(conexao: psycopg.Connection) -> None:
    with conexao.transaction():
        conexao.execute(TABELA_CONTROLE)


def aplicadas(conexao: psycopg.Connection) -> set[str]:
    _garantir_controle(conexao)
    return {linha[0] for linha in conexao.execute("select nome from migracoes_aplicadas")}


def pendentes(conexao: psycopg.Connection, migracoes: list[Migracao]) -> list[Migracao]:
    feitas = aplicadas(conexao)
    return [m for m in migracoes if m.nome not in feitas]


def aplicar(conexao: psycopg.Connection, migracao: Migracao) -> None:
    sql = migracao.caminho.read_text(encoding="utf-8")
    _garantir_controle(conexao)
    with conexao.transaction():
        conexao.execute(sql)
        conexao.execute(
            "insert into migracoes_aplicadas (nome, executada) values (%s, true)", (migracao.nome,)
        )


def marcar(conexao: psycopg.Connection, migracao: Migracao) -> None:
    _garantir_controle(conexao)
    with conexao.transaction():
        conexao.execute(
            "insert into migracoes_aplicadas (nome, executada) values (%s, false) "
            "on conflict (nome) do nothing",
            (migracao.nome,),
        )


def aplicar_pendentes(url: str, migracoes: list[Migracao] | None = None) -> list[str]:
    """Aplica tudo o que falta, sem perguntar (usado pelos testes e pela CLI)."""
    migracoes = migracoes if migracoes is not None else listar_migracoes()
    feitas = []
    with conectar(url) as conexao:
        for migracao in pendentes(conexao, migracoes):
            aplicar(conexao, migracao)
            feitas.append(migracao.nome)
    return feitas


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrações do banco (pasta sql/).")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--status", action="store_true", help="lista aplicadas e pendentes")
    grupo.add_argument("--simular", action="store_true", help="mostra o que faria")
    grupo.add_argument("--marcar-ate", metavar="NNN",
                       help="registra 001..NNN como aplicadas SEM executar (banco já migrado à mão)")
    parser.add_argument("--sim", action="store_true", help="não pedir confirmação")
    parser.add_argument("--url", help="URL do banco (padrão: DATABASE_URL)")
    args = parser.parse_args(argumentos)

    url = args.url or obter_configuracoes().database_url
    if not url:
        print("Defina DATABASE_URL no .env ou use --url.", file=sys.stderr)
        return 1
    migracoes = listar_migracoes()
    print(f"Banco: {descrever_destino(url)}")

    with conectar(url) as conexao:
        faltam = pendentes(conexao, migracoes)

        if args.status or args.simular:
            feitas = [m for m in migracoes if m not in faltam]
            print(f"Aplicadas ({len(feitas)}): {', '.join(m.numero for m in feitas) or '-'}")
            print(f"Pendentes ({len(faltam)}): {', '.join(m.nome for m in faltam) or '-'}")
            return 0

        if args.marcar_ate:
            alvo = [m for m in faltam if m.numero <= args.marcar_ate.zfill(3)]
            if not alvo:
                print("Nada para marcar.")
                return 0
            print("Serão MARCADAS como aplicadas (sem executar):", ", ".join(m.nome for m in alvo))
            if not args.sim and input("Confirmar? [s/N] ").strip().lower() != "s":
                print("Cancelado.")
                return 1
            for migracao in alvo:
                marcar(conexao, migracao)
            print("Feito.")
            return 0

        if not faltam:
            print("Nenhuma migração pendente.")
            return 0
        print("Serão aplicadas:", ", ".join(m.nome for m in faltam))
        if not args.sim and input("Fez backup e quer aplicar? [s/N] ").strip().lower() != "s":
            print("Cancelado.")
            return 1
        for migracao in faltam:
            print(f"  aplicando {migracao.nome}...", end=" ", flush=True)
            try:
                aplicar(conexao, migracao)
            except psycopg.Error as erro:
                print("ERRO")
                print(f"{migracao.nome} não foi aplicada (nada dela ficou no banco): {erro}",
                      file=sys.stderr)
                return 1
            print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
