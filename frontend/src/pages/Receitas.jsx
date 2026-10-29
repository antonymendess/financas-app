// Receitas: salário e outras entradas (recorrentes ou avulsas).
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AlertTriangle, ChevronDown, Plus, Repeat, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { data, dinheiro, hojeIso, lerValor, mesAno, valorParaCampo } from '../lib/formato'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import CampoResponsavel, { MarcaPessoa, responsavelParaApi, useResponsaveis } from '../components/CampoResponsavel'
import {
  Botao, BotaoIcone, Campo, CampoValor, Carregando, Etiqueta, Interruptor, MensagemErro, Modal,
  Opcoes, Titulo, Vazio,
} from '../components/ui'

export default function Receitas() {
  const { versao, excluir } = useDados()
  const { dados, carregando, erro, recarregar } = useCarregar(() => api.get('/receitas'), [versao], '/receitas')
  const [editando, setEditando] = useState(null) // null | 'nova' | 'salario' | receita
  const [params, setParams] = useSearchParams()
  const [verAntigas, setVerAntigas] = useState(false)
  const responsaveis = useResponsaveis()
  const hoje = hojeIso()

  // Vindo do Início: /receitas?nova=salario abre o formulário já como salário
  useEffect(() => {
    if (params.get('nova') === 'salario') {
      setEditando('salario')
      setParams({}, { replace: true })
    }
  }, [params, setParams])
  const ativa = (r) => (r.recorrente ? !r.data_fim || r.data_fim >= hoje : r.data_inicio.slice(0, 7) >= hoje.slice(0, 7))
  const totalRecorrente = (dados ?? []).filter((r) => r.recorrente && ativa(r)).reduce((s, r) => s + r.valor, 0)
  const antigas = (dados ?? []).filter((r) => !ativa(r)).length
  const visiveis = (dados ?? []).filter((r) => verAntigas || ativa(r))
  // Com pessoas cadastradas, a lista é separada por pessoa (sem pessoa = Conjunto, por último)
  const grupos = responsaveis.ativo
    ? [...responsaveis.lista.map((p) => p.id), null]
        .map((id) => ({ id, itens: visiveis.filter((r) => (r.responsavel_id ?? null) === id) }))
        .filter((g) => g.itens.length)
    : [{ id: undefined, itens: visiveis }]
  // Situação neste mês: já caiu ou em quantos dias cai
  const situacaoNoMes = (r) => {
    const mesHoje = hoje.slice(0, 7)
    if (!ativa(r) || r.data_inicio.slice(0, 7) > mesHoje) return null
    if (!r.recorrente && r.data_inicio.slice(0, 7) !== mesHoje) return null
    const dia = r.recorrente ? (r.dia_recebimento ?? Number(r.data_inicio.slice(8))) : Number(r.data_inicio.slice(8))
    const faltam = dia - Number(hoje.slice(8))
    if (faltam <= 0) return { texto: 'já caiu este mês', cor: 'text-positivo' }
    return { texto: `cai em ${faltam} dia${faltam > 1 ? 's' : ''}`, cor: 'text-saldo' }
  }
  const porMes = (itens) => itens.filter((r) => r.recorrente && ativa(r)).reduce((s, r) => s + r.valor, 0)

  return (
    <div>
      <Titulo acao={<Botao onClick={() => setEditando('nova')}><Plus className="size-4" /> Nova</Botao>}>Receitas</Titulo>
      {erro && <MensagemErro mensagem={erro} tentarNovamente={recarregar} />}
      {carregando && !dados && <Carregando />}
      {dados && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3 rounded-2xl border border-borda bg-painel p-5">
            <div>
              <p className="text-sm text-suave">Entra todo mês (recorrentes)</p>
              <p className="text-2xl font-bold text-positivo">{dinheiro(totalRecorrente)}</p>
            </div>
            {antigas > 0 && (
              <button onClick={() => setVerAntigas(!verAntigas)} className="text-sm text-saldo">
                {verAntigas ? 'Esconder antigas' : `Mostrar ${antigas} antiga${antigas > 1 ? 's' : ''}`}
              </button>
            )}
          </div>
          {!dados.length && (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-apagado">Nenhuma receita ainda. Comece pelo seu salário:</p>
              <Botao onClick={() => setEditando('salario')}><Repeat className="size-4" /> Cadastrar salário</Botao>
            </div>
          )}
          {grupos.map((g) => (
            <section key={g.id ?? 'conjunto'}>
              {g.id !== undefined && (
                <div className="mb-2 flex items-center justify-between gap-2 px-1">
                  <MarcaPessoa id={g.id} className="font-semibold" />
                  <span className="text-sm text-suave">{dinheiro(porMes(g.itens))}/mês</span>
                </div>
              )}
              {g.id === null && (
                <p className="mb-2 flex items-start gap-1.5 rounded-xl border border-alerta/40 bg-alerta/10 p-2.5 text-xs">
                  <AlertTriangle className="size-4 shrink-0 text-alerta" aria-hidden />
                  Receitas sem pessoa são divididas entre vocês no Início. Toque numa delas para dizer de quem é.
                </p>
              )}
              <ul className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
                {g.itens.map((r) => (
                  <li key={r.id} className={`flex min-w-0 items-center gap-1 rounded-2xl border border-borda bg-painel pr-1 ${ativa(r) ? '' : 'opacity-50'}`}>
                    <button onClick={() => setEditando(r)} className="flex min-w-0 flex-1 items-center gap-3 p-4 text-left">
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{r.descricao}</p>
                        <p className="text-xs text-apagado">
                          {r.recorrente
                            ? `Todo dia ${r.dia_recebimento ?? Number(r.data_inicio.slice(8))}${
                                // Começa num mês futuro: deixa claro que ainda não entra agora
                                r.data_inicio.slice(0, 7) > hoje.slice(0, 7) ? ` · a partir de ${mesAno(r.data_inicio.slice(0, 7))}` : ''
                              }${r.data_fim ? ` até ${data(r.data_fim)}` : ''}`
                            : `Em ${data(r.data_inicio)}`}
                        </p>
                        {situacaoNoMes(r) && <p className={`text-xs font-medium ${situacaoNoMes(r).cor}`}>{situacaoNoMes(r).texto}</p>}
                      </div>
                      <div className="text-right">
                        <p className="font-semibold">{dinheiro(r.valor)}</p>
                        <Etiqueta>{r.recorrente && <Repeat className="size-3" aria-hidden />}{r.tipo}</Etiqueta>
                      </div>
                    </button>
                    <BotaoIcone rotulo={`Excluir ${r.descricao}`} onClick={() => excluir(`/receitas/${r.id}`, `"${r.descricao}"`)} className="hover:text-negativo">
                      <Trash2 className="size-4" />
                    </BotaoIcone>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
      <Modal
        aberto={editando !== null}
        titulo={editando === 'salario' ? 'Salário (todo mês)' : editando === 'nova' ? 'Nova receita' : 'Editar receita'}
        onFechar={() => setEditando(null)}
      >
        {editando !== null && (
          <FormReceita
            receita={typeof editando === 'object' ? editando : null}
            descricaoInicial={editando === 'salario' ? 'Salário' : ''}
            onFechar={() => setEditando(null)}
          />
        )}
      </Modal>
    </div>
  )
}

export function FormReceita({ receita, descricaoInicial = '', onFechar }) {
  const { dadosMudaram, avisar, excluir } = useDados()
  const [form, setForm] = useState({
    descricao: receita?.descricao ?? descricaoInicial,
    valor: valorParaCampo(receita?.valor),
    tipo: receita?.tipo ?? 'Salário',
    recorrente: receita?.recorrente ?? true,
    dia_recebimento: receita?.dia_recebimento ?? '',
    data_inicio: receita?.data_inicio ?? hojeIso(),
    data_fim: receita?.data_fim ?? '',
    responsavel_id: receita?.responsavel_id ?? '',
  })
  const [detalhes, setDetalhes] = useState(Boolean(receita?.data_fim))
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)
  const mudar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })

  const salvar = async (e) => {
    e.preventDefault()
    const valor = lerValor(form.valor)
    if (!valor || valor <= 0) return setErro('Informe um valor maior que zero.')
    setSalvando(true)
    setErro(null)
    const corpo = {
      ...form,
      valor,
      dia_recebimento: form.recorrente && form.dia_recebimento ? Number(form.dia_recebimento) : null,
      data_fim: form.recorrente ? form.data_fim || null : null,
      responsavel_id: responsavelParaApi(form.responsavel_id),
    }
    try {
      if (receita) await api.put(`/receitas/${receita.id}`, corpo)
      else await api.post('/receitas', corpo)
      avisar('Receita salva')
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  const apagar = async () => {
    try {
      if (await excluir(`/receitas/${receita.id}`, `"${receita.descricao}"`)) onFechar()
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <Campo rotulo="Descrição" value={form.descricao} onChange={mudar('descricao')} required maxLength={300} autoFocus={!receita && !descricaoInicial} placeholder="Ex.: Salário" />
      <CampoValor rotulo={form.recorrente ? 'Valor por mês' : 'Valor'} value={form.valor} onChange={mudar('valor')} required autoFocus={Boolean(descricaoInicial)} />
      <Opcoes rotulo="Tipo" opcoes={['Salário', 'Extra', 'Comissão', 'Outros']} valor={form.tipo} onChange={(tipo) => setForm({ ...form, tipo })} />
      <CampoResponsavel rotulo="De quem é" valor={form.responsavel_id} onChange={(responsavel_id) => setForm({ ...form, responsavel_id })} />
      <Interruptor
        rotulo="Recebo todo mês"
        dica={form.recorrente ? 'Entra em todos os meses, sem data de fim' : 'Entra só no mês da data'}
        checked={form.recorrente}
        onChange={(recorrente) => setForm({ ...form, recorrente })}
      />
      {form.recorrente ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Campo rotulo="Dia que cai na conta" type="number" min={1} max={31} inputMode="numeric" value={form.dia_recebimento} onChange={mudar('dia_recebimento')} placeholder="ex.: 5" />
            <Campo rotulo="A partir de" type="date" value={form.data_inicio} onChange={mudar('data_inicio')} required />
          </div>
          <button type="button" onClick={() => setDetalhes(!detalhes)} className="flex items-center gap-1 text-sm text-suave">
            <ChevronDown className={`size-4 transition ${detalhes ? 'rotate-180' : ''}`} /> Mais detalhes
          </button>
          {detalhes && (
            <Campo rotulo="Até (opcional, ex.: troca de emprego)" type="date" value={form.data_fim} onChange={mudar('data_fim')} />
          )}
        </>
      ) : (
        <Campo rotulo="Data do recebimento" type="date" value={form.data_inicio} onChange={mudar('data_inicio')} required />
      )}
      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {receita && <Botao type="button" variante="perigo" onClick={apagar}><Trash2 className="size-4" /> Excluir</Botao>}
        <Botao type="submit" carregando={salvando} className="flex-1">Salvar</Botao>
      </div>
    </form>
  )
}
