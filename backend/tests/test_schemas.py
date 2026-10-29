"""Validação das entradas: campos opcionais vazios (null ou "") devem ser aceitos.

O front envia null em todo campo opcional não preenchido; isso já causou erro 500.
"""

import pytest
from pydantic import ValidationError

from schemas.anotacoes import AnotacaoEntrada
from schemas.cartoes import CartaoEntrada, ContaFixaCartaoEntrada, GastoCartaoEntrada
from schemas.comissoes import ComissaoEntrada, NegociacaoEntrada
from schemas.despesas import DespesaEntrada
from schemas.receitas import ReceitaEntrada

# (schema, campos obrigatórios, campos opcionais)
CASOS = [
    (DespesaEntrada,
     {"descricao": "Luz", "categoria_id": 1, "forma_pagamento_id": 1, "valor_mensal": 10},
     ["num_parcelas", "cancelada_em", "dia_vencimento", "observacao"]),
    (ReceitaEntrada, {"descricao": "Salário", "valor": 3000}, ["dia_recebimento", "data_fim"]),
    (ComissaoEntrada, {"cliente": "ACME", "valor_implantacao": 1000},
     ["telefone", "mensalidade", "observacao"]),
    (CartaoEntrada, {"nome": "Nubank"}, ["dia_fechamento", "dia_vencimento"]),
    (GastoCartaoEntrada, {"descricao": "Mercado", "cartao_id": 1, "valor_total": 50},
     ["categoria_id"]),
    (AnotacaoEntrada, {"texto": "Lembrar"}, ["data", "valor", "pessoa"]),
    (ContaFixaCartaoEntrada, {"descricao": "Netflix", "valor_mensal": 55}, ["categoria_id"]),
    (NegociacaoEntrada, {"cliente": "ACME"},
     ["telefone", "valor_implantacao", "mensalidade", "previsao_fechamento", "ultimo_contato",
      "proxima_acao", "observacao"]),
]


@pytest.mark.parametrize("schema,obrigatorios,opcionais", CASOS)
@pytest.mark.parametrize("vazio", [None, ""])
def test_opcionais_vazios_sao_aceitos(schema, obrigatorios, opcionais, vazio):
    if vazio == "" and schema in (GastoCartaoEntrada, ContaFixaCartaoEntrada):
        pytest.skip("ids não recebem texto")
    entrada = schema(**obrigatorios, **{campo: vazio for campo in opcionais})
    for campo in opcionais:
        assert getattr(entrada, campo) is None


@pytest.mark.parametrize("schema,dados", [
    (DespesaEntrada, {"descricao": "Luz", "categoria_id": 1, "forma_pagamento_id": 1,
                      "valor_mensal": 10, "dia_vencimento": 32}),
    (ReceitaEntrada, {"descricao": "X", "valor": 1, "dia_recebimento": 0}),
    (ComissaoEntrada, {"cliente": "ACME", "valor_implantacao": 1000, "mensalidade": -1}),
    (AnotacaoEntrada, {"texto": "X", "valor": 0}),
    (AnotacaoEntrada, {"texto": "X", "pessoa": "a" * 2001}),
])
def test_limites_continuam_valendo(schema, dados):
    with pytest.raises(ValidationError):
        schema(**dados)


def test_nome_da_categoria_e_obrigatorio_e_curto():
    from schemas.categorias import CategoriaEntrada

    assert CategoriaEntrada(nome="  Mercado  ").nome == "Mercado"
    with pytest.raises(ValidationError):
        CategoriaEntrada(nome="   ")
    with pytest.raises(ValidationError):
        CategoriaEntrada(nome="x" * 61)


def test_escolha_das_conexoes(monkeypatch):
    """DATABASE_URL_APP liga o app_api sem precisar mexer no DATABASE_URL (dono)."""
    import core.conexao as conexao
    from core.config import obter_configuracoes

    def urls(**variaveis):
        for nome in ("DATABASE_URL", "DATABASE_URL_APP", "DATABASE_URL_SISTEMA"):
            monkeypatch.delenv(nome, raising=False)
        for nome, valor in variaveis.items():
            monkeypatch.setenv(nome, valor)
        obter_configuracoes.cache_clear()
        conexao.obter_engine.cache_clear()
        conexao.obter_engine_sistema.cache_clear()
        return (conexao.obter_engine().url.username, conexao.obter_engine_sistema().url.username)

    try:
        assert urls(DATABASE_URL="postgresql://dono:x@h/db") == ("dono", "dono")
        assert urls(DATABASE_URL="postgresql://dono:x@h/db",
                    DATABASE_URL_APP="postgresql://app_api:y@h/db") == ("app_api", "dono")
        assert urls(DATABASE_URL="postgresql://app_api:y@h/db",
                    DATABASE_URL_SISTEMA="postgresql://dono:x@h/db") == ("app_api", "dono")
    finally:
        monkeypatch.undo()
        obter_configuracoes.cache_clear()
        conexao.obter_engine.cache_clear()
        conexao.obter_engine_sistema.cache_clear()
