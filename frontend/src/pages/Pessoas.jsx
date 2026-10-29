// Pessoas da casa: separam de quem é cada salário, conta e cartão.
// O que não tem pessoa fica no "Conjunto" (dinheiro e contas do casal).
import { useState } from 'react'
import { Pencil, Plus, Trash2, Users } from 'lucide-react'
import { api } from '../lib/api'
import { useDados } from '../contexts/DadosContext'
import { Botao, BotaoIcone, Campo, Cartao, MensagemErro, Modal, Titulo, Vazio } from '../components/ui'

export default function Pessoas() {
  const { opcoes } = useDados()
  const [editando, setEditando] = useState(null) // null | 'nova' | pessoa
  const { excluirPessoa } = useAcoes()

  return (
    <div className="space-y-6">
      <Titulo acao={<Botao onClick={() => setEditando('nova')}><Plus className="size-4" /> Pessoa</Botao>}>Pessoas da casa</Titulo>

      <Cartao>
        <p className="text-sm text-suave">
          Cadastre quem divide as finanças (ex.: você e sua esposa). Depois, em cada receita, conta, cartão ou comissão,
          escolha de quem é. O que ficar sem pessoa entra como <strong className="text-texto">Conjunto</strong> e, no
          Início, é dividido entre vocês proporcionalmente à renda de cada um.
        </p>
        <p className="mt-2 text-xs text-apagado">
          Gastos e contas no cartão sem pessoa escolhida contam para o dono do cartão.
        </p>
      </Cartao>

      {!opcoes.responsaveis.length && <Vazio>Nenhuma pessoa cadastrada.</Vazio>}
      <ul className="divide-y divide-borda overflow-hidden rounded-2xl border border-borda bg-painel">
        {opcoes.responsaveis.map((p) => (
          <li key={p.id} className="flex items-center gap-2 px-4">
            <Users className="size-5 text-suave" aria-hidden />
            <button onClick={() => setEditando(p)} className="min-h-14 flex-1 text-left">{p.nome}</button>
            <BotaoIcone rotulo={`Editar ${p.nome}`} onClick={() => setEditando(p)}><Pencil className="size-4" /></BotaoIcone>
            <BotaoIcone rotulo={`Excluir ${p.nome}`} onClick={() => excluirPessoa(p)} className="hover:text-negativo">
              <Trash2 className="size-4" />
            </BotaoIcone>
          </li>
        ))}
      </ul>

      <Modal aberto={editando !== null} titulo={editando === 'nova' ? 'Nova pessoa' : 'Editar pessoa'} onFechar={() => setEditando(null)}>
        {editando !== null && <FormPessoa pessoa={editando === 'nova' ? null : editando} onFechar={() => setEditando(null)} />}
      </Modal>
    </div>
  )
}

function useAcoes() {
  const { recarregarOpcoes, dadosMudaram, avisar, confirmar } = useDados()
  const excluirPessoa = async (p) => {
    const ok = await confirmar(`Excluir ${p.nome}? Nenhum lançamento é apagado: o que era dessa pessoa volta para o Conjunto.`)
    if (!ok) return
    try {
      await api.delete(`/responsaveis/${p.id}`)
      avisar('Excluído')
      recarregarOpcoes()
      dadosMudaram()
    } catch (e) {
      avisar(e.message)
    }
  }
  return { excluirPessoa }
}

function FormPessoa({ pessoa, onFechar }) {
  const { recarregarOpcoes, dadosMudaram, avisar } = useDados()
  const [nome, setNome] = useState(pessoa?.nome ?? '')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  const salvar = async (e) => {
    e.preventDefault()
    setSalvando(true)
    setErro(null)
    try {
      if (pessoa) await api.put(`/responsaveis/${pessoa.id}`, { nome })
      else await api.post('/responsaveis', { nome })
      avisar('Pessoa salva')
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
      <Campo rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={300} autoFocus placeholder="Ex.: Maria" />
      {erro && <MensagemErro mensagem={erro} />}
      <Botao type="submit" carregando={salvando} className="w-full">Salvar</Botao>
    </form>
  )
}
