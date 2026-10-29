// Tela inicial, de cima para baixo: saldo do mês, quanto sobra para cada pessoa,
// contas do mês separadas por quem paga e, depois, anotações, gráficos e cartões.
// Tudo é clicável e leva à tela com o detalhe.
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bar, CartesianGrid, Cell, ComposedChart, Legend, Line, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import {
  AlertTriangle, ArrowDownCircle, ArrowUpCircle, CheckCircle2, ChevronDown, ChevronRight, CreditCard, Receipt,
  Landmark, PiggyBank, TrendingDown, TrendingUp, Users, Wallet,
} from 'lucide-react'
import { api } from '../lib/api'
import { dataCurta, diasAte, dinheiro, mesAno, mesCurto, numeroCurto } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import SeletorMes, { mesAtual } from '../components/SeletorMes'
import AnotacaoRapida from '../components/AnotacaoRapida'
import ItemAnotacao from '../components/ItemAnotacao'
import FormAnotacao from '../components/FormAnotacao'
import { MarcaPessoa, useResponsaveis } from '../components/CampoResponsavel'
import VisaoPeriodo from '../components/VisaoPeriodo'
import { CartaoConferencia, FormConferencia } from '../components/Conferencia'
import { coresDasMetas } from './Metas'
import { Abas, BarraProgresso, Botao, Cartao, CaixaPago, Carregando, MensagemErro, Modal, Opcoes, Vazio } from '../components/ui'

// Paleta categórica validada para fundo escuro, sempre na mesma ordem
const CORES_CATEGORIAS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
const CORES = { receitas: '#199e70', despesas: '#d95926', saldo: '#3987e5', grade: 'var(--color-borda)', eixo: 'var(--color-apagado)' }
// Barra "para onde vai a renda" de cada pessoa
const CORES_RENDA = { proprias: '#d95926', casa: 'var(--color-apagado)', sobra: '#3ecf8e' }
const FILTRO_PESSOA = 'inicio-filtro-pessoa'

// Pessoa escolhida no filtro fica lembrada neste aparelho
function lerFiltroPessoa() {
  try {
    return localStorage.getItem(FILTRO_PESSOA) ?? ''
  } catch {
    return ''
  }
}

export default function Dashboard() {
  const [mes, setMes] = useState(mesAtual)
  const [modo, setModo] = useState('mes') // 'mes' | 'periodo'
  const [pessoaEscolhida, setPessoa] = useState(lerFiltroPessoa) // '' | id | 'conjunto'
  const { versao, dadosMudaram, avisar } = useDados()
  const responsaveis = useResponsaveis()
  const [editandoAnotacao, setEditandoAnotacao] = useState(null)
  const [conferindo, setConferindo] = useState(false)
  // Pessoa excluída (ou ainda carregando a lista): volta para "Todos"
  const pessoa = responsaveis.ativo && (pessoaEscolhida === 'conjunto' || responsaveis.lista.some((x) => String(x.id) === pessoaEscolhida))
    ? pessoaEscolhida
    : ''
  const filtro = pessoa ? `&responsavel=${pessoa}` : ''

  const resumo = useCarregar(() => api.get(`/dashboard?ano=${mes.ano}&mes=${mes.mes}${filtro}`), [mes, filtro, versao], `/dashboard?ano=${mes.ano}&mes=${mes.mes}${filtro}`)
  const projecao = useCarregar(() => api.get(`/projecao?meses=11&ano=${mes.ano}&mes=${mes.mes}${filtro}`), [mes, filtro, versao], `/projecao?meses=11&ano=${mes.ano}&mes=${mes.mes}${filtro}`)
  const anotacoes = useCarregar(() => api.get('/anotacoes?status=pendentes'), [versao], '/anotacoes?status=pendentes')
  const metas = useCarregar(() => api.get('/metas/painel'), [versao], '/metas/painel')

  const escolherPessoa = (valor) => {
    setPessoa(valor)
    try {
      localStorage.setItem(FILTRO_PESSOA, valor)
    } catch {
      /* sem armazenamento: vale só nesta visita */
    }
  }
  const abrirMes = (m) => {
    setMes(m)
    setModo('mes')
  }

  // Marca conta/fatura como paga na hora e confirma com o servidor
  const marcarPago = async (v, pago) => {
    const caminho = v.tipo === 'fatura' ? `/cartoes/${v.id}/pagamento` : `/despesas/${v.id}/pagamento`
    resumo.setDados((d) => ({
      ...d,
      vencimentos: d.vencimentos.map((x) => (x.tipo === v.tipo && x.id === v.id ? { ...x, pago, vencido: false } : x)),
    }))
    try {
      await api.patch(caminho, { ano: mes.ano, mes: mes.mes, pago })
      avisar(pago ? 'Marcado como pago' : 'Pagamento desmarcado')
    } catch (e) {
      avisar(e.message)
    }
    dadosMudaram()
  }

  const r = resumo.dados
  const contas = r ? r.vencimentos.filter((v) => v.tipo !== 'anotacao') : []
  const contasPagas = contas.filter((v) => v.pago).length

  return (
    <div className="space-y-6 lg:space-y-8">
      <div className="space-y-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <h1 className="hidden text-[28px] font-semibold tracking-tight lg:block">Visão geral</h1>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center lg:justify-end">
            <div className="sm:w-56">
              <Abas abas={[{ valor: 'mes', rotulo: 'Mês' }, { valor: 'periodo', rotulo: 'Período' }]} ativa={modo} onChange={setModo} />
            </div>
            {modo === 'mes' && (
              <div className="sm:w-80">
                <SeletorMes valor={mes} onChange={setMes} />
              </div>
            )}
          </div>
        </div>
        {responsaveis.ativo && (
          <Opcoes
            opcoes={[
              { valor: '', rotulo: 'Todos' },
              ...responsaveis.lista.map((x) => ({ valor: String(x.id), rotulo: <MarcaPessoa id={x.id} /> })),
              { valor: 'conjunto', rotulo: <MarcaPessoa id={null} /> },
            ]}
            valor={pessoa}
            onChange={escolherPessoa}
          />
        )}
      </div>

      {modo === 'periodo' && <VisaoPeriodo pessoa={pessoa} onEscolherMes={abrirMes} />}

      {modo === 'mes' && resumo.erro && <MensagemErro mensagem={resumo.erro} tentarNovamente={resumo.recarregar} />}
      {modo === 'mes' && resumo.carregando && !r && <Carregando />}

      {modo === 'mes' && r && (
        <div className={`space-y-4 transition-opacity lg:space-y-6 ${resumo.carregando ? 'opacity-70' : ''}`}>
          <Indicadores r={r} />

          {/* Conferência com o banco: visão da casa toda (sem filtro de pessoa) */}
          {!pessoa && (r.conferencia || ehMesAtual(r)) && (
            <CartaoConferencia conferencia={r.conferencia} onConferir={() => setConferindo(true)} />
          )}

          {/* Nenhuma receita mensal (salário) no mês: convite para cadastrar */}
          {!pessoa && !r.receitas.some((x) => x.recorrente) && (
            <Convite para="/receitas?nova=salario" Icone={ArrowUpCircle} cor="text-positivo" titulo="Cadastre seu salário">
              Ele entra todo mês e deixa o saldo previsto certo.
            </Convite>
          )}

          {r.avisos.map((aviso) => (
            <Link key={aviso} to="/cartoes" className="flex items-start gap-2 rounded-xl border border-alerta/40 bg-alerta/10 p-3 text-sm">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-alerta" aria-hidden /> {aviso}
            </Link>
          ))}

          {pessoa ? null : r.por_responsavel.length > 0 ? (
            <Cartao titulo="Quanto sobra para cada um" acao={<Link to="/pessoas" className="text-sm text-saldo">pessoas</Link>}>
              <PorPessoa itens={r.por_responsavel} receitas={r.receitas} noMesAtual={ehMesAtual(r)} />
            </Cartao>
          ) : (
            <Convite para="/pessoas" Icone={Users} cor="text-saldo" titulo="Separe o dinheiro por pessoa">
              Cadastre quem divide as finanças e veja quanto cada um recebe, gasta e sobra.
            </Convite>
          )}

          <Cartao
            titulo="Contas do mês"
            acao={contas.length > 0 && <span className="text-sm text-suave">{contasPagas} de {contas.length} pagas</span>}
          >
            <ContasDoMes contas={contas} onPagar={marcarPago} />
          </Cartao>

          <div className="grid gap-4 lg:grid-cols-3 lg:gap-6">
            {/* Celular: metas e anotações logo depois das contas. Computador: coluna da direita */}
            <div className="space-y-4 lg:col-start-3 lg:row-start-1 lg:space-y-6">
            {metas.dados?.metas.length > 0 && <ResumoMetas p={metas.dados} />}
            <Cartao
              titulo="Anotações"
              acao={<Link to="/anotacoes" className="text-sm text-saldo">ver todas</Link>}
            >
              <AnotacaoRapida />
              {anotacoes.erro && <MensagemErro mensagem={anotacoes.erro} />}
              <ul className="mt-3 space-y-0.5">
                {(anotacoes.dados ?? []).slice(0, 6).map((a) => (
                  <ItemAnotacao key={a.id} anotacao={a} onEditar={setEditandoAnotacao} compacto />
                ))}
              </ul>
              {anotacoes.dados?.length === 0 && <p className="pt-4 text-center text-sm text-apagado">Nada pendente.</p>}
              {anotacoes.dados?.length > 6 && (
                <Link to="/anotacoes" className="mt-2 block text-center text-sm text-saldo">
                  + {anotacoes.dados.length - 6} anotações
                </Link>
              )}
            </Cartao>
            </div>

            <Cartao titulo={`Receitas × despesas — próximos 12 meses${pessoa ? ` · ${responsaveis.nome(pessoa === 'conjunto' ? null : Number(pessoa))}` : ''}`} className="lg:col-span-2 lg:col-start-1 lg:row-start-1">
              {projecao.erro && <MensagemErro mensagem={projecao.erro} />}
              {projecao.dados ? <GraficoProjecao dados={projecao.dados} onEscolherMes={setMes} /> : <Carregando />}
            </Cartao>

            <Cartao titulo="Despesas por categoria" className="lg:col-start-3 lg:row-start-2">
              <GraficoCategorias itens={r.por_categoria} total={r.total_despesas} />
            </Cartao>

            <Cartao
              titulo="Cartões"
              acao={<Link to="/cartoes" className="text-sm text-saldo">detalhes</Link>}
              className="lg:col-span-2 lg:col-start-1 lg:row-start-2"
            >
              <BlocoCartoes faturas={r.faturas} />
            </Cartao>
          </div>
        </div>
      )}

      <Modal aberto={conferindo && Boolean(r) && !pessoa} titulo="Conferir com o saldo do banco" onFechar={() => setConferindo(false)}>
        {conferindo && r && !pessoa && <FormConferencia r={r} onPagar={marcarPago} onFechar={() => setConferindo(false)} />}
      </Modal>
      <Modal aberto={editandoAnotacao !== null} titulo="Editar anotação" onFechar={() => setEditandoAnotacao(null)}>
        {editandoAnotacao && <FormAnotacao anotacao={editandoAnotacao} onSalvo={() => setEditandoAnotacao(null)} />}
      </Modal>
    </div>
  )
}

function Convite({ para, Icone, cor, titulo, children }) {
  return (
    <Link to={para} className="flex items-center gap-3 rounded-2xl border border-borda bg-painel p-5 transition hover:border-apagado/50">
      <Icone className={`size-6 shrink-0 ${cor}`} aria-hidden />
      <span className="flex-1">
        <span className="block font-medium">{titulo}</span>
        <span className="block text-sm text-suave">{children}</span>
      </span>
      <ChevronRight className="size-5 text-suave" aria-hidden />
    </Link>
  )
}

// ---------------------------------------------------------------- indicadores
function Indicadores({ r }) {
  const pessoa = r.pessoa && 'saldo_final' in r.pessoa ? r.pessoa : null
  const saldo = pessoa ? pessoa.saldo_final : r.saldo
  const semComissoes = pessoa ? pessoa.saldo_final_garantido : r.saldo - r.comissoes_a_receber
  const positivo = saldo >= 0
  const pctPago = r.total_despesas ? r.total_pago / r.total_despesas : 0
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:gap-4 xl:grid-cols-4">
      {/* Saldo em destaque */}
      <div className={`col-span-2 rounded-2xl border p-5 md:col-span-3 xl:col-span-2 xl:row-span-2 xl:p-6 ${positivo ? 'border-positivo/40 bg-positivo/5' : 'border-negativo/50 bg-negativo/5'}`}>
        <p className="flex items-center gap-1.5 text-sm text-suave">
          {positivo ? <TrendingUp className="size-4" aria-hidden /> : <TrendingDown className="size-4" aria-hidden />}
          {positivo ? 'Sobra prevista do mês' : 'Vai faltar no mês'}{pessoa ? ` · ${pessoa.nome}` : ''}
        </p>
        <p className={`mt-1 text-3xl font-bold ${positivo ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(saldo)}</p>
        {r.comissoes_a_receber > 0 && (
          <p className="text-xs text-alerta">sem as comissões ainda não recebidas: {dinheiro(semComissoes)}</p>
        )}
        <ContaDoMes r={r} pessoa={pessoa} saldo={saldo} />
        <PeloBanco r={r} pessoa={pessoa} prevista={saldo} />
      </div>

      <CardLink para="/despesas?status=a-pagar" rotulo="Falta pagar" valor={dinheiro(r.total_a_pagar)}>
        <div className="mt-2">
          <BarraProgresso atual={r.total_pago} total={r.total_despesas} cor="bg-positivo" />
          <p className="mt-1 text-xs text-apagado">{Math.round(pctPago * 100)}% já pago</p>
        </div>
      </CardLink>
      <CardLink para="/comissoes" rotulo="Comissões a receber" valor={dinheiro(r.comissoes_a_receber)} detalhe={r.comissoes_recebidas ? `${dinheiro(r.comissoes_recebidas)} já recebido` : null} Icone={Wallet} />
      <CardLink para="/cartoes" rotulo="Faturas de cartão" valor={dinheiro(r.total_faturas)} detalhe="já incluídas no que sai" Icone={CreditCard} />
      <CardLink para="/despesas" rotulo="Contas ativas" valor={r.contas_ativas} detalhe="no mês" Icone={Receipt} />
    </div>
  )
}

function CardLink({ para, rotulo, valor, detalhe, Icone, children }) {
  return (
    <Link to={para} className="group rounded-2xl border border-borda bg-painel p-5 transition hover:border-apagado/50">
      <p className="flex items-center justify-between gap-1 text-sm text-suave">
        <span className="flex items-center gap-1.5">{Icone && <Icone className="size-4" aria-hidden />}{rotulo}</span>
        <ChevronRight className="size-4 opacity-0 transition group-hover:opacity-100" aria-hidden />
      </p>
      <p className="mt-1 text-lg font-bold sm:text-xl">{valor}</p>
      {detalhe && <p className="text-xs text-apagado">{detalhe}</p>}
      {children}
    </Link>
  )
}

// ---------------------------------------------------------------- o que já entrou × o que vai entrar
const ehMesAtual = (r) => {
  const atual = mesAtual()
  return r.ano === atual.ano && r.mes === atual.mes
}

// Separa as receitas do mês: já entrou, vai entrar (certo, ex.: salário do dia 15)
// e comissões ainda não recebidas (previstas, podem atrasar)
function situacaoReceitas(receitas) {
  const soma = (lista) => lista.reduce((s, x) => s + x.valor, 0)
  const pendentes = receitas.filter((x) => !x.recebida)
  const certas = pendentes.filter((x) => x.origem !== 'comissao')
  const previstas = pendentes.filter((x) => x.origem === 'comissao')
  return {
    jaEntrou: soma(receitas.filter((x) => x.recebida)),
    certas,
    previstas,
    totalCertas: soma(certas),
    totalPrevistas: soma(previstas),
  }
}

function quando(dataIso) {
  const dias = diasAte(dataIso)
  if (dias === null) return ''
  if (dias <= 0) return 'hoje'
  return `dia ${Number(dataIso.slice(8))} (em ${dias} dia${dias > 1 ? 's' : ''})`
}

// A conta do saldo do topo, linha a linha: entra − contas (− parte da casa) = sobra prevista
function ContaDoMes({ r, pessoa, saldo }) {
  const { jaEntrou, certas, totalCertas, totalPrevistas } = situacaoReceitas(r.receitas)
  const detalheEntra = ehMesAtual(r) && (totalCertas || totalPrevistas)
    ? [
        `${dinheiro(jaEntrou)} já entrou`,
        totalCertas > 0 && `${dinheiro(totalCertas)} ainda vai cair${certas.length === 1 ? ` ${quando(certas[0].data)}` : ''}`,
        totalPrevistas > 0 && `${dinheiro(totalPrevistas)} de comissão prevista`,
      ].filter(Boolean).join(' · ')
    : null
  const detalheContas = r.total_despesas <= 0 ? null
    : r.total_a_pagar > 0.005 ? `${dinheiro(r.total_pago)} pago · ${dinheiro(r.total_a_pagar)} falta pagar`
      : 'tudo pago ✓'
  const parte = pessoa?.parte_conjunto ?? 0
  return (
    <div className="mt-3 space-y-1.5 rounded-xl bg-painel-2/60 p-3 text-sm">
      <LinhaConta rotulo="Entra no mês" valor={r.total_receitas} para="/receitas" detalhe={detalheEntra} />
      <LinhaConta
        rotulo={pessoa ? 'Contas próprias' : 'Contas do mês'}
        valor={-r.total_despesas}
        para={pessoa ? `/despesas?responsavel=${pessoa.responsavel_id}` : '/despesas'}
        detalhe={detalheContas}
      />
      {Math.abs(parte) > 0.005 && (
        <LinhaConta
          rotulo={parte > 0 ? 'Parte das contas da casa' : 'Parte do que sobrou no conjunto'}
          valor={-parte}
          mais
          para="/despesas?responsavel=conjunto"
          detalhe={`${Math.round(pessoa.proporcao * 100)}% da renda da casa`}
        />
      )}
      <p className="flex justify-between gap-2 border-t border-borda pt-2 font-medium">
        <span>= {saldo >= 0 ? 'Sobra prevista' : 'Vai faltar'}</span>
        <span className={saldo >= 0 ? 'text-positivo' : 'text-negativo'}>{dinheiro(saldo)}</span>
      </p>
    </div>
  )
}

function LinhaConta({ rotulo, valor, para, detalhe, mais }) {
  return (
    <Link to={para} className="-mx-1 block rounded-lg px-1 py-0.5 hover:bg-painel">
      <span className="flex justify-between gap-2">
        <span className="min-w-0 truncate text-suave">{valor < 0 ? '− ' : mais ? '+ ' : ''}{rotulo}</span>
        <span className="whitespace-nowrap font-semibold">{dinheiro(Math.abs(valor))}</span>
      </span>
      {detalhe && <span className="block text-xs text-apagado">{detalhe}</span>}
    </Link>
  )
}

// Com conferência: a sobra pelo saldo real do banco e por que ela é diferente da prevista
function PeloBanco({ r, pessoa, prevista }) {
  const c = r.conferencia
  if (!c) return null
  const dela = pessoa ? c.por_pessoa.find((p) => p.responsavel_id === pessoa.responsavel_id) : null
  if (pessoa && !dela) return null
  const banco = dela ? dela.sobra : c.sobra
  const diferenca = banco - prevista
  return (
    <div className="mt-3 rounded-xl border border-borda p-3 text-sm">
      <p className="flex justify-between gap-2">
        <span className="flex items-center gap-1.5 text-suave"><Landmark className="size-4" aria-hidden /> Pelo saldo do banco</span>
        <span className={`font-semibold ${banco >= 0 ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(banco)}</span>
      </p>
      <p className="mt-1 text-xs text-apagado">
        {Math.abs(diferenca) < 1
          ? 'Bate com o previsto ✓'
          : diferenca > 0
            ? `${dinheiro(diferenca)} a mais que o previsto: é o dinheiro que já estava na conta antes deste mês (sobra do mês passado), menos os gastos não anotados.`
            : `${dinheiro(-diferenca)} a menos que o previsto: são gastos que não foram anotados no app (ou o mês passado terminou no negativo).`}
      </p>
    </div>
  )
}

// Linhas de "recebe" num extrato: no mês atual separa o que já entrou do que vai entrar
function LinhasRecebe({ receitas, noMesAtual, rotulo = 'Recebe' }) {
  const total = receitas.reduce((s, x) => s + x.valor, 0)
  const { jaEntrou, certas, totalCertas, totalPrevistas } = situacaoReceitas(receitas)
  if (!noMesAtual || (!totalCertas && !totalPrevistas)) {
    return <LinhaExtrato rotulo={rotulo} valor={total} para="/receitas" />
  }
  return (
    <>
      <LinhaExtrato rotulo="Já entrou" valor={jaEntrou} para="/receitas" />
      {certas.length === 1 ? (
        <LinhaExtrato rotulo={`Cai ${quando(certas[0].data)}`} valor={totalCertas} para="/receitas" aEntrar />
      ) : totalCertas > 0 ? (
        <LinhaExtrato rotulo="Ainda vai entrar" valor={totalCertas} para="/receitas" aEntrar />
      ) : null}
      {totalPrevistas > 0 && (
        <LinhaExtrato rotulo="Comissão a receber (prevista)" valor={totalPrevistas} para="/comissoes" previsto />
      )}
    </>
  )
}

// ---------------------------------------------------------------- metas (resumo)
// Só informativo: mostra o quanto já foi guardado em cada meta
function ResumoMetas({ p }) {
  const cores = coresDasMetas(p.metas)
  const ativas = p.metas.filter((m) => m.ativa).slice(0, 3)
  return (
    <Cartao titulo="Metas" acao={<Link to="/metas" className="text-sm text-saldo">ver metas</Link>}>
      <p className="flex items-center gap-2 text-sm text-suave">
        <PiggyBank className="size-4 text-saldo" aria-hidden /> Guardado: <span className="font-semibold text-texto">{dinheiro(p.guardado_total)}</span>
        {p.guardado_no_mes > 0 && <span className="text-positivo">+{dinheiro(p.guardado_no_mes)} este mês</span>}
      </p>
      <ul className="mt-3 space-y-3">
        {ativas.map((m) => {
          const pct = m.progresso !== null ? Math.round(m.progresso * 100) : null
          return (
            <li key={m.id}>
              <Link to="/metas" className="block">
                <div className="flex justify-between gap-2 text-sm">
                  <span className="truncate">{m.nome}</span>
                  <span className="text-suave">{pct !== null ? `${pct}%` : dinheiro(m.guardado)}</span>
                </div>
                {pct !== null && (
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-borda">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: cores[m.id] }} />
                  </div>
                )}
              </Link>
            </li>
          )
        })}
      </ul>
    </Cartao>
  )
}

// ---------------------------------------------------------------- por pessoa
// Extrato de cada pessoa: recebe − contas dela − parte do Conjunto = sobra.
// O Conjunto (contas da casa) é dividido proporcionalmente à renda de cada um.
function PorPessoa({ itens, receitas, noMesAtual }) {
  const pessoas = itens.filter((p) => p.responsavel_id !== null)
  const conjunto = itens.find((p) => p.responsavel_id === null)
  const total = pessoas.length + (conjunto ? 1 : 0)
  return (
    <>
      <div className={`grid items-start gap-3 sm:grid-cols-2 ${total >= 3 ? 'xl:grid-cols-3' : ''}`}>
        {pessoas.map((p) => (
          <ExtratoPessoa
            key={p.responsavel_id}
            p={p}
            conjunto={conjunto}
            receitas={receitas.filter((x) => x.responsavel_id === p.responsavel_id)}
            noMesAtual={noMesAtual}
          />
        ))}
        {conjunto && <CartaoConjunto conjunto={conjunto} pessoas={pessoas} />}
      </div>
      <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-apagado">
        <Legenda cor={CORES_RENDA.proprias}>contas próprias</Legenda>
        {conjunto && <Legenda cor={CORES_RENDA.casa}>parte do conjunto</Legenda>}
        <Legenda cor={CORES_RENDA.sobra}>sobra</Legenda>
      </p>
    </>
  )
}

function Legenda({ cor, children }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-2.5 rounded-sm" style={{ background: cor }} aria-hidden />
      {children}
    </span>
  )
}

function ExtratoPessoa({ p, conjunto, receitas, noMesAtual }) {
  const positivo = p.saldo_final >= 0
  const faltaPagar = p.despesas - p.pago
  // Conjunto com receitas sem dono: a "parte" mistura contas e receitas
  const rotuloParte = conjunto?.receitas > 0 ? 'Parte do conjunto' : 'Parte das contas da casa'
  return (
    <div className="flex flex-col rounded-xl border border-borda bg-painel-2 p-4">
      <div className="flex items-center justify-between gap-2">
        <MarcaPessoa id={p.responsavel_id} className="font-semibold" />
        {conjunto && <span className="text-xs text-apagado">{Math.round(p.proporcao * 100)}% da renda da casa</span>}
      </div>

      <div className="mt-3 space-y-1 text-sm">
        <LinhasRecebe receitas={receitas} noMesAtual={noMesAtual} />
        <LinhaExtrato rotulo="Contas próprias" valor={-p.despesas} para={`/despesas?responsavel=${p.responsavel_id}`} />
        {conjunto && <LinhaExtrato rotulo={rotuloParte} valor={-p.parte_conjunto} para="/despesas?responsavel=conjunto" />}
      </div>
      <div className="mt-2 flex items-baseline justify-between border-t border-borda pt-2">
        <span className="text-sm font-medium">{positivo ? 'Sobra' : 'Falta'}</span>
        <span className={`text-2xl font-bold ${positivo ? 'text-positivo' : 'text-negativo'}`}>{dinheiro(p.saldo_final)}</span>
      </div>
      {p.receitas_previstas > 0 && (
        <p className="mt-1 flex justify-between gap-2 text-xs text-suave">
          <span>Sem a comissão a receber</span>
          <span className="font-semibold text-texto">{dinheiro(p.saldo_final_garantido)}</span>
        </p>
      )}

      <BarraRenda p={p} />

      <p className="pt-3 text-xs">
        {faltaPagar > 0.005 ? (
          <span className="text-suave">Ainda falta pagar <span className="font-semibold text-texto">{dinheiro(faltaPagar)}</span> das contas próprias</span>
        ) : p.despesas > 0 ? (
          <span className="flex items-center gap-1 text-positivo"><CheckCircle2 className="size-3.5" aria-hidden /> Contas próprias pagas</span>
        ) : (
          <span className="text-apagado">Sem contas próprias no mês</span>
        )}
      </p>
    </div>
  )
}

// Para onde vai a renda: contas próprias | parte do conjunto | sobra
function BarraRenda({ p }) {
  const base = Math.max(p.receitas, p.despesas + Math.max(p.parte_conjunto, 0), 0.01)
  const fatias = [
    { cor: CORES_RENDA.proprias, valor: p.despesas, nome: 'Contas próprias' },
    { cor: CORES_RENDA.casa, valor: Math.max(p.parte_conjunto, 0), nome: 'Parte do conjunto' },
    { cor: CORES_RENDA.sobra, valor: Math.max(p.saldo_final, 0), nome: 'Sobra' },
  ].filter((f) => f.valor > 0)
  return (
    <div className="mt-3 flex h-2.5 w-full overflow-hidden rounded-full bg-borda" role="img" aria-label={fatias.map((f) => `${f.nome}: ${dinheiro(f.valor)}`).join(', ')}>
      {fatias.map((f) => (
        <div key={f.nome} title={`${f.nome}: ${dinheiro(f.valor)}`} style={{ width: `${(f.valor / base) * 100}%`, background: f.cor }} />
      ))}
    </div>
  )
}

function LinhaExtrato({ rotulo, valor, para, previsto, aEntrar }) {
  const cor = previsto ? 'text-alerta' : aEntrar ? 'text-saldo' : valor > 0 ? 'text-positivo' : valor < 0 ? 'text-texto' : 'text-apagado'
  return (
    <Link to={para} className="-mx-1 flex justify-between gap-2 rounded-lg px-1 py-0.5 hover:bg-painel">
      <span className={`min-w-0 truncate ${previsto ? 'text-alerta' : aEntrar ? 'text-saldo' : 'text-suave'}`}>{rotulo}</span>
      <span className={`whitespace-nowrap ${cor}`}>{valor > 0 ? '+ ' : valor < 0 ? '− ' : ''}{dinheiro(Math.abs(valor))}</span>
    </Link>
  )
}

function CartaoConjunto({ conjunto, pessoas }) {
  const { dadosMudaram, avisar } = useDados()
  const [atribuindo, setAtribuindo] = useState(null)
  const falta = conjunto.despesas - conjunto.pago

  const assumirComissoes = async (pessoa) => {
    setAtribuindo(pessoa.responsavel_id)
    try {
      const r = await api.post(`/responsaveis/${pessoa.responsavel_id}/assumir-comissoes`)
      avisar(`${r.comissoes} comissões e ${r.receitas} receitas passaram para ${pessoa.nome}`)
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
    }
    setAtribuindo(null)
  }

  return (
    <div className="flex flex-col rounded-xl border border-dashed border-borda p-4">
      <MarcaPessoa id={null} className="font-semibold" />
      <p className="mt-3 text-sm text-suave">Contas da casa</p>
      <p className="text-2xl font-bold">{dinheiro(conjunto.despesas)}</p>
      {conjunto.despesas > 0 && (
        <>
          <p className="text-xs text-apagado">{falta > 0.005 ? `${dinheiro(falta)} ainda a pagar` : 'Tudo pago'}</p>
          <ul className="mt-3 space-y-1 text-sm">
            {pessoas.map((p) => (
              <li key={p.responsavel_id} className="flex justify-between gap-2">
                <MarcaPessoa id={p.responsavel_id} className="text-suave" />
                <span>{dinheiro(conjunto.despesas * p.proporcao)} <span className="text-xs text-apagado">({Math.round(p.proporcao * 100)}%)</span></span>
              </li>
            ))}
          </ul>
        </>
      )}

      {conjunto.receitas > 0 && (
        <div className="mt-3 rounded-lg border border-alerta/40 bg-alerta/10 p-3 text-xs">
          <p className="flex gap-1.5">
            <AlertTriangle className="size-4 shrink-0 text-alerta" aria-hidden />
            <span>
              <strong>{dinheiro(conjunto.receitas)}</strong> em receitas sem pessoa estão sendo divididas entre vocês.{' '}
              <Link to="/receitas" className="text-saldo">Definir de quem é</Link>
            </span>
          </p>
          {conjunto.receitas_comissao > 0 && (
            <div className="mt-2">
              <p className="mb-1.5 text-suave">{dinheiro(conjunto.receitas_comissao)} são de comissões. As comissões são de:</p>
              <div className="flex flex-wrap gap-2">
                {pessoas.map((p) => (
                  <Botao key={p.responsavel_id} variante="secundario" className="min-h-9 px-3 text-sm" carregando={atribuindo === p.responsavel_id} onClick={() => assumirComissoes(p)}>
                    <MarcaPessoa id={p.responsavel_id} />
                  </Botao>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- contas do mês
// Separadas por quem paga (uma coluna por pessoa). Pendentes em cima, pagas recolhidas.
function ContasDoMes({ contas, onPagar }) {
  const responsaveis = useResponsaveis()
  if (!contas.length) return <Vazio>Nenhuma conta neste mês.</Vazio>
  if (!responsaveis.ativo) return <GrupoContas itens={contas} onPagar={onPagar} />

  const grupos = [...responsaveis.lista.map((p) => p.id), null]
    .map((id) => ({ id, itens: contas.filter((v) => (v.responsavel_id ?? null) === id) }))
    .filter((g) => g.itens.length)
  const colunas = { 1: '', 2: 'lg:grid-cols-2', 3: 'lg:grid-cols-3' }[Math.min(grupos.length, 3)]
  return (
    <div className={`grid gap-4 ${colunas}`}>
      {grupos.map((g) => <GrupoContas key={g.id ?? 'conjunto'} pessoa={g.id} comCabecalho itens={g.itens} onPagar={onPagar} />)}
    </div>
  )
}

function GrupoContas({ pessoa, comCabecalho, itens, onPagar }) {
  const [verPagas, setVerPagas] = useState(false)
  const pendentes = itens.filter((v) => !v.pago)
    .sort((a, b) => Number(b.vencido) - Number(a.vencido) || (a.data ?? '9').localeCompare(b.data ?? '9'))
  const pagas = itens.filter((v) => v.pago)
  const total = itens.reduce((s, v) => s + (v.valor ?? 0), 0)
  const pago = pagas.reduce((s, v) => s + (v.valor ?? 0), 0)

  return (
    <div className={comCabecalho ? 'rounded-xl bg-painel-2/50 p-3' : ''}>
      {comCabecalho && (
        <div className="mb-2">
          <div className="flex items-center justify-between gap-2">
            <MarcaPessoa id={pessoa} className="font-semibold" />
            <span className="text-sm font-semibold">{dinheiro(total)}</span>
          </div>
          <div className="mt-1.5"><BarraProgresso atual={pago} total={total} cor="bg-positivo" /></div>
          <p className="mt-1 text-xs text-apagado">
            {pendentes.length ? `${dinheiro(total - pago)} a pagar · ${pagas.length} de ${itens.length} pagas` : 'Tudo pago'}
          </p>
        </div>
      )}
      {pendentes.length > 0 && (
        <ul className={comCabecalho ? '' : 'grid grid-cols-1 gap-x-6 md:grid-cols-2'}>
          {pendentes.map((v) => <ItemConta key={`${v.tipo}-${v.id}`} v={v} onPagar={onPagar} />)}
        </ul>
      )}
      {pagas.length > 0 && (
        <>
          <button onClick={() => setVerPagas(!verPagas)} className="mt-1 flex min-h-9 items-center gap-1 text-sm text-positivo">
            <CheckCircle2 className="size-4" aria-hidden /> {pagas.length} paga{pagas.length > 1 ? 's' : ''} · {dinheiro(pago)}
            <ChevronDown className={`size-4 transition ${verPagas ? 'rotate-180' : ''}`} aria-hidden />
          </button>
          {verPagas && (
            <ul className={comCabecalho ? '' : 'grid grid-cols-1 gap-x-6 md:grid-cols-2'}>
              {pagas.map((v) => <ItemConta key={`${v.tipo}-${v.id}`} v={v} onPagar={onPagar} />)}
            </ul>
          )}
        </>
      )}
    </div>
  )
}

function ItemConta({ v, onPagar }) {
  const navegar = useNavigate()
  const dias = diasAte(v.data)
  const emBreve = !v.pago && dias !== null && dias >= 0 && dias <= 7
  const Icone = v.tipo === 'fatura' ? CreditCard : Receipt
  const abrir = () => navegar(v.tipo === 'fatura' ? `/cartoes?cartao=${v.id}` : `/despesas?editar=${v.id}`)
  return (
    <li className={`flex items-center gap-3 border-b border-borda/60 py-2 last:border-b-0 ${v.vencido ? '-mx-2 rounded-xl border-transparent bg-negativo/10 px-2' : ''}`}>
      <CaixaPago marcado={v.pago} onChange={(pago) => onPagar(v, pago)} rotulo={v.pago ? 'Desmarcar pagamento' : 'Marcar como paga'} />
      <button onClick={abrir} className="flex min-w-0 flex-1 items-center gap-3 text-left">
        <span className="min-w-0 flex-1">
          <span className={`flex items-center gap-1.5 truncate text-sm ${v.pago ? 'text-apagado' : ''}`}>
            <Icone className="size-3.5 shrink-0 text-apagado" aria-hidden /> {v.descricao}
          </span>
          <span className="block text-xs">
            {v.pago ? (
              <span className="text-positivo">Pago</span>
            ) : v.vencido ? (
              <span className="font-medium text-negativo">Vencida em {dataCurta(v.data)}</span>
            ) : emBreve ? (
              <span className="text-alerta">{dias === 0 ? 'Vence hoje' : `Vence em ${dias} dia${dias > 1 ? 's' : ''} (${dataCurta(v.data)})`}</span>
            ) : (
              <span className="text-apagado">{v.data ? `Vence ${dataCurta(v.data)}` : 'Sem data'}</span>
            )}
          </span>
        </span>
        <span className={`text-sm ${v.pago ? 'text-apagado' : 'font-semibold'}`}>{dinheiro(v.valor)}</span>
      </button>
    </li>
  )
}

// ---------------------------------------------------------------- gráficos
function DicaGrafico({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-borda bg-painel px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 font-semibold">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="flex items-center gap-2">
          <span className="size-2 rounded-full" style={{ background: p.color }} />
          <span className="text-suave">{p.name}:</span> {dinheiro(p.value)}
        </p>
      ))}
      <p className="mt-1 text-apagado">Clique para ver este mês</p>
    </div>
  )
}

function GraficoProjecao({ dados, onEscolherMes }) {
  const linhas = dados.map((m) => ({ ...m, rotulo: mesCurto(m.ano, m.mes) }))
  const escolher = (e) => {
    const m = linhas[e?.activeTooltipIndex]
    if (m) onEscolherMes({ ano: m.ano, mes: m.mes })
  }
  return (
    <div className="h-64 w-full lg:h-80">
      <ResponsiveContainer>
        <ComposedChart data={linhas} margin={{ top: 8, right: 4, left: -8, bottom: 0 }} barGap={2} onClick={escolher} className="cursor-pointer">
          <CartesianGrid vertical={false} stroke={CORES.grade} />
          <XAxis dataKey="rotulo" tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tickFormatter={numeroCurto} tick={{ fill: CORES.eixo, fontSize: 11 }} tickLine={false} axisLine={false} width={58} />
          <Tooltip content={<DicaGrafico />} cursor={{ fill: 'var(--color-painel-2)' }} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: CORES.eixo }} />
          <Bar dataKey="receitas" name="Receitas" fill={CORES.receitas} radius={[4, 4, 0, 0]} maxBarSize={22} />
          <Bar dataKey="despesas" name="Despesas" fill={CORES.despesas} radius={[4, 4, 0, 0]} maxBarSize={22} />
          <Line dataKey="saldo" name="Saldo" stroke={CORES.saldo} strokeWidth={2} dot={{ r: 3, fill: CORES.saldo }} type="monotone" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function GraficoCategorias({ itens, total }) {
  const { opcoes } = useDados()
  const navegar = useNavigate()
  if (!itens.length) return <Vazio>Nenhuma despesa neste mês.</Vazio>
  // Até 8 categorias com cor própria; o restante é agrupado em "Outras"
  const fatias = itens.slice(0, 7)
  if (itens.length > 7) {
    fatias.push({ nome: 'Outras', valor: itens.slice(7).reduce((s, i) => s + i.valor, 0) })
  }
  const abrir = (nome) => {
    const categoria = opcoes.categorias.find((c) => c.nome === nome)
    navegar(categoria ? `/despesas?categoria=${categoria.id}` : '/despesas')
  }
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row lg:flex-col">
      <div className="h-44 w-44 shrink-0">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={fatias} dataKey="valor" nameKey="nome" innerRadius="62%" outerRadius="100%" paddingAngle={2} stroke="none" animationDuration={500} onClick={(f) => abrir(f.nome)} className="cursor-pointer">
              {fatias.map((f, i) => (
                <Cell key={f.nome} fill={CORES_CATEGORIAS[i]} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="rounded-xl border border-borda bg-painel-2 px-3 py-2 text-xs">
                    {payload[0].name}: {dinheiro(payload[0].value)}
                  </div>
                ) : null
              }
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-full space-y-0.5 text-sm">
        {fatias.map((f, i) => (
          <li key={f.nome}>
            <button onClick={() => abrir(f.nome)} className="flex w-full items-center gap-2 rounded-lg px-1 py-1 text-left hover:bg-painel-2">
              <span className="size-2.5 shrink-0 rounded-full" style={{ background: CORES_CATEGORIAS[i] }} />
              <span className="flex-1 truncate">{f.nome}</span>
              <span className="text-suave">{Math.round((f.valor / total) * 100)}%</span>
              <span className="w-24 text-right">{dinheiro(f.valor)}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ---------------------------------------------------------------- cartões
function BlocoCartoes({ faturas }) {
  if (!faturas.length) return <Vazio>Nenhum cartão cadastrado.</Vazio>
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {faturas.map((f) => (
        <Link key={f.cartao_id} to={`/cartoes?cartao=${f.cartao_id}`} className="rounded-xl border border-borda bg-painel-2 p-3 transition hover:border-apagado/50">
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-2 truncate text-sm font-medium">
              <CreditCard className="size-4 shrink-0 text-suave" aria-hidden /> {f.nome}
            </span>
            <span className="font-semibold">{dinheiro(f.total)}</span>
          </div>
          <p className="mt-1 text-xs text-apagado">
            {f.paga ? <span className="text-positivo">Paga · </span> : null}
            {f.data_vencimento ? `Vence ${dataCurta(f.data_vencimento)}` : 'Sem dia de vencimento'}
            {' · '}
            {f.termina_em ? `parcelas até ${mesAno(f.termina_em)}` : 'sem parcelamentos'}
          </p>
          {f.sem_dias && (
            <p className="mt-1 flex items-center gap-1 text-xs text-alerta">
              <AlertTriangle className="size-3" aria-hidden /> Cadastre fechamento e vencimento
            </p>
          )}
        </Link>
      ))}
    </div>
  )
}
