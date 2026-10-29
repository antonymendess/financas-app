"""Segunda trava: o próprio banco isola as casas para o papel app_api (sql/011).

Aqui não há filtro nenhum do código: as consultas são SQL puro conectado como
app_api. E o fluxo completo da API roda com esse papel, para garantir que as
permissões bastam para o app funcionar em produção.
"""

import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from core.contexto import Contexto, contexto_casa
from core.db import obter_sessao, obter_sessao_sistema
from main import app
from repositories.modelos import Base, ComCasa
from scripts.migrar import aplicar_pendentes
from services.casas import criar_casa
from tests.integracao.dados import popular

TABELAS = sorted(m.class_.__tablename__ for m in Base.registry.mappers if issubclass(m.class_, ComCasa))


def _como_app_api(url: str) -> str:
    partes = urlsplit(url)
    return urlunsplit(partes._replace(netloc=f"app_api:senha-de-teste@{partes.hostname or ''}"))


@pytest.fixture(scope="module")
def banco_rls(servidor):
    nome = f"rls_{uuid.uuid4().hex[:8]}"
    servidor.psql(f"create database {nome};")
    url = servidor.get_uri(nome)
    aplicar_pendentes(url)
    servidor.psql("alter role app_api with login password 'senha-de-teste';")

    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1), poolclass=NullPool)
    sistema = sessionmaker(bind=engine, expire_on_commit=False)()
    a, b = criar_casa(sistema, "Casa A"), criar_casa(sistema, "Casa B")
    sistema.flush()
    popular(sistema, a.id, "AAA")
    popular(sistema, b.id, "BBB")
    sistema.commit()
    yield {"url": url, "app_api": _como_app_api(url), "a": a.id, "b": b.id, "engine": engine}
    engine.dispose()


def _conectar(banco, casa_id=None):
    conexao = psycopg.connect(banco["app_api"])
    if casa_id is not None:
        conexao.execute("select set_config('app.casa_id', %s, false)", (str(casa_id),))
    return conexao


def test_sem_casa_definida_nao_ve_nada(banco_rls):
    with _conectar(banco_rls) as conexao:
        for tabela in TABELAS:
            assert conexao.execute(f'select count(*) from "{tabela}"').fetchone()[0] == 0, tabela


def test_so_ve_a_propria_casa_em_todas_as_tabelas(banco_rls):
    with _conectar(banco_rls, banco_rls["a"]) as conexao:
        for tabela in TABELAS:
            total, de_outra = conexao.execute(
                f'select count(*), count(*) filter (where casa_id <> %s) from "{tabela}"',
                (banco_rls["a"],),
            ).fetchone()
            assert total > 0 and de_outra == 0, tabela
        casas = conexao.execute("select id from casas").fetchall()
        assert casas == [(banco_rls["a"],)]


def test_nao_grava_nem_altera_outra_casa(banco_rls):
    with _conectar(banco_rls, banco_rls["a"]) as conexao:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexao.execute("insert into responsaveis (nome, casa_id) values ('Intruso', %s)",
                            (banco_rls["b"],))
    with _conectar(banco_rls, banco_rls["a"]) as conexao:
        alteradas = conexao.execute("update despesas set valor_mensal = 1 where casa_id = %s",
                                    (banco_rls["b"],)).rowcount
        apagadas = conexao.execute("delete from receitas where casa_id = %s", (banco_rls["b"],)).rowcount
        assert (alteradas, apagadas) == (0, 0)


@pytest.fixture
def cliente_app_api(banco_rls):
    """A API usando o papel app_api (como em produção) para a casa A."""
    engine = create_engine(banco_rls["app_api"].replace("postgresql://", "postgresql+psycopg://", 1),
                           poolclass=NullPool, connect_args={"prepare_threshold": None})
    usuario = str(uuid.uuid4())
    contexto = Contexto(usuario, "a@exemplo.com", banco_rls["a"], "Casa A", "dono", admin=True)

    def sessao_da_casa():
        s = sessionmaker(bind=engine, expire_on_commit=False)()
        s.info.update(casa_id=banco_rls["a"], usuario_id=usuario)
        try:
            yield s
        finally:
            s.close()

    def sessao_sistema():
        s = sessionmaker(bind=banco_rls["engine"], expire_on_commit=False)()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[contexto_casa] = lambda: contexto
    app.dependency_overrides[obter_sessao] = sessao_da_casa
    app.dependency_overrides[obter_sessao_sistema] = sessao_sistema
    yield TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.clear()
    engine.dispose()


def test_fluxo_completo_funciona_com_o_papel_app_api(cliente_app_api):
    c = cliente_app_api
    ok = lambda r: r.status_code < 300 or pytest.fail(f"{r.request.method} {r.request.url}: {r.text}")  # noqa: E731

    pessoa = ok(c.post("/responsaveis", json={"nome": "Carla"})) and c.get("/responsaveis").json()[-1]
    opcoes = c.get("/opcoes").json()
    categoria = ok(c.post("/categorias", json={"nome": "Mercado novo"})) and c.get("/categorias").json()
    cat_id = next(x["id"] for x in categoria if x["nome"] == "Mercado novo")
    forma_id = next(f["id"] for f in opcoes["formas_pagamento"] if f["cartao_id"] is None)
    despesa = c.post("/despesas", json={"descricao": "Luz", "categoria_id": cat_id,
                                        "forma_pagamento_id": forma_id, "valor_mensal": 120,
                                        "responsavel_id": pessoa["id"]})
    ok(despesa)
    ok(c.patch(f"/despesas/{despesa.json()['id']}/pagamento", json={"ano": 2026, "mes": 10}))
    ok(c.post("/receitas", json={"descricao": "Salário", "valor": 3000, "dia_recebimento": 5}))
    cartao = c.post("/cartoes", json={"nome": "Cartão novo", "dia_fechamento": 5, "dia_vencimento": 15})
    ok(cartao)
    ok(c.post("/gastos-cartao", json={"descricao": "Mercado", "cartao_id": cartao.json()["id"],
                                      "valor_total": 90, "num_parcelas": 3}))
    ok(c.post(f"/cartoes/{cartao.json()['id']}/contas-fixas", json={"descricao": "Streaming", "valor_mensal": 30}))
    comissao = c.post("/comissoes", json={"cliente": "Cliente", "valor_implantacao": 1000, "num_parcelas": 2})
    ok(comissao)
    parcela = comissao.json()["parcelas"][0]["id"]
    ok(c.patch(f"/comissoes/parcelas/{parcela}", json={"paga": True, "lancar_receita": True}))
    ok(c.post("/anotacoes", json={"texto": "Pagar João", "valor": 50}))
    meta = c.post("/metas", json={"nome": "Viagem", "valor_alvo": 1000})
    ok(meta)
    ok(c.post(f"/metas/{meta.json()['id']}/movimentos", json={"valor": 100}))
    ok(c.post("/conferencias", json={"saldos": [{"responsavel_id": pessoa["id"], "valor": 900}]}))
    ok(c.delete(f"/categorias/{cat_id}?mover_para={next(x['id'] for x in categoria if x['nome'] == 'Outros')}"))
    ok(c.post("/casa/convites", json={"email": "conjuge@exemplo.com"}))
    ok(c.post("/admin/convites", json={"email": "cliente@exemplo.com", "nome_casa": "Família Silva"}))
    ok(c.put("/casa", json={"nome": "Casa A renomeada"}))

    for rota in ("/dashboard", "/projecao", "/periodo?inicio=2026-09&fim=2026-11", "/metas/painel",
                 "/despesas", "/gastos-cartao", "/comissoes", "/negociacoes", "/anotacoes",
                 "/conferencias", "/casa/convites", "/eu"):
        resposta = c.get(rota)
        ok(resposta)
        assert "BBB" not in resposta.text, rota
    assert len(c.get("/casa/convites").json()) == 2
