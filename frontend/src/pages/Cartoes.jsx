// Cartões: faturas por mês (marcar como paga) com tudo o que soma nelas, e dias de fechamento/vencimento.
import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AlertTriangle, CreditCard, Pencil, Plus, Repeat, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { dataCurta, dinheiro, mesCurto, nomeMes } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import FormGastoCartao from '../components/FormGastoCartao'
import SeletorMes, { mesAtual } from '../components/SeletorMes'
import CampoResponsavel, { MarcaPessoa, responsavelParaApi, useResponsaveis } from '../components/CampoResponsavel'
import { FormDespesa } from './Despesas'
import {
  Botao, BotaoIcone, CaixaPago, Campo, Carregando, MensagemErro, Modal, Titulo, Vazio,
} from '../components/ui'

export default function Cartoes() {
  const { versao, dadosMudaram, avisar, excluir } = useDados()
  const [mes, setMes] = useState(mesAtual)
  const ehMesAtual = mes.ano === mesAtual().ano && mes.mes === mesAtual().mes
  const cartoes = useCarregar(() => api.get('/cartoes'), [versao], '/cartoes')
  const urlProjecao = `/projecao?meses=5&ano=${mes.ano}&mes=${mes.mes}`
  const projecao = useCarregar(() => api.get(urlProjecao), [urlProjecao, versao], urlProjecao)
  const gastos = useCarregar(() => api.get('/gastos-cartao'), [versao], '/gastos-cartao')
  const despesas = useCarregar(() => api.get('/despesas'), [versao], '/despesas')
  const [editandoDespesa, setEditandoDespesa] = useState(null)
  const [params] = useSearchParams()
  const destaque = params.get('cartao')
  const refDestaque = useRef(null)
  const [editandoCartao, setEditandoCartao] = useState(null) // null | 'novo' | cartão
  const [gasto, setGasto] = useState(null) // null | { cartao_id, fixa? } (novo) | gasto (edição)
  const responsaveis = useResponsaveis()

  // Vindo do Dashboard: rola até o cartão escolhido
  useEffect(() => {
    refDestaque.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [cartoes.dados])

  // Faturas de cada cartão: mês escolhido + 5 seguintes
  const faturasPorCartao = useMemo(() => {
    const mapa = {}
    for (const m of projecao.dados ?? []) {
      for (const f of m.faturas) (mapa[f.cartao_id] ??= []).push({ ...f, ano: m.ano, mes: m.mes })
    }
    return mapa
  }, [projecao.dados])

  const pagarFatura = async (cartao, fatura, pago) => {
    try {
      await api.patch(`/cartoes/${cartao.id}/pagamento`, { ano: fatura.ano, mes: fatura.mes, pago })
      avisar(pago ? `Fatura ${cartao.nome} paga` : 'Pagamento desmarcado')
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
    }
  }

  // Clique num item da fatura: abre a conta (despesa) ou o gasto avulso para editar
  const editarItem = (item) => {
    if (item.origem === 'despesa') {
      const alvo = despesas.dados?.find((d) => d.id === item.id)
      if (alvo) setEditandoDespesa(alvo)
    } else {
      const alvo = gastos.dados?.find((g) => g.id === item.id)
      if (alvo) setGasto(alvo)
    }
  }
  const excluirItem = (item) =>
    item.origem === 'despesa'
      ? excluir(`/despesas/${item.id}`, `"${item.descricao}"`)
      : excluir(`/gastos-cartao/${item.id}`, `o gasto "${item.descricao}"`)

  const erro = cartoes.erro || projecao.erro || gastos.erro || despesas.erro

  return (
    <div className="space-y-6">
      <Titulo acao={<Botao variante="secundario" onClick={() => setEditandoCartao('novo')}><Plus className="size-4" /> Cartão</Botao>}>
        Cartões
      </Titulo>

      <SeletorMes valor={mes} onChange={setMes} />

      {erro && <MensagemErro mensagem={erro} tentarNovamente={() => [cartoes, projecao, gastos, despesas].forEach((c) => c.recarregar())} />}
      {cartoes.carregando && !cartoes.dados && <Carregando />}
      {cartoes.dados && !cartoes.dados.length && <Vazio>Nenhum cartão cadastrado.</Vazio>}

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {cartoes.dados?.map((c) => {
          const faturas = faturasPorCartao[c.id] ?? []
          const atual = faturas[0]
          const semDias = !c.dia_fechamento || !c.dia_vencimento
          const ehDestaque = String(c.id) === destaque
          return (
            <section
              key={c.id}
              ref={ehDestaque ? refDestaque : null}
              className={`rounded-2xl border bg-painel p-5 sm:p-6 ${ehDestaque ? 'border-destaque/60 ring-4 ring-destaque/5' : 'border-borda'}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <CreditCard className="size-5 text-suave" aria-hidden />
                  <div>
                    <p className="font-semibold">{c.nome}</p>
                    <p className="text-xs text-apagado">
                      {semDias ? 'Dias não cadastrados' : `Fecha dia ${c.dia_fechamento} · vence dia ${c.dia_vencimento}`}
                    </p>
                    {responsaveis.ativo && <MarcaPessoa id={c.responsavel_id} className="mt-0.5 text-xs text-suave" />}
                  </div>
                </div>
                <BotaoIcone rotulo={`Editar ${c.nome}`} onClick={() => setEditandoCartao(c)}><Pencil className="size-4" /></BotaoIcone>
              </div>

              {semDias && (
                <button onClick={() => setEditandoCartao(c)} className="mt-2 flex w-full items-center gap-2 rounded-xl border border-alerta/40 bg-alerta/10 p-2 text-left text-xs">
                  <AlertTriangle className="size-4 shrink-0 text-alerta" aria-hidden />
                  Sem os dias, os gastos vão para o mês seguinte à compra. Toque para cadastrar.
                </button>
              )}

              {atual && (
                <div className={`mt-3 flex items-center gap-3 rounded-xl p-3 ${atual.paga ? 'bg-positivo/10' : 'bg-painel-2'}`}>
                  <CaixaPago marcado={atual.paga} onChange={(p) => pagarFatura(c, atual, p)} rotulo={atual.paga ? 'Desmarcar pagamento' : 'Marcar fatura como paga'} />
                  <div className="flex-1">
                    <p className="text-xs text-suave">
                      {ehMesAtual ? 'Fatura deste mês' : `Fatura de ${nomeMes(mes.ano, mes.mes).toLowerCase()}`}
                      {atual.data_vencimento && ` · vence ${dataCurta(atual.data_vencimento)}`}
                    </p>
                    <p className="text-lg font-bold">{dinheiro(atual.total)}</p>
                  </div>
                  <span className={`text-xs ${atual.paga ? 'text-positivo' : 'text-apagado'}`}>{atual.paga ? 'Paga' : 'Em aberto'}</span>
                </div>
              )}

              {faturas.length > 1 && (
                <div className="mt-2 grid grid-cols-5 gap-1.5">
                  {faturas.slice(1).map((f) => (
                    <div key={`${f.ano}-${f.mes}`} className="rounded-lg bg-painel-2/60 p-1.5 text-center">
                      <p className="text-[11px] text-apagado">{mesCurto(f.ano, f.mes)}</p>
                      <p className="text-xs font-medium">{f.total ? dinheiro(f.total).replace(',00', '') : '—'}</p>
                    </div>
                  ))}
                </div>
              )}

              {atual && <ItensDaFatura itens={atual.itens ?? []} mostrarPessoa={responsaveis.ativo} onEditar={editarItem} onExcluir={excluirItem} />}

              <div className="mt-3 grid grid-cols-2 gap-2">
                <Botao variante="secundario" onClick={() => setGasto({ cartao_id: c.id })}>
                  <Plus className="size-4" /> Gasto
                </Botao>
                <Botao variante="secundario" onClick={() => setGasto({ cartao_id: c.id, fixa: true })}>
                  <Repeat className="size-4" /> Conta fixa
                </Botao>
              </div>
            </section>
          )
        })}
      </div>

      <Modal
        aberto={gasto !== null}
        titulo={gasto?.id ? 'Editar gasto' : gasto?.fixa ? 'Conta fixa no cartão' : 'Gasto no cartão'}
        onFechar={() => setGasto(null)}
      >
        {gasto !== null && (
          <FormGastoCartao
            gasto={gasto.id ? gasto : undefined}
            cartaoInicial={gasto.id ? undefined : gasto.cartao_id}
            fixaInicial={Boolean(gasto.fixa)}
            onSalvo={() => setGasto(null)}
            onExcluir={
              gasto.id
                ? async () => (await excluir(`/gastos-cartao/${gasto.id}`, `o gasto "${gasto.descricao}"`)) && setGasto(null)
                : undefined
            }
          />
        )}
      </Modal>
      <Modal aberto={editandoDespesa !== null} titulo="Editar conta do cartão" onFechar={() => setEditandoDespesa(null)}>
        {editandoDespesa && <FormDespesa despesa={editandoDespesa} onFechar={() => setEditandoDespesa(null)} />}
      </Modal>
      <Modal aberto={editandoCartao !== null} titulo={editandoCartao === 'novo' ? 'Novo cartão' : 'Editar cartão'} onFechar={() => setEditandoCartao(null)}>
        {editandoCartao !== null && <FormCartao cartao={editandoCartao === 'novo' ? null : editandoCartao} onFechar={() => setEditandoCartao(null)} />}
      </Modal>
    </div>
  )
}

// Tudo o que soma na fatura do mês escolhido (contas do cartão + gastos avulsos):
// a soma desta lista é sempre o total da fatura
function ItensDaFatura({ itens, mostrarPessoa, onEditar, onExcluir }) {
  if (!itens.length) return <p className="mt-3 text-center text-xs text-apagado">Nada nesta fatura.</p>
  const fixas = itens.filter((i) => i.origem === 'despesa' && !i.num_parcelas)
  const totalFixo = fixas.reduce((s, i) => s + i.valor, 0)
  return (
    <div className="mt-3">
      <p className="mb-1 flex justify-between text-xs text-suave">
        <span>Itens desta fatura</span>
        {fixas.length > 0 && <span>fixas: {dinheiro(totalFixo)}/mês</span>}
      </p>
      <ul className="divide-y divide-borda/60 rounded-xl bg-painel-2/50 px-2">
        {itens.map((i) => (
          <li key={`${i.origem}-${i.id}`} className="flex items-center gap-1">
            <button onClick={() => onEditar(i)} className="flex min-w-0 flex-1 items-center gap-2 py-2 text-left text-sm">
              {i.origem === 'despesa' && !i.num_parcelas && <Repeat className="size-3.5 shrink-0 text-saldo" aria-label="todo mês" />}
              <span className="min-w-0 flex-1">
                <span className="block truncate">{i.descricao}</span>
                {mostrarPessoa && <MarcaPessoa id={i.responsavel_id} className="text-xs text-apagado" />}
              </span>
              <span className="text-xs text-apagado">
                {i.num_parcelas ? `${i.parcela_atual}/${i.num_parcelas}` : i.origem === 'despesa' ? 'todo mês' : 'à vista'}
              </span>
              <span className="w-20 text-right">{dinheiro(i.valor)}</span>
            </button>
            <BotaoIcone rotulo={`Excluir ${i.descricao}`} onClick={() => onExcluir(i)} className="size-8 hover:text-negativo">
              <Trash2 className="size-3.5" />
            </BotaoIcone>
          </li>
        ))}
      </ul>
    </div>
  )
}

function FormCartao({ cartao, onFechar }) {
  const { dadosMudaram, recarregarOpcoes, avisar, excluir } = useDados()
  const [form, setForm] = useState({
    nome: cartao?.nome ?? '',
    dia_fechamento: cartao?.dia_fechamento ?? '',
    dia_vencimento: cartao?.dia_vencimento ?? '',
    responsavel_id: cartao?.responsavel_id ?? '',
  })
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })

  const salvar = async (e) => {
    e.preventDefault()
    setSalvando(true)
    setErro(null)
    const corpo = {
      nome: form.nome,
      dia_fechamento: form.dia_fechamento ? Number(form.dia_fechamento) : null,
      dia_vencimento: form.dia_vencimento ? Number(form.dia_vencimento) : null,
      responsavel_id: responsavelParaApi(form.responsavel_id),
    }
    try {
      if (cartao) await api.put(`/cartoes/${cartao.id}`, corpo)
      else await api.post('/cartoes', corpo)
      avisar('Cartão salvo')
      recarregarOpcoes()
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  const apagar = async () => {
    try {
      if (await excluir(`/cartoes/${cartao.id}`, `o cartão "${cartao.nome}"`)) {
        recarregarOpcoes()
        onFechar()
      }
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <Campo rotulo="Nome" value={form.nome} onChange={mudar('nome')} required maxLength={300} />
      <div className="grid grid-cols-2 gap-3">
        <Campo rotulo="Dia do fechamento" type="number" min={1} max={31} inputMode="numeric" value={form.dia_fechamento} onChange={mudar('dia_fechamento')} />
        <Campo rotulo="Dia do vencimento" type="number" min={1} max={31} inputMode="numeric" value={form.dia_vencimento} onChange={mudar('dia_vencimento')} />
      </div>
      <p className="text-xs text-apagado">
        Compras até o dia do fechamento entram na fatura daquele mês; depois dele, na fatura seguinte.
      </p>
      <CampoResponsavel rotulo="Dono do cartão" valor={form.responsavel_id} onChange={(responsavel_id) => setForm({ ...form, responsavel_id })} />
      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {cartao && <Botao type="button" variante="perigo" onClick={apagar}><Trash2 className="size-4" /> Excluir</Botao>}
        <Botao type="submit" carregando={salvando} className="flex-1">Salvar</Botao>
      </div>
    </form>
  )
}
