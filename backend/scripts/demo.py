"""Preenche (ou refaz) os dados fictícios da demonstração na hora, sem esperar o cron.

Uso (dentro da pasta backend, com DATABASE_URL e DEMO_EMAIL no .env):
    python -m scripts.demo

O login de DEMO_EMAIL precisa já existir no Supabase Auth. APAGA os dados da casa
dele e põe os fictícios no lugar.
"""

import sys

from core.conexao import obter_sessao_sistema
from core.config import obter_configuracoes
from services import demo
from services.calculos import hoje


def main() -> None:
    config = obter_configuracoes()
    if not config.demo_email:
        sys.exit("Defina DEMO_EMAIL no .env.")
    if config.demo_email == config.allowed_email:
        sys.exit("DEMO_EMAIL não pode ser o mesmo e-mail do administrador (ALLOWED_EMAIL).")

    sessao = next(obter_sessao_sistema())
    try:
        usuario_id = demo.usuario_por_email(sessao, config.demo_email)
        if usuario_id is None:
            sys.exit(f"Nenhum login com o e-mail {config.demo_email} no Supabase Auth.")
        casa_id = demo.recriar(sessao, usuario_id, config.demo_email, hoje())
    finally:
        sessao.close()
    print(f"Demonstração pronta na casa {casa_id}.")


if __name__ == "__main__":
    main()
