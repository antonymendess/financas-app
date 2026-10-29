"""Isolamento entre casas (bloqueia o lançamento multiusuário).

Duas casas (A e B), cada uma com dados em todas as tabelas. Logado como A:
- nenhuma rota devolve dados de B;
- nenhuma rota consegue ler, alterar ou excluir registros de B pelo id;
- não dá para usar ids de B dentro de cadastros de A;
- os dados de B ficam exatamente iguais no final.
A lista de rotas sai do próprio app: rota nova sem cobertura faz o teste falhar.
"""

import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from core.contexto import Contexto, contexto_casa
from core.db import obter_sessao, obter_sessao_sistema
from core.erros import ErroNegocio
from main import app
from repositories.modelos import Base, ComCasa, Convite, Membro
from schemas.despesas import DespesaEntrada
from schemas.cartoes import GastoCartaoEntrada
from services import cartoes, despesas, receitas, responsaveis
from services.casas import criar_casa
from tests.integracao.dados import popular

MARCA_B = "SEGREDO_B"
SEM_CASA = {"/health", "/cron/keepalive", "/convites/{token}", "/convites/{token}/aceitar"}


@pytest.fixture
def duas_casas(abrir):
    sistema = abrir()
    a, b = criar_casa(sistema, "Casa A"), criar_casa(sistema, f"Casa {MARCA_B}")
    sistema.flush()
    ids_a = popular(sistema, a.id, "AAA")
    ids_b = popular(sistema, b.id, MARCA_B)
    membro_b = Membro(casa_id=b.id, usuario_id=uuid.uuid4(), email="b@exemplo.com", papel="membro")
    convite_b = Convite(token="token-b", tipo="membro", casa_id=b.id, email="b2@exemplo.com",
                        criado_por=uuid.uuid4(), expira_em=datetime.now(UTC) + timedelta(days=7))
    sistema.add_all([membro_b, convite_b])
    sistema.commit()
    ids_b.update(membro_id=membro_b.id, convite_id=convite_b.id)
    return a.id, ids_a, b.id, ids_b


def foto(abrir, casa_id: int) -> dict:
    """Todas as linhas da casa, tabela por tabela (para conferir que nada mudou)."""
    sessao = abrir()
    retrato = {}
    for mapper in Base.registry.mappers:
        modelo = mapper.class_
        if not issubclass(modelo, ComCasa):
            continue
        linhas = sessao.scalars(select(modelo).where(modelo.casa_id == casa_id).order_by(modelo.id))
        retrato[modelo.__tablename__] = [
            {c.key: getattr(o, c.key) for c in mapper.column_attrs} for o in linhas
        ]
    retrato["membros"] = [(m.id, m.email) for m in sessao.scalars(select(Membro).where(Membro.casa_id == casa_id))]
    retrato["convites"] = [(c.id, c.email) for c in sessao.scalars(select(Convite).where(Convite.casa_id == casa_id))]
    sessao.close()
    return retrato


@pytest.fixture
def cliente_a(abrir, duas_casas):
    casa_a = duas_casas[0]
    usuario = str(uuid.uuid4())
    contexto = Contexto(usuario, "a@exemplo.com", casa_a, "Casa A", "dono", admin=True)
    app.dependency_overrides[contexto_casa] = lambda: contexto
    app.dependency_overrides[obter_sessao] = lambda: abrir(casa_a, usuario)
    app.dependency_overrides[obter_sessao_sistema] = lambda: abrir()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _rotas():
    for caminho, operacoes in app.openapi()["paths"].items():
        if caminho in SEM_CASA:
            continue
        for metodo, operacao in operacoes.items():
            schema = (operacao.get("requestBody", {}).get("content", {})
                      .get("application/json", {}).get("schema", {}).get("$ref", ""))
            yield metodo, caminho, schema.split("/")[-1]


def _corpo(modelo: str, ids_a: dict) -> dict | None:
    """Corpo válido para cada tipo de entrada (com referências da própria casa A)."""
    corpos = {
        "AnotacaoEntrada": {"texto": "nova"},
        "ConclusaoAnotacao": {"concluida": True},
        "CartaoEntrada": {"nome": "Cartão novo"},
        "ContaFixaCartaoEntrada": {"descricao": "Assinatura", "valor_mensal": 10},
        "Pagamento": {"ano": 2026, "mes": 10, "pago": True},
        "CasaEntrada": {"nome": "Casa A"},
        "ConviteMembroEntrada": {"email": "novo@exemplo.com"},
        "ConviteClienteEntrada": {"email": "cliente@exemplo.com"},
        "CategoriaEntrada": {"nome": "Categoria nova"},
        "ComissaoEntrada": {"cliente": "Cliente", "valor_implantacao": 100},
        "PagamentoParcela": {"paga": True},
        "DataParcela": {"data_prevista": "2026-11-15"},
        "ConferenciaEntrada": {"junto": True, "total": 10},
        "QuemPagaEntrada": {"ano": 2026, "mes": 11},
        "DespesaEntrada": {"descricao": "Conta", "categoria_id": ids_a["categoria_id"],
                           "forma_pagamento_id": ids_a["forma_id"], "valor_mensal": 10},
        "GastoCartaoEntrada": {"descricao": "Gasto", "cartao_id": ids_a["cartao_id"], "valor_total": 10},
        "MetaEntrada": {"nome": "Meta"},
        "FechamentoMes": {"ano": 2026, "mes": 10},
        "MovimentoEntrada": {"valor": 10},
        "NegociacaoEntrada": {"cliente": "Cliente"},
        "FechamentoNegociacao": {},
        "ReceitaEntrada": {"descricao": "Receita", "valor": 10},
        "ResponsavelEntrada": {"nome": "Pessoa nova"},
    }
    if not modelo:
        return None
    assert modelo in corpos, f"Rota com corpo {modelo} sem caso de teste: acrescente em _corpo()"
    return corpos[modelo]


def test_nenhuma_rota_mostra_ou_altera_dados_de_outra_casa(abrir, duas_casas, cliente_a):
    _, ids_a, casa_b, ids_b = duas_casas
    antes = foto(abrir, casa_b)
    testadas_com_id = 0

    for metodo, caminho, modelo in _rotas():
        parametros = re.findall(r"{(\w+)}", caminho)
        if parametros:
            faltando = [p for p in parametros if p not in ids_b]
            assert not faltando, f"{caminho}: sem id de teste para {faltando}"
            url = caminho.format(**{p: ids_b[p] for p in parametros})
        else:
            url = caminho
        if caminho == "/periodo":
            url += "?inicio=2026-09&fim=2026-11"
        resposta = cliente_a.request(metodo.upper(), url, json=_corpo(modelo, ids_a))

        assert resposta.status_code < 500, f"{metodo} {url}: erro {resposta.status_code} {resposta.text}"
        assert MARCA_B not in resposta.text, f"{metodo} {url} devolveu dados da casa B"
        if parametros:
            testadas_com_id += 1
            # Id de outra casa: tem que ser "não encontrado" (nunca sucesso)
            assert resposta.status_code in (403, 404), (
                f"{metodo} {url} com id da casa B respondeu {resposta.status_code}: {resposta.text}"
            )

    assert testadas_com_id >= 30
    assert foto(abrir, casa_b) == antes, "Dados da casa B mudaram"


def test_cadastro_nao_aceita_referencias_de_outra_casa(abrir, duas_casas):
    casa_a, ids_a, _, ids_b = duas_casas
    sessao = abrir(casa_a)
    with pytest.raises(ErroNegocio):
        despesas.criar(sessao, DespesaEntrada(
            descricao="x", categoria_id=ids_b["categoria_id"], forma_pagamento_id=ids_a["forma_id"],
            valor_mensal=Decimal("10"),
        ))
    with pytest.raises(ErroNegocio):
        cartoes.criar_gasto(sessao, GastoCartaoEntrada(
            descricao="x", cartao_id=ids_b["cartao_id"], valor_total=Decimal("10"),
        ))
    with pytest.raises(ErroNegocio):
        responsaveis.validar(sessao, ids_b["responsavel_id"])


def test_listagens_e_carga_do_mes_so_trazem_a_propria_casa(abrir, duas_casas):
    from repositories.consultas import carregar_dados_financeiros

    casa_a, *_ = duas_casas
    sessao = abrir(casa_a)
    dados = carregar_dados_financeiros(sessao)
    textos = repr(dados) + repr(receitas.listar(sessao)) + repr(despesas.listar(sessao))
    assert MARCA_B not in textos
    assert "AAA" in textos


def test_registro_novo_fica_na_casa_da_sessao(abrir, duas_casas):
    from schemas.responsaveis import ResponsavelEntrada

    casa_a, *_ = duas_casas
    pessoa = responsaveis.criar(abrir(casa_a), ResponsavelEntrada(nome="Nova"))
    assert pessoa.casa_id == casa_a
