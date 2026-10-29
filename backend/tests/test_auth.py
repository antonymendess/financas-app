"""Testes de autenticação: sem token -> 401, sem casa -> 403, com casa -> passa."""

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import core.auth
import core.contexto
import services.casas
from core.db import obter_sessao, obter_sessao_sistema
from main import app

CHAVE_PRIVADA = ec.generate_private_key(ec.SECP256R1())
EMISSOR = "https://projeto-teste.supabase.co/auth/v1"


USUARIO_ID = "6f9619ff-8b86-d011-b42d-00c04fc964ff"
SEM_CASA = "0b2f6b8e-0000-4000-8000-000000000001"


def gerar_token(email="eu@exemplo.com", expira_em=3600, chave=CHAVE_PRIVADA, sub=USUARIO_ID, **extra):
    agora = int(time.time())
    dados = {"sub": sub, "email": email, "aud": "authenticated", "iss": EMISSOR,
             "iat": agora, "exp": agora + expira_em, **extra}
    return jwt.encode(dados, chave, algorithm="ES256")


class SessaoFalsa:
    """Substitui o banco nas rotas que só precisam passar pela autenticação."""

    def scalars(self, *_):
        return []


def membro_falso(_sessao, usuario, admin):
    """Só o USUARIO_ID tem casa; qualquer outro login fica sem acesso."""
    if usuario.id != USUARIO_ID:
        return None
    return SimpleNamespace(papel="dono"), SimpleNamespace(id=1, nome="Casa teste")


@pytest.fixture
def cliente(monkeypatch):
    # Em vez de baixar o JWKS do Supabase, usa a chave pública gerada no teste
    monkeypatch.setattr(core.auth, "obter_chave_publica", lambda _: CHAVE_PRIVADA.public_key())
    monkeypatch.setattr(services.casas, "resolver_membro", membro_falso)
    core.contexto.esquecer()  # cada teste começa sem casa guardada em memória
    app.dependency_overrides[obter_sessao] = lambda: SessaoFalsa()
    app.dependency_overrides[obter_sessao_sistema] = lambda: SessaoFalsa()
    yield TestClient(app)
    app.dependency_overrides.clear()
    core.contexto.esquecer()


ROTAS = [
    ("get", "/dashboard"), ("get", "/projecao"), ("get", "/despesas"),
    ("post", "/despesas"), ("get", "/receitas"), ("get", "/comissoes"),
    ("patch", "/comissoes/parcelas/1"), ("get", "/cartoes"), ("get", "/gastos-cartao"),
    ("get", "/anotacoes"), ("patch", "/anotacoes/1/concluir"), ("get", "/opcoes"),
    ("patch", "/despesas/1/pagamento"), ("patch", "/cartoes/1/pagamento"),
    ("get", "/negociacoes"), ("post", "/negociacoes/1/fechar"),
    ("patch", "/comissoes/parcelas/1/data"), ("post", "/cartoes/1/contas-fixas"),
]


@pytest.mark.parametrize("metodo,rota", ROTAS)
def test_rotas_sem_token_retornam_401(cliente, metodo, rota):
    resposta = getattr(cliente, metodo)(rota)
    assert resposta.status_code == 401


@pytest.mark.parametrize("metodo,rota", ROTAS)
def test_login_sem_casa_retorna_403(cliente, metodo, rota):
    cabecalho = {"Authorization": f"Bearer {gerar_token(email='intruso@exemplo.com', sub=SEM_CASA)}"}
    resposta = getattr(cliente, metodo)(rota, headers=cabecalho)
    assert resposta.status_code == 403
    assert "convite" in resposta.json()["detail"]


def test_token_sem_uuid_retorna_401(cliente):
    cabecalho = {"Authorization": f"Bearer {gerar_token(sub='123')}"}
    assert cliente.get("/anotacoes/pessoas", headers=cabecalho).status_code == 401


def test_token_expirado_retorna_401(cliente):
    cabecalho = {"Authorization": f"Bearer {gerar_token(expira_em=-10)}"}
    resposta = cliente.get("/anotacoes/pessoas", headers=cabecalho)
    assert resposta.status_code == 401
    assert "expirada" in resposta.json()["detail"]


def test_token_assinado_por_outra_chave_retorna_401(cliente):
    outra_chave = ec.generate_private_key(ec.SECP256R1())
    cabecalho = {"Authorization": f"Bearer {gerar_token(chave=outra_chave)}"}
    assert cliente.get("/anotacoes/pessoas", headers=cabecalho).status_code == 401


def test_token_com_publico_errado_retorna_401(cliente):
    cabecalho = {"Authorization": f"Bearer {gerar_token(aud='anon')}"}
    assert cliente.get("/anotacoes/pessoas", headers=cabecalho).status_code == 401


def test_membro_de_uma_casa_passa(cliente):
    cabecalho = {"Authorization": f"Bearer {gerar_token(email='EU@exemplo.com')}"}
    resposta = cliente.get("/anotacoes/pessoas", headers=cabecalho)
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_cron_exige_segredo(cliente):
    assert cliente.get("/cron/keepalive").status_code == 401
    errado = {"Authorization": "Bearer outro"}
    assert cliente.get("/cron/keepalive", headers=errado).status_code == 401


def test_cors_so_libera_o_front():
    cliente = TestClient(app)
    pre = {"Access-Control-Request-Method": "GET"}
    liberado = cliente.options("/despesas", headers={**pre, "Origin": "https://meu-front.vercel.app"})
    bloqueado = cliente.options("/despesas", headers={**pre, "Origin": "https://site-malicioso.com"})
    assert liberado.headers.get("access-control-allow-origin") == "https://meu-front.vercel.app"
    assert "access-control-allow-origin" not in bloqueado.headers


def test_casa_fica_guardada_e_evita_consulta_a_cada_clique(cliente, monkeypatch):
    chamadas = []

    def contando(sessao, usuario, admin):
        chamadas.append(usuario.id)
        return membro_falso(sessao, usuario, admin)

    monkeypatch.setattr(services.casas, "resolver_membro", contando)
    cabecalho = {"Authorization": f"Bearer {gerar_token()}"}
    for _ in range(3):
        assert cliente.get("/anotacoes/pessoas", headers=cabecalho).status_code == 200
    assert len(chamadas) == 1
    core.contexto.esquecer()
    cliente.get("/anotacoes/pessoas", headers=cabecalho)
    assert len(chamadas) == 2


def test_sem_casa_nao_fica_guardado(cliente, monkeypatch):
    """Quem acabou de aceitar um convite entra na hora (só o 'tem casa' é guardado)."""
    cabecalho = {"Authorization": f"Bearer {gerar_token(email='novo@exemplo.com', sub=SEM_CASA)}"}
    assert cliente.get("/anotacoes/pessoas", headers=cabecalho).status_code == 403
    monkeypatch.setattr(services.casas, "resolver_membro",
                        lambda *_, **__: (SimpleNamespace(papel="dono"), SimpleNamespace(id=2, nome="Nova")))
    assert cliente.get("/anotacoes/pessoas", headers=cabecalho).status_code == 200
