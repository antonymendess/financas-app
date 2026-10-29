// Anotações: escrever rápido no topo, filtrar, concluir, editar e excluir.
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../lib/api'
import { useCarregar } from '../hooks/useCarregar'
import { useDados } from '../contexts/DadosContext'
import AnotacaoRapida from '../components/AnotacaoRapida'
import ItemAnotacao from '../components/ItemAnotacao'
import FormAnotacao from '../components/FormAnotacao'
import { Botao, Cartao, Carregando, MensagemErro, Modal, Opcoes, Selecao, Titulo, Vazio } from '../components/ui'

export default function Anotacoes() {
  const { versao } = useDados()
  const [status, setStatus] = useState('pendentes')
  const [pessoa, setPessoa] = useState('')
  const parametros = new URLSearchParams({ status, ...(pessoa && { pessoa }) })
  const { dados, carregando, erro, recarregar } = useCarregar(() => api.get(`/anotacoes?${parametros}`), [status, pessoa, versao], `/anotacoes?${parametros}`)
  const pessoas = useCarregar(() => api.get('/anotacoes/pessoas'), [versao], '/anotacoes/pessoas')
  const [editando, setEditando] = useState(null) // null | 'nova' | anotação

  const comData = (dados ?? []).filter((a) => a.data)
  const semData = (dados ?? []).filter((a) => !a.data)

  return (
    <div className="space-y-6">
      <Titulo acao={<Botao variante="secundario" onClick={() => setEditando('nova')}><Plus className="size-4" /> Com detalhes</Botao>}>
        Anotações
      </Titulo>

      <AnotacaoRapida autoFocus />

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <Opcoes
          opcoes={[
            { valor: 'pendentes', rotulo: 'Pendentes' },
            { valor: 'concluidas', rotulo: 'Concluídas' },
            { valor: 'todas', rotulo: 'Todas' },
          ]}
          valor={status}
          onChange={setStatus}
        />
        {pessoas.dados?.length > 0 && (
          <Selecao vazio="Todas as pessoas" opcoes={pessoas.dados} value={pessoa} onChange={(e) => setPessoa(e.target.value)} aria-label="Filtrar por pessoa" className="sm:w-56" />
        )}
      </div>

      {erro && <MensagemErro mensagem={erro} tentarNovamente={recarregar} />}
      {carregando && !dados && <Carregando />}
      {dados && !dados.length && <Vazio>{status === 'pendentes' ? 'Nada pendente. Escreva no campo acima para anotar.' : 'Nenhuma anotação.'}</Vazio>}

      {dados?.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {comData.length > 0 && (
            <Cartao titulo="Com data">
              <ul className="space-y-0.5">
                {comData.map((a) => <ItemAnotacao key={a.id} anotacao={a} onEditar={setEditando} />)}
              </ul>
            </Cartao>
          )}
          {semData.length > 0 && (
            <Cartao titulo="Sem data">
              <ul className="space-y-0.5">
                {semData.map((a) => <ItemAnotacao key={a.id} anotacao={a} onEditar={setEditando} />)}
              </ul>
            </Cartao>
          )}
        </div>
      )}

      <Modal aberto={editando !== null} titulo={editando === 'nova' ? 'Nova anotação' : 'Editar anotação'} onFechar={() => setEditando(null)}>
        {editando !== null && (
          <FormAnotacao anotacao={editando === 'nova' ? null : editando} pessoas={pessoas.dados ?? []} onSalvo={() => setEditando(null)} />
        )}
      </Modal>
    </div>
  )
}
