// Despesas fixas e parceladas: marcar como paga, progresso, filtros, editar e excluir.
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ChevronDown, CreditCard, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { data, dataCurta, dinheiro, hojeIso, lerValor, mesAno, nomeMes, valorParaCampo } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import SeletorMes, { mesAtual } from '../components/SeletorMes'
import CampoResponsavel, { MarcaPessoa, responsavelParaApi, useResponsaveis } from '../components/CampoResponsavel'
import CampoCategoria from '../components/CampoCategoria'
import {
  AreaTexto, BarraProgresso, Botao, BotaoIcone, CaixaPago, Campo, CampoValor, Carregando, Etiqueta,
  Indicador, MensagemErro, Modal, Opcoes, Selecao, Titulo, Vazio,
} from '../components/ui'

const STATUS = ['Fixa', 'Em andamento', 'A iniciar', 'Quitado', 'Cancelada']
const ATIVAS = ['Fixa', 'Em andamento', 'A iniciar']
const COR_STATUS = {
  Fixa: 'border-borda text-texto',
  'Em andamento': 'border-alerta/50 text-alerta',
  'A iniciar': 'border-borda text-suave',
  Quitado: 'border-positivo/50 text-positivo',
  Cancelada: 'border-borda text-apagado',
}

export default function Despesas() {
  const { opcoes, versao, dadosMudaram, avisar, excluir } = useDados()
  const [mes, setMes] = useState(mesAtual)
  const ehMesAtual = mes.ano === mesAtual().ano && mes.mes === mesAtual().mes
  const url = `/despesas?ano=${mes.ano}&mes=${mes.mes}`
  const { dados, carregando, erro, recarregar, setDados } = useCarregar(() => api.get(url), [url, versao], url)
  const [params, setParams] = useSearchParams()
  const [busca, setBusca] = useState('')
  const [filtros, setFiltros] = useState({
    categoria: params.get('categoria') ?? '',
    forma: '',
    status: params.get('status') ?? 'ativas',
    responsavel: params.get('responsavel') ?? '',
  })
  const responsaveis = useResponsaveis()
  // Quem paga no mês escolhido (pode ter sido trocado só a partir de algum mês)
  const quemPaga = (d) => responsaveis.efetivo({ ...d, responsavel_id: d.responsavel_no_mes ?? d.responsavel_id })
  const [editando, setEditando] = useState(null) // null | 'nova' | despesa

  // Vindo do Dashboard: /despesas?editar=ID abre a despesa; ?categoria, ?status e ?responsavel filtram
  useEffect(() => {
    const id = params.get('editar')
    if (id && dados) {
      const alvo = dados.find((d) => String(d.id) === id)
      if (alvo) setEditando(alvo)
    }
  }, [params, dados])

  const fecharModal = () => {
    setEditando(null)
    if (params.has('editar')) {
      params.delete('editar')
      setParams(params, { replace: true })
    }
  }

  const lista = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    return (dados ?? []).filter((d) => {
      if (termo && !d.descricao.toLowerCase().includes(termo)) return false
      if (filtros.categoria && String(d.categoria_id) !== filtros.categoria) return false
      if (filtros.forma && String(d.forma_pagamento_id) !== filtros.forma) return false
      if (filtros.responsavel && String(quemPaga(d) ?? 'conjunto') !== filtros.responsavel) return false
      const status = d.situacao.status
      if (filtros.status === 'ativas') return ATIVAS.includes(status) || Boolean(d.vencimento_mes_atual)
      if (filtros.status === 'do-mes') return Boolean(d.vencimento_mes_atual)
      if (filtros.status === 'a-pagar') return d.vencimento_mes_atual && !d.pago_mes_atual
      if (filtros.status) return status === filtros.status
      return true
    })
  }, [dados, filtros, busca, quemPaga])

  // Os totais acompanham a pessoa escolhida
  const daPessoa = (d) => !filtros.responsavel || String(quemPaga(d) ?? 'conjunto') === filtros.responsavel
  const doMes = (dados ?? []).filter((d) => d.vencimento_mes_atual && daPessoa(d))
  const totalMes = doMes.reduce((s, d) => s + d.valor_mensal, 0)
  const pagoMes = doMes.filter((d) => d.pago_mes_atual).reduce((s, d) => s + d.valor_mensal, 0)
  const totalDevo = (dados ?? []).filter(daPessoa).reduce((s, d) => s + (progressoNoMes(d).ainda_devo || 0), 0)
  const mudar = (campo) => (e) => setFiltros({ ...filtros, [campo]: e.target.value })

  // Outro mês: mostra as contas que cobram nele (é onde dá para marcar como paga)
  const trocarMes = (novo) => {
    setMes(novo)
    const atual = mesAtual()
    const voltouParaHoje = novo.ano === atual.ano && novo.mes === atual.mes
    if (voltouParaHoje && filtros.status === 'do-mes') setFiltros({ ...filtros, status: 'ativas' })
    else if (!voltouParaHoje && filtros.status === 'ativas') setFiltros({ ...filtros, status: 'do-mes' })
  }

  const marcarPago = async (d, pago) => {
    const { ano } = mes
    setDados((lista) => lista.map((x) => (x.id === d.id ? { ...x, pago_mes_atual: pago } : x)))
    try {
      await api.patch(`/despesas/${d.id}/pagamento`, { ano, mes: mes.mes, pago })
      avisar(pago ? `${d.descricao}: paga` : 'Pagamento desmarcado')
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
      recarregar()
    }
  }

  const apagar = (d) => excluir(`/despesas/${d.id}`, `"${d.descricao}"`)

  return (
    <div className="space-y-6">
      <Titulo acao={<Botao onClick={() => setEditando('nova')}><Plus className="size-4" /> Nova</Botao>}>Despesas</Titulo>

      <SeletorMes valor={mes} onChange={trocarMes} />

      {dados && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Indicador rotulo={ehMesAtual ? 'Contas deste mês' : `Contas de ${nomeMes(mes.ano, mes.mes).split(' ')[0].toLowerCase()}`} valor={dinheiro(totalMes)} detalhe={`${doMes.length} contas`} />
          <Indicador rotulo="Já paguei" valor={dinheiro(pagoMes)} cor="text-positivo" onClick={() => setFiltros({ ...filtros, status: '' })} />
          <Indicador rotulo="Falta pagar" valor={dinheiro(totalMes - pagoMes)} onClick={() => setFiltros({ ...filtros, status: 'a-pagar' })} />
          <Indicador rotulo="Ainda devo (parcelas)" valor={dinheiro(totalDevo)} />
        </div>
      )}

      {responsaveis.ativo && (
        <Opcoes
          opcoes={[
            { valor: '', rotulo: 'Todas as pessoas' },
            ...responsaveis.lista.map((p) => ({ valor: String(p.id), rotulo: <MarcaPessoa id={p.id} /> })),
            { valor: 'conjunto', rotulo: <MarcaPessoa id={null} /> },
          ]}
          valor={filtros.responsavel}
          onChange={(responsavel) => setFiltros({ ...filtros, responsavel })}
        />
      )}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <label className="relative col-span-2 md:col-span-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-apagado" />
          <input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar"
            className="min-h-11 w-full rounded-xl border border-borda bg-painel pr-3 pl-9 focus:border-apagado focus:outline-none"
            aria-label="Buscar despesa"
          />
        </label>
        <Selecao vazio="Todas categorias" opcoes={opcoes.categorias} value={filtros.categoria} onChange={mudar('categoria')} aria-label="Filtrar por categoria" />
        <Selecao vazio="Todas as formas" opcoes={opcoes.formas_pagamento} value={filtros.forma} onChange={mudar('forma')} aria-label="Filtrar por forma de pagamento" />
        <Selecao
          className="col-span-2 md:col-span-1"
          opcoes={[
            { id: 'ativas', nome: 'Ativas' },
            { id: 'do-mes', nome: 'Cobram no mês' },
            { id: 'a-pagar', nome: 'A pagar no mês' },
            { id: '', nome: 'Todos os status' },
            ...STATUS.map((s) => ({ id: s, nome: s })),
          ]}
          value={filtros.status}
          onChange={mudar('status')}
          aria-label="Filtrar por status"
        />
      </div>

      {erro && <MensagemErro mensagem={erro} tentarNovamente={recarregar} />}
      {carregando && !dados && <Carregando />}
      {dados && !lista.length && <Vazio>Nenhuma despesa com esses filtros.</Vazio>}

      {/* Celular: cartões */}
      {lista.length > 0 && (
        <ul className="space-y-2 md:hidden">
          {lista.map((d) => (
            <li key={d.id} className="rounded-2xl border border-borda bg-painel p-4">
              <div className="flex items-start gap-3">
                <div className="pt-0.5">
                  {d.vencimento_mes_atual ? (
                    <CaixaConta d={d} onChange={(p) => marcarPago(d, p)} />
                  ) : (
                    <span className="block size-7" />
                  )}
                </div>
                <button onClick={() => setEditando(d)} className="min-w-0 flex-1 text-left">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className={`truncate font-medium ${d.pago_mes_atual ? 'text-suave' : ''}`}>{d.descricao}</p>
                      <p className="text-xs text-apagado">
                        {d.categoria} · {d.forma}
                        {d.vencimento_mes_atual && ` · vence ${dataCurta(d.vencimento_mes_atual)}`}
                      </p>
                      {responsaveis.ativo && <QuemPaga d={d} id={quemPaga(d)} className="mt-0.5 text-xs text-suave" />}
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{dinheiro(d.valor_mensal)}</p>
                      <Etiqueta cor={COR_STATUS[statusNoMes(d)]}>{statusNoMes(d)}</Etiqueta>
                    </div>
                  </div>
                  <Progresso d={d} />
                </button>
                <BotaoIcone rotulo={`Excluir ${d.descricao}`} onClick={() => apagar(d)} className="-mr-1 hover:text-negativo">
                  <Trash2 className="size-4" />
                </BotaoIcone>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Computador: tabela */}
      {lista.length > 0 && (
        <div className="hidden overflow-hidden rounded-2xl border border-borda bg-painel md:block">
          <table className="w-full text-sm">
            <thead className="border-b border-borda text-left text-xs text-suave">
              <tr>
                <th className="w-14 px-4 py-3 font-medium">Pago</th>
                <th className="px-2 py-3 font-medium">Descrição</th>
                {responsaveis.ativo && <th className="px-2 py-3 font-medium">De quem</th>}
                <th className="px-2 py-3 font-medium">Forma</th>
                <th className="px-2 py-3 font-medium">Vence</th>
                <th className="px-2 py-3 text-right font-medium">Valor</th>
                <th className="w-56 px-4 py-3 font-medium">Parcelas</th>
                <th className="px-2 py-3 font-medium">Status</th>
                <th className="w-24 px-2 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-borda/60">
              {lista.map((d) => (
                <tr key={d.id} className="cursor-pointer transition hover:bg-painel-2/50" onClick={() => setEditando(d)}>
                  <td className="px-4 py-2.5">
                    {d.vencimento_mes_atual && <CaixaConta d={d} onChange={(p) => marcarPago(d, p)} />}
                  </td>
                  <td className="px-2 py-2.5">
                    <p className={`font-medium ${d.pago_mes_atual ? 'text-suave' : ''}`}>{d.descricao}</p>
                    <p className="text-xs text-apagado">{d.categoria}</p>
                  </td>
                  {responsaveis.ativo && <td className="px-2 py-2.5 text-suave"><QuemPaga d={d} id={quemPaga(d)} /></td>}
                  <td className="px-2 py-2.5 text-suave">{d.forma}</td>
                  <td className="px-2 py-2.5 text-suave">{d.vencimento_mes_atual ? dataCurta(d.vencimento_mes_atual) : '—'}</td>
                  <td className="px-2 py-2.5 text-right font-semibold">{dinheiro(d.valor_mensal)}</td>
                  <td className="px-4 py-2.5"><Progresso d={d} /></td>
                  <td className="px-2 py-2.5"><Etiqueta cor={COR_STATUS[statusNoMes(d)]}>{statusNoMes(d)}</Etiqueta></td>
                  <td className="px-2 py-2.5 text-right" onClick={(e) => e.stopPropagation()}>
                    <BotaoIcone rotulo={`Editar ${d.descricao}`} onClick={() => setEditando(d)}><Pencil className="size-4" /></BotaoIcone>
                    <BotaoIcone rotulo={`Excluir ${d.descricao}`} onClick={() => apagar(d)} className="hover:text-negativo"><Trash2 className="size-4" /></BotaoIcone>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal aberto={editando !== null} titulo={editando === 'nova' ? 'Nova despesa' : 'Editar despesa'} onFechar={fecharModal}>
        {editando !== null && <FormDespesa despesa={editando === 'nova' ? null : editando} mes={mes} onFechar={fecharModal} />}
      </Modal>
    </div>
  )
}

// Pessoa que paga no mês; "trocado" quando é diferente do cadastro da conta
function QuemPaga({ d, id, className = '' }) {
  const trocado = d.trocas?.length > 0 && (d.responsavel_no_mes ?? null) !== (d.responsavel_id ?? null)
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <MarcaPessoa id={id} />
      {trocado && <span className="rounded-md border border-borda px-1 text-[10px] text-apagado" title="Quem paga mudou a partir de algum mês">trocado</span>}
    </span>
  )
}

// Quem pagou/paga em cada período (quando houve troca)
function HistoricoQuemPaga({ trocas, inicial }) {
  const { nome } = useResponsaveis()
  if (!trocas?.length) return null
  const partes = [`${nome(inicial ?? null)} no início`, ...trocas.map((t) => `${nome(t.responsavel_id)} a partir de ${mesAno(t.a_partir_de.slice(0, 7))}`)]
  return <p className="-mt-2 text-xs text-apagado">Quem paga: {partes.join(' → ')}</p>
}

// Conta no cartão é paga junto com a fatura (marcar em Cartões); as outras, aqui
function CaixaConta({ d, onChange }) {
  if (d.cartao_id) {
    return (
      <Link
        to={`/cartoes?cartao=${d.cartao_id}`}
        onClick={(e) => e.stopPropagation()}
        title={d.pago_mes_atual ? 'Fatura paga' : 'Paga junto com a fatura do cartão'}
        className={`flex size-7 items-center justify-center rounded-lg border ${d.pago_mes_atual ? 'border-positivo/50 text-positivo' : 'border-borda text-apagado'}`}
      >
        <CreditCard className="size-4" aria-label={d.pago_mes_atual ? 'Fatura paga' : 'Paga com a fatura'} />
      </Link>
    )
  }
  return <CaixaPago marcado={d.pago_mes_atual} onChange={onChange} rotulo={d.pago_mes_atual ? 'Desmarcar pagamento' : 'Marcar como paga no mês'} />
}

// Parcelas pagas olhando o mês escolhido: a parcela do mês só conta depois de
// marcada como paga (no cartão: fatura paga), igual ao "2/2" da tela de Cartões
function progressoNoMes(d) {
  if (!d.num_parcelas || !d.parcela_no_mes) return d.situacao
  const pagas = d.parcela_no_mes - (d.pago_mes_atual ? 0 : 1)
  const faltam = d.num_parcelas - pagas
  return { ...d.situacao, pagas, faltam, ainda_devo: faltam * d.valor_mensal }
}

// Última parcela já paga: mostra "Quitado" mesmo antes do mês acabar
function statusNoMes(d) {
  const p = progressoNoMes(d)
  return d.num_parcelas && p.faltam === 0 ? 'Quitado' : d.situacao.status
}

function Progresso({ d }) {
  if (d.situacao.status === 'Cancelada') {
    return d.cancelada_em ? <p className="mt-1 text-xs text-apagado">Cancelada em {data(d.cancelada_em)}</p> : null
  }
  if (!d.num_parcelas) return null
  const p = progressoNoMes(d)
  return (
    <div className="mt-2 md:mt-0">
      <div className="mb-1 flex justify-between gap-2 text-xs text-suave">
        <span>{p.pagas}/{d.num_parcelas}</span>
        <span className="truncate">
          {p.faltam > 0 ? `faltam ${dinheiro(p.ainda_devo)} · até ${mesAno(p.termina_em)}` : `terminou ${mesAno(p.termina_em)}`}
        </span>
      </div>
      <BarraProgresso atual={p.pagas} total={d.num_parcelas} cor={p.faltam ? 'bg-destaque' : 'bg-positivo'} />
    </div>
  )
}

// Quem paga no mês aberto; sem essa informação (ex.: vindo de outra tela), o do cadastro
const quemPagavaNoMes = (despesa) =>
  (despesa?.responsavel_no_mes !== undefined ? despesa.responsavel_no_mes : despesa?.responsavel_id) ?? ''

// Para quais meses vale a troca de quem paga (conta que já existia)
const ALCANCE_TROCA = (rotuloMes) => [
  { valor: 'so', rotulo: `Só em ${rotuloMes}` },
  { valor: 'diante', rotulo: `De ${rotuloMes} em diante` },
  { valor: 'todos', rotulo: 'Todos os meses' },
]

export function FormDespesa({ despesa, mes = mesAtual(), onFechar }) {
  const { opcoes, dadosMudaram, avisar, excluir } = useDados()
  const idPadrao = (lista, nome) => lista.find((i) => i.nome === nome)?.id ?? lista[0]?.id ?? ''
  const [form, setForm] = useState({
    descricao: despesa?.descricao ?? '',
    valor: valorParaCampo(despesa?.valor_mensal),
    categoria_id: despesa?.categoria_id ?? idPadrao(opcoes.categorias, 'Outros'),
    forma_pagamento_id: despesa?.forma_pagamento_id ?? idPadrao(opcoes.formas_pagamento, 'Pix'),
    parcelada: Boolean(despesa?.num_parcelas),
    num_parcelas: despesa?.num_parcelas ?? 2,
    primeira_cobranca: despesa?.primeira_cobranca ?? hojeIso(),
    dia_vencimento: despesa?.dia_vencimento ?? '',
    cancelada_em: despesa?.cancelada_em ?? '',
    observacao: despesa?.observacao ?? '',
    // Conta existente: mostra quem paga no mês aberto (pode ser diferente do cadastro)
    responsavel_id: quemPagavaNoMes(despesa),
  })
  const [alcance, setAlcance] = useState(null) // 'so' | 'diante' | 'todos'
  const trocouQuemPaga = Boolean(despesa) && String(form.responsavel_id) !== String(quemPagavaNoMes(despesa))
  // Conta que já cobrava antes deste mês (ou já tem trocas): a troca precisa dizer até onde vale
  const chaveMes = `${mes.ano}-${String(mes.mes).padStart(2, '0')}`
  const temPassado = Boolean(despesa) && (despesa.primeira_cobranca.slice(0, 7) < chaveMes || despesa.trocas?.length > 0)
  const rotuloMes = nomeMes(mes.ano, mes.mes).split(' ')[0].toLowerCase()
  const [detalhes, setDetalhes] = useState(Boolean(despesa?.cancelada_em || despesa?.observacao || despesa?.dia_vencimento))
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })
  // Paga no cartão: sem pessoa escolhida, conta para o dono do cartão
  const noCartao = Boolean(opcoes.formas_pagamento.find((f) => String(f.id) === String(form.forma_pagamento_id))?.cartao_id)

  const salvar = async (e) => {
    e.preventDefault()
    const valor = lerValor(form.valor)
    if (!valor || valor <= 0) return setErro('Informe um valor mensal maior que zero.')
    const porMes = trocouQuemPaga && temPassado
    if (porMes && !alcance) return setErro(`Escolha se a troca de quem paga vale só em ${rotuloMes} ou daí em diante.`)
    setSalvando(true)
    setErro(null)
    const corpo = {
      descricao: form.descricao,
      valor_mensal: valor,
      categoria_id: Number(form.categoria_id),
      forma_pagamento_id: Number(form.forma_pagamento_id),
      num_parcelas: form.parcelada ? Number(form.num_parcelas) : null,
      primeira_cobranca: form.primeira_cobranca,
      dia_vencimento: form.dia_vencimento ? Number(form.dia_vencimento) : null,
      cancelada_em: form.cancelada_em || null,
      observacao: form.observacao || null,
      // Troca só a partir de um mês: o cadastro continua com quem pagava antes
      responsavel_id: responsavelParaApi(porMes && alcance !== 'todos' ? despesa.responsavel_id : form.responsavel_id),
    }
    try {
      if (despesa) await api.put(`/despesas/${despesa.id}`, corpo)
      else await api.post('/despesas', corpo)
      if (porMes) {
        // "Todos os meses": refaz desde a 1ª cobrança, o que apaga as trocas antigas
        const [ano, m] = alcance === 'todos' ? despesa.primeira_cobranca.split('-').map(Number) : [mes.ano, mes.mes]
        await api.put(`/despesas/${despesa.id}/quem-paga`, {
          ano, mes: m, responsavel_id: responsavelParaApi(form.responsavel_id), so_este_mes: alcance === 'so',
        })
      }
      avisar('Despesa salva')
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  const apagar = async () => {
    try {
      if (await excluir(`/despesas/${despesa.id}`, `"${despesa.descricao}"`)) onFechar()
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <Campo rotulo="Descrição" value={form.descricao} onChange={mudar('descricao')} required maxLength={300} autoFocus={!despesa} placeholder="Ex.: Internet" />
      <CampoValor rotulo="Valor mensal" value={form.valor} onChange={mudar('valor')} required />
      <div className="grid grid-cols-2 items-start gap-3">
        <CampoCategoria value={form.categoria_id} onChange={(categoria_id) => setForm({ ...form, categoria_id })} />
        <Selecao rotulo="Forma" opcoes={opcoes.formas_pagamento} value={form.forma_pagamento_id} onChange={mudar('forma_pagamento_id')} />
      </div>
      <CampoResponsavel
        rotulo={temPassado ? `Quem paga em ${rotuloMes}` : 'De quem é'}
        vazio={noCartao ? 'Dono do cartão' : 'Conjunto'}
        valor={form.responsavel_id}
        onChange={(responsavel_id) => setForm({ ...form, responsavel_id })}
      />
      {trocouQuemPaga && temPassado && (
        <div className="-mt-2 space-y-2 rounded-xl bg-painel-2/60 p-3">
          <Opcoes rotulo="Essa troca vale para" opcoes={ALCANCE_TROCA(rotuloMes)} valor={alcance ?? ''} onChange={setAlcance} />
          <p className="text-xs text-apagado">
            {alcance === 'so' ? 'No mês seguinte volta quem pagava antes.'
              : alcance === 'diante' ? 'Os meses anteriores continuam como estão (inclusive os já pagos).'
                : alcance === 'todos' ? 'Corrige o cadastro: muda também os meses que já passaram.'
                  : 'Os meses que já passaram só mudam em "Todos os meses".'}
          </p>
        </div>
      )}
      <HistoricoQuemPaga trocas={despesa?.trocas} inicial={despesa?.responsavel_id} />
      <Opcoes
        rotulo="Tipo"
        opcoes={[{ valor: 'fixa', rotulo: 'Fixa (todo mês)' }, { valor: 'parcelada', rotulo: 'Parcelada' }]}
        valor={form.parcelada ? 'parcelada' : 'fixa'}
        onChange={(v) => setForm({ ...form, parcelada: v === 'parcelada' })}
      />
      <div className="grid grid-cols-2 gap-3">
        {form.parcelada && (
          <Campo rotulo="Nº de parcelas" type="number" min={1} max={600} inputMode="numeric" value={form.num_parcelas} onChange={mudar('num_parcelas')} required />
        )}
        <Campo rotulo="1ª cobrança" type="date" value={form.primeira_cobranca} onChange={mudar('primeira_cobranca')} required className={form.parcelada ? '' : 'col-span-2'} />
      </div>
      {noCartao && (
        <p className="-mt-2 text-xs text-apagado">
          No cartão, a 1ª cobrança é o mês da fatura em que a 1ª parcela é paga (não o dia da compra).
          Caiu no mês errado? Ajuste esta data.
        </p>
      )}

      <button type="button" onClick={() => setDetalhes(!detalhes)} className="flex items-center gap-1 text-sm text-suave">
        <ChevronDown className={`size-4 transition ${detalhes ? 'rotate-180' : ''}`} /> Mais detalhes
      </button>
      {detalhes && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Campo rotulo="Dia de vencimento" type="number" min={1} max={31} inputMode="numeric" value={form.dia_vencimento} onChange={mudar('dia_vencimento')} placeholder="mesmo da 1ª" />
            <Campo rotulo="Cancelei em" type="date" value={form.cancelada_em} onChange={mudar('cancelada_em')} />
          </div>
          <AreaTexto rotulo="Observação" value={form.observacao} onChange={mudar('observacao')} maxLength={2000} />
        </div>
      )}

      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {despesa && (
          <Botao type="button" variante="perigo" onClick={apagar}>
            <Trash2 className="size-4" /> Excluir
          </Botao>
        )}
        <Botao type="submit" carregando={salvando} className="flex-1">Salvar</Botao>
      </div>
    </form>
  )
}
