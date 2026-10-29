# Controle Financeiro

App web para organizar as finanças da casa: contas fixas e parceladas, faturas de cartão,
salários, comissões, metas de economia e uma previsão de quanto vai sobrar no fim do mês.
Funciona no celular e pode ser instalado como aplicativo (PWA).

**Demo:** <https://financas-app-frontend.vercel.app>

| Login | Senha |
|-------|-------|
| `demo@exemplo.com` | `123456` |

Os dados da demo são fictícios e voltam ao estado original todo dia. Pode mexer à vontade.

## Duas versões

Este repositório é a versão pública do projeto, feita para portfólio. O app que eu uso de
verdade com a minha família roda à parte, num repositório privado, com outro banco de dados e
outro endereço, porque guarda nossos dados financeiros reais.

O código é o mesmo. O que muda é o ambiente:

|               | Versão pessoal                     | Esta demo                                  |
|---------------|------------------------------------|--------------------------------------------|
| Repositório   | privado                            | público                                    |
| Banco         | projeto Supabase próprio           | outro projeto Supabase, só com dados fictícios |
| Cadastro      | só por convite                     | fechado, entra só o login de demonstração  |
| Dados         | reais                              | recriados todo dia                         |

As duas ficam no ar o tempo todo. Uma rotina agendada na Vercel chama a API uma vez por dia
para o Supabase não pausar o banco por inatividade e, na demo, aproveita para recriar os
dados fictícios.

## Por que eu fiz

Eu controlava tudo numa planilha do Excel. Funcionava, mas toda vez que entrava uma compra
parcelada no cartão ou uma comissão dividida em vários meses, eu tinha que mexer em fórmula e
conferir mês a mês se estava certo. E a pergunta que eu mais queria responder, "quanto vai
sobrar no fim do mês?", dava trabalho de calcular.

Resolvi transformar a planilha num app de verdade, que eu uso no dia a dia com a minha
família. Foi também a forma que encontrei de praticar back-end com Python num projeto real,
com regra de negócio de verdade, autenticação, banco em produção e testes.

## O que dá para fazer

- **Início:** saldo previsto do mês, contas a pagar com marcação de pago, gráfico de
  receitas × despesas dos próximos 12 meses e gastos por categoria. Dá para filtrar por pessoa
  e ver vários meses somados.
- **Despesas:** contas fixas (aluguel, internet) ou parceladas. Uma conta pode ser cancelada a
  partir de uma data, e o app mostra quanto ainda falta pagar das parceladas.
- **Quem paga:** cada conta tem um responsável, e dá para trocar quem paga só num mês ou de um
  mês em diante (ex.: aluguel revezando entre o casal).
- **Cartões:** cada compra cai na fatura certa conforme o dia de fechamento e de vencimento
  do cartão. Compras parceladas aparecem em cada fatura até terminar.
- **Receitas:** salários (todo mês) e entradas pontuais.
- **Comissões:** comissões parceladas com controle do que já foi recebido, e um funil de
  negociações que vira comissão quando fecha.
- **Anotações:** lembretes e dívidas informais ("pagar João dia 20 R$ 50"). O app entende a
  data e o valor do texto e pode somar no saldo do mês.
- **Metas (cofrinho):** quanto quero juntar e até quando. Mostra o progresso, o ritmo médio e
  quanto guardar por mês para chegar na data.
- **Conferência com o banco:** informo o saldo real da conta e o app calcula quanto deve
  sobrar no fim do mês a partir dele.
- **Pessoas da casa:** cada lançamento pode ser de uma pessoa ou do "Conjunto". As contas
  conjuntas são divididas proporcionalmente à renda de cada um.
- **Simulador:** orçamento, juros compostos e quanto aplicar por mês para chegar numa meta,
  sem mexer nos dados reais.

## Como usar a demo

1. Entre com o login e a senha acima.
2. No **Início**, troque o mês no topo para ver a previsão dos próximos meses. Toque no
   círculo ao lado de uma conta para marcar como paga.
3. Em **Despesas**, cadastre uma conta parcelada e veja ela aparecer nos meses seguintes.
4. Em **Cartões**, lance uma compra em 3x e veja em qual fatura cada parcela cai.
5. Em **Metas**, guarde um valor na "Viagem de férias" e veja o progresso mudar.
6. No **Simulador**, teste quanto um valor rende com juros compostos.

No celular, Cartões, Metas e Simulador ficam no menu **Mais**. Para instalar como app, use
"Adicionar à tela inicial" no navegador.

## Tecnologias

| Parte     | O que usei                                               |
|-----------|----------------------------------------------------------|
| Back-end  | Python, FastAPI, SQLAlchemy 2, Pydantic 2                |
| Front-end | React, Vite, Tailwind CSS, Recharts, React Router        |
| Banco     | PostgreSQL no Supabase, com migrações SQL versionadas    |
| Login     | Supabase Auth, com o token validado na API               |
| Deploy    | Vercel (site estático + API como função serverless)      |
| Testes    | pytest, com PostgreSQL embutido nos testes de integração |

## Como funciona por dentro

### Organização do back-end

```
routers/       recebem a requisição HTTP e devolvem a resposta
services/      regras de negócio (cálculos de fatura, parcelas, projeção do mês)
repositories/  modelos do banco e consultas
schemas/       validação dos dados que entram e saem (Pydantic)
core/          configuração, conexão com o banco e autenticação
```

O cálculo do mês fica em [`services/projecao.py`](backend/services/projecao.py). Os dados são
carregados com poucas consultas e o cálculo é feito por funções puras, sem acessar o banco.
Isso deixa a lógica fácil de testar e evita uma consulta para cada mês.

### Login

1. A tela de login manda e-mail e senha direto para o Supabase Auth, que confere a senha e
   devolve um token JWT.
2. O front guarda o token e envia em toda chamada à API no cabeçalho
   `Authorization: Bearer <token>`.
3. A API confere a assinatura do token com a chave pública do Supabase, a validade e o
   projeto de origem ([`core/auth.py`](backend/core/auth.py)). Se algo não bate, responde 401.
4. Com o usuário identificado, a API descobre a qual casa ele pertence e só trabalha com os
   dados dela.

A API nunca vê a senha, e o front nunca acessa o banco direto: tudo passa pela API.

### Separação dos dados entre usuários

Cada família é uma "casa", e o isolamento tem duas travas:

- **Na aplicação:** toda consulta recebe automaticamente o filtro da casa do usuário logado
  ([`core/escopo.py`](backend/core/escopo.py)).
- **No banco:** Row Level Security do PostgreSQL. A API conecta com um usuário do banco que só
  enxerga as linhas da casa informada ([`sql/011_rls_por_casa.sql`](backend/sql/011_rls_por_casa.sql)).
  Mesmo que o código esqueça um filtro, o banco não devolve dados de outra casa.

As duas travas têm testes próprios em `tests/integracao/test_isolamento.py` e `test_rls.py`.

### Outros cuidados

- Credenciais só em variáveis de ambiente.
- CORS liberado só para o domínio do front.
- Documentação automática da API desligada em produção.
- Logs sem tokens e sem valores das consultas.
- "Hoje" sempre calculado no fuso de São Paulo, independente do servidor.
- Conexão pensada para serverless: usa o pooler do Supabase e não mantém pool local.

### Regras de negócio que deram mais trabalho

- **Fatura do cartão:** compra até o dia de fechamento entra na fatura daquele mês; depois do
  fechamento, na seguinte. Se o vencimento é antes do fechamento, a fatura vence no mês
  seguinte.
- **Conta paga no cartão** (ex.: streaming) aparece dentro da fatura e é contada uma vez só.
- **Comissões:** valor da venda × percentual, dividido em parcelas iguais, com os centavos
  na última. A primeira cai na data informada e as outras no dia 15 dos meses seguintes.
- **Quem paga:** trocar o responsável de uma conta não altera os meses que já passaram.

## Rodando na sua máquina

Precisa de Python 3.12+, Node.js 20+ e um projeto no Supabase.

```bash
# back-end
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # preencha com os dados do seu Supabase
python -m scripts.migrar      # cria as tabelas
uvicorn main:app --reload

# front-end (outro terminal)
cd frontend
cp .env.example .env
npm install
npm run dev
```

Para ter dados de exemplo, crie um usuário em Authentication → Users no Supabase, coloque o
e-mail dele em `DEMO_EMAIL` no `.env` e rode:

```bash
python -m scripts.demo
```

### Testes

```bash
cd backend
pytest
```

Os testes de integração sobem um PostgreSQL embutido (pacote `pgserver`), sem precisar de
Docker, e aplicam as migrações do zero.

## Estrutura

```
backend/
  main.py        app FastAPI e registro das rotas
  core/          configuração, conexão, autenticação e isolamento por casa
  routers/       endpoints
  schemas/       validação (Pydantic)
  services/      regras de negócio
  repositories/  modelos e consultas (SQLAlchemy)
  scripts/       migrações, backup, dados da demo e importação de planilhas
  sql/           migrações do banco
  tests/         testes
frontend/src/
  pages/         telas
  components/    componentes de interface
  contexts/      sessão do usuário e dados compartilhados
  lib/           cliente da API e formatação
```

## Autor

Antony Mendes, estudante de back-end com Python.
[github.com/antonymendess](https://github.com/antonymendess)
