"""Convites, primeiro login do dono atual e limite de 2 pessoas por casa."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from core.auth import Usuario
from core.erros import ErroNegocio
from repositories.modelos import Casa, Categoria, Membro
from services import casas


def usuario(email: str) -> Usuario:
    return Usuario(str(uuid.uuid4()), email)


def test_primeiro_login_do_administrador_assume_a_casa_com_os_dados_antigos(abrir, casa_legado):
    sistema = abrir()
    dono = usuario("eu@exemplo.com")
    membro, casa = casas.resolver_membro(sistema, dono, admin=True)
    assert (casa.id, membro.papel) == (casa_legado, "dono")
    # Segundo login: mesma casa, sem duplicar
    assert casas.resolver_membro(sistema, dono, admin=True)[1].id == casa_legado
    assert sistema.query(Membro).filter_by(casa_id=casa_legado).count() == 1


def test_quem_nao_e_administrador_nem_membro_fica_sem_casa(abrir, casa_legado):
    assert casas.resolver_membro(abrir(), usuario("estranho@exemplo.com"), admin=False) is None


def test_cliente_novo_ganha_casa_propria_com_dados_iniciais(abrir, casa_legado):
    sistema = abrir()
    admin = usuario("eu@exemplo.com")
    casas.resolver_membro(sistema, admin, admin=True)
    convite = casas.convidar_cliente(sistema, admin.id, "Cliente@Exemplo.com", "Família Silva")
    assert casas.ver_convite(sistema, convite.token) == {
        "tipo": "nova_casa", "email": "cliente@exemplo.com", "nome_casa": "Família Silva",
        "situacao": "pendente",
    }

    cliente = usuario("cliente@exemplo.com")
    casa = casas.aceitar(sistema, convite.token, cliente)
    assert casa.id != casa_legado and casa.nome == "Família Silva"
    membro, mesma = casas.resolver_membro(sistema, cliente, admin=False)
    assert (mesma.id, membro.papel) == (casa.id, "dono")
    nomes = {c.nome for c in abrir(casa.id).query(Categoria)}
    assert "Outros" in nomes and len(nomes) == len(casas.CATEGORIAS_PADRAO)
    with pytest.raises(ErroNegocio, match="já foi usado"):
        casas.aceitar(sistema, convite.token, cliente)


def test_convite_so_vale_para_o_email_convidado(abrir, casa_legado):
    sistema = abrir()
    admin = usuario("eu@exemplo.com")
    convite = casas.convidar_cliente(sistema, admin.id, "certo@exemplo.com", None)
    with pytest.raises(ErroNegocio, match="certo@exemplo.com") as erro:
        casas.aceitar(sistema, convite.token, usuario("outro@exemplo.com"))
    assert erro.value.status == 403


def test_convite_expirado_e_token_errado(abrir, casa_legado):
    sistema = abrir()
    convite = casas.convidar_cliente(sistema, str(uuid.uuid4()), "x@exemplo.com", None)
    convite.expira_em = datetime.now(UTC) - timedelta(minutes=1)
    sistema.commit()
    assert casas.ver_convite(sistema, convite.token)["situacao"] == "expirado"
    with pytest.raises(ErroNegocio, match="expirou"):
        casas.aceitar(sistema, convite.token, usuario("x@exemplo.com"))
    with pytest.raises(ErroNegocio) as erro:
        casas.aceitar(sistema, "token-que-nao-existe", usuario("x@exemplo.com"))
    assert erro.value.status == 404


def test_limite_de_duas_pessoas_por_casa(abrir, casa_legado):
    sistema = abrir()
    dono = usuario("eu@exemplo.com")
    casas.resolver_membro(sistema, dono, admin=True)
    sessao = abrir(casa_legado, dono.id)

    convite = casas.convidar_membro(sessao, casa_legado, dono.id, "conjuge@exemplo.com")
    with pytest.raises(ErroNegocio, match="até 2 pessoas"):
        casas.convidar_membro(sessao, casa_legado, dono.id, "terceiro@exemplo.com")
    casas.aceitar(sistema, convite.token, usuario("conjuge@exemplo.com"))
    assert {m.papel for m in casas.membros(sessao, casa_legado)} == {"dono", "membro"}
    with pytest.raises(ErroNegocio, match="até 2 pessoas"):
        casas.convidar_membro(sessao, casa_legado, dono.id, "terceiro@exemplo.com")


def test_login_que_ja_tem_casa_nao_entra_em_outra(abrir, casa_legado):
    sistema = abrir()
    dono = usuario("eu@exemplo.com")
    casas.resolver_membro(sistema, dono, admin=True)
    convite = casas.convidar_cliente(sistema, dono.id, "eu@exemplo.com", None)
    with pytest.raises(ErroNegocio, match="já faz parte"):
        casas.aceitar(sistema, convite.token, dono)


def test_dono_remove_membro_mas_nao_a_si_mesmo(abrir, casa_legado):
    sistema = abrir()
    dono = usuario("eu@exemplo.com")
    membro_dono, _ = casas.resolver_membro(sistema, dono, admin=True)
    sessao = abrir(casa_legado, dono.id)
    convite = casas.convidar_membro(sessao, casa_legado, dono.id, "conjuge@exemplo.com")
    casas.aceitar(sistema, convite.token, usuario("conjuge@exemplo.com"))
    conjuge = next(m for m in casas.membros(sessao, casa_legado) if m.papel == "membro")
    with pytest.raises(ErroNegocio, match="não pode ser removido"):
        casas.remover_membro(sessao, casa_legado, membro_dono.id)
    casas.remover_membro(sessao, casa_legado, conjuge.id)
    assert [m.papel for m in casas.membros(sessao, casa_legado)] == ["dono"]


def test_cancelar_convite(abrir, casa_legado):
    sistema = abrir()
    dono = usuario("eu@exemplo.com")
    casas.resolver_membro(sistema, dono, admin=True)
    sessao = abrir(casa_legado, dono.id)
    convite = casas.convidar_membro(sessao, casa_legado, dono.id, "conjuge@exemplo.com")
    casas.cancelar_convite(sessao, casa_legado, dono.id, convite.id)
    assert casas.convites_visiveis(sessao, casa_legado, dono.id) == []
    assert sistema.get(Casa, casa_legado) is not None
