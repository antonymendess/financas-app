// Categorias de despesa: criar, renomear e excluir.
// Ao excluir uma categoria em uso, os lançamentos dela são movidos para outra.
import { useState } from 'react'
import { Lock, Pencil, Plus, Tags, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import { Botao, BotaoIcone, Campo, Carregando, MensagemErro, Modal, Selecao, Titulo, Vazio } from '../components/ui'

export default function Categorias() {
  const { versao } = useDados()
  const { dados, carregando, erro, recarregar } = useCarregar(() => api.get('/categorias'), [versao], '/categorias')
  const [editando, setEditando] = useState(null) // null | 'nova' | categoria
  const [excluindo, setExcluindo] = useState(null) // categoria

  return (
    <div className="space-y-6">
      <Titulo acao={<Botao onClick={() => setEditando('nova')}><Plus className="size-4" /> Categoria</Botao>}>Categorias</Titulo>
      <p className="text-sm text-suave">Usadas nas despesas e nos gastos do cartão. Toque numa categoria para renomear.</p>

      {erro && <MensagemErro mensagem={erro} tentarNovamente={recarregar} />}
      {carregando && !dados && <Carregando />}
      {dados && !dados.length && <Vazio>Nenhuma categoria.</Vazio>}

      {dados?.length > 0 && (
        <ul className="grid grid-cols-1 gap-x-6 overflow-hidden rounded-2xl border border-borda bg-painel md:grid-cols-2">
          {dados.map((c) => {
            const usos = c.despesas + c.gastos
            return (
              <li key={c.id} className="flex items-center gap-2 border-b border-borda/60 px-4">
                <Tags className="size-4 shrink-0 text-apagado" aria-hidden />
                <button onClick={() => !c.protegida && setEditando(c)} className="min-h-14 min-w-0 flex-1 text-left" disabled={c.protegida}>
                  <span className="block truncate">{c.nome}</span>
                  <span className="block text-xs text-apagado">
                    {usos ? `${usos} lançamento${usos > 1 ? 's' : ''}` : 'sem lançamentos'}
                    {c.protegida && ' · padrão do sistema'}
                  </span>
                </button>
                {c.protegida ? (
                  <Lock className="size-4 text-apagado" aria-label="Categoria padrão: não pode ser renomeada nem excluída" />
                ) : (
                  <>
                    <BotaoIcone rotulo={`Renomear ${c.nome}`} onClick={() => setEditando(c)}><Pencil className="size-4" /></BotaoIcone>
                    <BotaoIcone rotulo={`Excluir ${c.nome}`} onClick={() => setExcluindo(c)} className="hover:text-negativo"><Trash2 className="size-4" /></BotaoIcone>
                  </>
                )}
              </li>
            )
          })}
        </ul>
      )}

      <Modal aberto={editando !== null} titulo={editando === 'nova' ? 'Nova categoria' : 'Renomear categoria'} onFechar={() => setEditando(null)}>
        {editando !== null && <FormCategoria categoria={editando === 'nova' ? null : editando} onFechar={() => setEditando(null)} />}
      </Modal>
      <Modal aberto={excluindo !== null} titulo={`Excluir "${excluindo?.nome ?? ''}"`} onFechar={() => setExcluindo(null)}>
        {excluindo && <ExcluirCategoria categoria={excluindo} outras={(dados ?? []).filter((c) => c.id !== excluindo.id)} onFechar={() => setExcluindo(null)} />}
      </Modal>
    </div>
  )
}

function FormCategoria({ categoria, onFechar }) {
  const { recarregarOpcoes, dadosMudaram, avisar } = useDados()
  const [nome, setNome] = useState(categoria?.nome ?? '')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  const salvar = async (e) => {
    e.preventDefault()
    setSalvando(true)
    setErro(null)
    try {
      if (categoria) await api.put(`/categorias/${categoria.id}`, { nome })
      else await api.post('/categorias', { nome })
      avisar('Categoria salva')
      recarregarOpcoes()
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <Campo rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={60} autoFocus placeholder="Ex.: Mercado" />
      {categoria && (categoria.despesas + categoria.gastos) > 0 && (
        <p className="text-xs text-apagado">O novo nome aparece em todos os lançamentos desta categoria.</p>
      )}
      {erro && <MensagemErro mensagem={erro} />}
      <Botao type="submit" carregando={salvando} className="w-full">Salvar</Botao>
    </form>
  )
}

function ExcluirCategoria({ categoria, outras, onFechar }) {
  const { recarregarOpcoes, dadosMudaram, avisar } = useDados()
  const usos = categoria.despesas + categoria.gastos
  const padrao = outras.find((c) => c.protegida) ?? outras[0]
  const [destino, setDestino] = useState(padrao ? String(padrao.id) : '')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  const excluir = async () => {
    setSalvando(true)
    setErro(null)
    try {
      await api.delete(`/categorias/${categoria.id}${usos ? `?mover_para=${destino}` : ''}`)
      avisar(usos ? 'Categoria excluída e lançamentos movidos' : 'Categoria excluída')
      recarregarOpcoes()
      dadosMudaram()
      onFechar()
    } catch (e) {
      setErro(e.message)
      setSalvando(false)
    }
  }

  return (
    <div className="space-y-6">
      {usos ? (
        <>
          <p className="text-sm text-suave">
            {usos} lançamento{usos > 1 ? 's usam' : ' usa'} esta categoria. Para onde {usos > 1 ? 'eles vão' : 'ele vai'}?
          </p>
          <Selecao rotulo="Mover para" opcoes={outras} value={destino} onChange={(e) => setDestino(e.target.value)} />
        </>
      ) : (
        <p className="text-sm text-suave">Nenhum lançamento usa esta categoria. Isso não pode ser desfeito.</p>
      )}
      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        <Botao variante="secundario" onClick={onFechar} className="flex-1">Cancelar</Botao>
        <Botao variante="perigo" onClick={excluir} carregando={salvando} disabled={usos > 0 && !destino} className="flex-1">
          <Trash2 className="size-4" /> Excluir
        </Botao>
      </div>
    </div>
  )
}
