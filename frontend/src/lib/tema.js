// Tema do app (claro, escuro ou o do sistema), lembrado neste aparelho.
import { useEffect, useState } from 'react'

const CHAVE = 'tema'
export const TEMAS = ['sistema', 'claro', 'escuro']
const COR_BARRA = { claro: '#fafafa', escuro: '#0a0a0a' }

export function lerTema() {
  try {
    const salvo = localStorage.getItem(CHAVE)
    return TEMAS.includes(salvo) ? salvo : 'sistema'
  } catch {
    return 'sistema'
  }
}

function temaEfetivo(tema) {
  if (tema !== 'sistema') return tema
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'claro' : 'escuro'
}

export function aplicarTema(tema) {
  const raiz = document.documentElement
  if (tema === 'sistema') delete raiz.dataset.tema
  else raiz.dataset.tema = tema
  // Cor da barra do navegador/celular acompanha o tema
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', COR_BARRA[temaEfetivo(tema)])
}

export function useTema() {
  const [tema, setTema] = useState(lerTema)
  useEffect(() => {
    aplicarTema(tema)
    try {
      localStorage.setItem(CHAVE, tema)
    } catch {
      /* armazenamento indisponível: vale só nesta visita */
    }
    if (tema !== 'sistema') return
    const consulta = window.matchMedia?.('(prefers-color-scheme: light)')
    const mudou = () => aplicarTema('sistema')
    consulta?.addEventListener('change', mudou)
    return () => consulta?.removeEventListener('change', mudou)
  }, [tema])
  return [tema, setTema]
}
