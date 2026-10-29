"""Erros de negócio e tradução das mensagens de validação para português."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class ErroNegocio(Exception):
    """Erro previsto nas regras do app, devolvido ao front com mensagem clara."""

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class NaoEncontrado(ErroNegocio):
    def __init__(self, recurso: str):
        super().__init__(f"{recurso}: registro não encontrado.", status=404)


# Tradução dos tipos de erro mais comuns do pydantic
_MENSAGENS = {
    "missing": "campo obrigatório",
    "string_too_short": "não pode ficar vazio",
    "string_too_long": "texto muito longo",
    "greater_than": "deve ser maior que {gt}",
    "greater_than_equal": "deve ser maior ou igual a {ge}",
    "less_than_equal": "deve ser menor ou igual a {le}",
    "decimal_parsing": "valor numérico inválido",
    "decimal_max_places": "use no máximo {decimal_places} casas decimais",
    "decimal_max_digits": "valor muito grande",
    "int_parsing": "número inteiro inválido",
    "date_from_datetime_parsing": "data inválida (use AAAA-MM-DD)",
    "date_parsing": "data inválida (use AAAA-MM-DD)",
    "bool_parsing": "valor verdadeiro/falso inválido",
    "literal_error": "opção inválida (use: {expected})",
    "json_invalid": "corpo da requisição inválido",
}


def _traduzir(erro: dict) -> str:
    campo = ".".join(str(p) for p in erro.get("loc", []) if p not in ("body", "query"))
    modelo = _MENSAGENS.get(erro.get("type", ""))
    if modelo:
        try:
            texto = modelo.format(**(erro.get("ctx") or {})).replace(" or ", " ou ")
        except (KeyError, IndexError):
            texto = modelo
    else:
        # Erros vindos de validadores próprios já estão em português
        texto = str(erro.get("msg", "valor inválido")).removeprefix("Value error, ")
    return f"{campo}: {texto}" if campo else texto


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroNegocio)
    async def _erro_negocio(_: Request, exc: ErroNegocio):
        return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})

    @app.exception_handler(RequestValidationError)
    async def _erro_validacao(_: Request, exc: RequestValidationError):
        mensagens = [_traduzir(e) for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "; ".join(mensagens)})

    @app.exception_handler(IntegrityError)
    async def _erro_integridade(_: Request, exc: IntegrityError):
        # Não devolvemos a mensagem do banco (pode conter dados); só uma explicação
        texto = str(exc.orig).lower() if exc.orig else ""
        if "unique" in texto or "duplicate" in texto:
            mensagem = "Já existe um registro com esse nome."
        elif "foreign key" in texto:
            mensagem = "Este registro está em uso ou referencia um item inexistente."
        else:
            mensagem = "Os dados não passaram nas regras do banco (verifique os valores)."
        return JSONResponse(status_code=409, content={"detail": mensagem})
