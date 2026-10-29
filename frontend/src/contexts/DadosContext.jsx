// Dados compartilhados: listas dos formulários, aviso rápido e sinal de atualização.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { api } from '../lib/api'
import { Botao, Modal } from '../components/ui'

const DadosContext = createContext(null)

export function DadosProvider({ children, eu = null, recarregarEu = () => {} }) {
  const [opcoes, setOpcoes] = useState({ categorias: [], formas_pagamento: [], cartoes: [], responsaveis: [] })
  const [versao, setVersao] = useState(0) // muda quando algo é salvo -> telas recarregam
  const [aviso, setAviso] = useState(null)
  const [pergunta, setPergunta] = useState(null) // confirmação aberta
  const resolver = useRef(null)

  // Devolve a promessa para quem precisa esperar a lista nova (ex.: categoria recém-criada)
  const recarregarOpcoes = useCallback(() => api.get('/opcoes').then(setOpcoes).catch(() => {}), [])

  useEffect(() => {
    recarregarOpcoes()
  }, [recarregarOpcoes])

  const temporizador = useRef(null)
  const avisar = useCallback((texto) => {
    // Cada aviso novo reinicia o tempo (um aviso antigo não apaga o novo)
    clearTimeout(temporizador.current)
    setAviso(texto)
    temporizador.current = setTimeout(() => setAviso(null), 2500)
  }, [])

  const dadosMudaram = useCallback(() => setVersao((v) => v + 1), [])

  // Pergunta de confirmação (ex.: excluir). Uso: if (await confirmar('...')) {...}
  const confirmar = useCallback((mensagem, textoBotao = 'Excluir') => {
    setPergunta({ mensagem, textoBotao })
    return new Promise((resolve) => {
      resolver.current = resolve
    })
  }, [])

  const responder = (resposta) => {
    resolver.current?.(resposta)
    setPergunta(null)
  }

  // Exclui com confirmação, avisa e atualiza as telas
  const excluir = useCallback(
    async (caminho, descricao) => {
      if (!(await confirmar(`Excluir ${descricao}? Isso não pode ser desfeito.`))) return false
      try {
        await api.delete(caminho)
      } catch (e) {
        avisar(e.message) // ex.: cartão com gastos lançados
        return false
      }
      avisar('Excluído')
      dadosMudaram()
      return true
    },
    [confirmar, avisar, dadosMudaram],
  )

  return (
    <DadosContext.Provider
      value={{ opcoes, recarregarOpcoes, versao, dadosMudaram, avisar, confirmar, excluir, eu, recarregarEu }}
    >
      {children}
      <Modal aberto={pergunta !== null} titulo="Confirmar" onFechar={() => responder(false)}>
        <p className="mb-5 text-suave">{pergunta?.mensagem}</p>
        <div className="flex gap-2">
          <Botao variante="secundario" className="flex-1" onClick={() => responder(false)}>
            Cancelar
          </Botao>
          <Botao variante="perigo" className="flex-1" onClick={() => responder(true)} autoFocus>
            {pergunta?.textoBotao}
          </Botao>
        </div>
      </Modal>
      {aviso && (
        <div
          className="fixed inset-x-4 bottom-[calc(6rem+env(safe-area-inset-bottom))] z-[60] mx-auto flex max-w-sm items-center gap-2 rounded-xl border border-borda bg-painel-2 px-4 py-3 text-sm shadow-lg lg:inset-x-auto lg:right-8 lg:bottom-8"
          role="status"
        >
          <CheckCircle2 className="size-4 text-positivo" aria-hidden />
          {aviso}
        </div>
      )}
    </DadosContext.Provider>
  )
}

export const useDados = () => useContext(DadosContext)
