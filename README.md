# Controle Financeiro Pessoal

Aplicação web *mobile-first* (instalável como PWA) para controle de finanças pessoais:
contas fixas e parceladas, faturas de cartão, receitas, comissões de vendas, anotações,
metas de economia e um simulador de cenários.

**Demo:** em breve (dados fictícios)

## Funcionalidades

- **Visão geral do mês**: saldo previsto, contas a pagar com marcação de pagamento,
  gráfico de receitas × despesas dos próximos 12 meses e despesas por categoria.
- **Despesas**: contas fixas ou parceladas, com cancelamento a partir de uma data e
  acompanhamento de quanto ainda falta pagar.
- **Cartões**: gastos avulsos e parcelados distribuídos na fatura correta conforme os
  dias de fechamento e vencimento de cada cartão.
- **Receitas**: recorrentes (salário) ou pontuais.
- **Comissões e negociações**: comissões parceladas com controle de recebimento e um
  funil de negociações que, ao fechar, vira comissão.
- **Anotações**: lembretes e dívidas informais, com interpretação de texto livre
  (data e valor) e opção de somar no saldo do mês.
- **Metas (cofrinho)**: quanto quero juntar e até quando; os valores guardados são
  anotados à parte e não mexem no saldo. Mostra progresso com marcos, ritmo médio,
  previsão de conclusão, quanto guardar por mês para chegar na data e meses seguidos
  guardando.
- **Conferência com o banco**: informe o saldo real (por pessoa ou tudo junto) e o app
  calcula quanto deve sobrar no fim do mês a partir dele, somando o que ainda vai entrar e
  descontando o que falta pagar. Os gastos pequenos não anotados já estão no saldo.
- **Filtros no Início**: por pessoa (Todos / cada pessoa / Conjunto) e visão por período
  (vários meses somados, com maiores despesas, categorias e cada pessoa no período).
- **Pessoas da casa**: cada receita, conta, cartão e comissão pode ser de uma pessoa ou do
  "Conjunto". O painel mostra quanto cada um recebe, gasta e quanto sobra depois da sua parte
  nas contas conjuntas (divididas proporcionalmente à renda).
- **Categorias**: criar, renomear e excluir (movendo os lançamentos para outra). "Outros"
  é a padrão do sistema e fica protegida. Dá para criar uma categoria direto nos formulários.
- **Simulador**: orçamento, rendimento de investimentos com juros compostos e cálculo de
  aporte para uma meta, sem afetar os dados reais.

## Stack

| Camada    | Tecnologias                                                         |
|-----------|---------------------------------------------------------------------|
| Frontend  | React, Vite, Tailwind CSS, Recharts, React Router, PWA              |
| Backend   | Python, FastAPI, SQLAlchemy 2, Pydantic 2                           |
| Banco     | PostgreSQL (Supabase), migrações SQL versionadas                    |
| Auth      | Supabase Auth (JWT validado na API via JWKS)                        |
| Deploy    | Vercel (frontend estático + backend como Vercel Function, cron)     |
| Testes    | pytest                                                              |

```
/backend   API REST (FastAPI) publicada como Vercel Function
/frontend  SPA em React
```

## Arquitetura e decisões

- **Camadas no backend**: `routers` (HTTP) → `services` (regras de negócio) →
  `repositories` (ORM e consultas). Validação de entrada e saída com Pydantic e
  mensagens de erro traduzidas para português.
- **Projeção em memória**: os dados financeiros são carregados com um número fixo de
  consultas e o cálculo de cada mês é feito por funções puras
  ([`services/projecao.py`](backend/services/projecao.py)), o que torna a lógica
  testável sem banco e evita consultas mês a mês.
- **Serverless**: conexão via pooler do Supabase em modo transaction, sem pool local
  (`NullPool`) e sem prepared statements.
- **Fuso horário**: "hoje" é sempre calculado em `America/Sao_Paulo`, independente do
  servidor.
- **Cron**: uma rota protegida por segredo (`/cron/keepalive`) é chamada diariamente pela
  Vercel para manter o banco ativo.

## Segurança

- **Multiusuário por casas**: cada cliente é uma casa com até 2 logins; gente nova só
  entra por link de convite. A API aceita tokens assinados pelo Supabase de quem é
  membro de uma casa. `ALLOWED_EMAIL` é o administrador (convida clientes novos).
- **Isolamento em duas travas**: a aplicação filtra toda consulta pela casa
  (`core/escopo.py`) e o banco aplica Row Level Security por casa para o papel
  `app_api` (`sql/011`). Testes em `tests/integracao/test_isolamento.py` e `test_rls.py`.
- A chave pública do frontend não tem acesso direto ao banco; todo acesso passa pela API.
- Credenciais exclusivamente em variáveis de ambiente; logs sem tokens nem valores de
  consultas (`hide_parameters`).
- CORS restrito ao domínio do frontend e cabeçalhos de segurança no site estático.
- Documentação interativa da API desabilitada em produção.

## Regras de negócio

- **Despesas**: uma linha por compromisso. Fixa (sem nº de parcelas) entra todo mês
  desde a 1ª cobrança; parcelada entra até completar as parcelas. Com data de
  cancelamento, deixa de entrar a partir do primeiro vencimento posterior.
- **Quem paga**: a conta tem um responsável no cadastro, e dá para trocar quem paga
  só num mês ou de um mês em diante (ex.: aluguel revezando). Os meses anteriores,
  inclusive os já pagos, não mudam.
- **Fatura do cartão**: compra até o dia de fechamento entra na fatura que fecha naquele
  mês; depois do fechamento, na seguinte. O mês considerado é o do vencimento (se o dia
  de vencimento for menor ou igual ao de fechamento, ele cai no mês seguinte).
- **Despesa paga no cartão** aparece dentro da fatura daquele cartão e é contada uma
  única vez no total do mês. Assinaturas viram despesas fixas com o cartão como forma
  de pagamento.
- **Comissões**: valor = implantação × percentual, em parcelas iguais (centavos na
  última). A 1ª parcela cai na data informada e as seguintes no dia 15 dos meses
  seguintes ([`services/regras_comissao.py`](backend/services/regras_comissao.py)).
  Uma parcela recebida pode gerar uma receita do tipo Comissão sem ser contada duas vezes.
- **Anotações**: somam no saldo apenas quando marcadas para isso e com data e valor.
  Vencidas e não concluídas continuam aparecendo no mês atual.
- **Metas**: o valor do mês é calculado pela regra da meta sobre a sobra (receitas −
  despesas) ou sobre as receitas. Valores guardados ficam registrados à parte e não
  entram como despesa.

## Estrutura

```
backend/
  main.py            app FastAPI, CORS e registro das rotas
  core/              configuração, conexão, autenticação (JWT) e erros
  routers/           endpoints REST
  schemas/           validação de entrada/saída (Pydantic)
  services/          regras de negócio (funções puras onde possível)
  repositories/      modelos ORM e consultas (SQLAlchemy)
  scripts/           migrações, backup e importação de planilhas .xlsx
  sql/               migrações (001 a 012)
  tests/             pytest
frontend/src/
  pages/             telas
  components/        layout, formulários e componentes de UI
  contexts/          autenticação e dados compartilhados
  lib/               cliente da API e formatação pt-BR
```

Principais endpoints (todos autenticados, exceto `/health`):
`GET /dashboard`, `GET /projecao`, `GET /periodo`, `GET /opcoes`, `GET /metas/painel`, CRUD em
`/despesas`, `/receitas`, `/comissoes`, `/cartoes`, `/gastos-cartao`, `/anotacoes` e
`/metas`, `/responsaveis`, `/conferencias` e `/categorias`.

## Execução local

Requisitos: Python 3.12+, Node.js 20+ e um projeto Supabase com as migrações de
[`backend/sql`](backend/sql) aplicadas em ordem.

```bash
# backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn main:app --reload

# frontend
cd frontend
cp .env.example .env
npm install
npm run dev
```

Variáveis do backend: `DATABASE_URL`, `DATABASE_URL_APP`, `DATABASE_URL_SISTEMA`, `SUPABASE_URL`, `ALLOWED_EMAIL`, `FRONTEND_URL`,
`CRON_SECRET`. Do frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`,
`VITE_API_URL`.

Testes (os de `tests/integracao` sobem um PostgreSQL embutido via `pgserver`):

```bash
cd backend && pytest
```

Migrações e backup (dentro de `backend`, usando o `DATABASE_URL` do `.env` ou `--url`):

```bash
python -m scripts.migrar --status            # aplicadas e pendentes
python -m scripts.migrar                     # aplica as pendentes (pede confirmação)
python -m scripts.backup salvar              # dados em CSV na pasta backups/
python -m scripts.backup restaurar backups/AAAA-MM-DD_HHMMSS --url URL_DE_TESTES
```

## Autor

Desenvolvido por **Antony** — [github.com/antonymendess](https://github.com/antonymendess)
