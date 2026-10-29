// Cliente da API: adiciona o token do Supabase em toda requisição
// e transforma erros em mensagens amigáveis.
import { supabase } from './supabase'

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export class ErroApi extends Error {
  constructor(mensagem, status) {
    super(mensagem)
    this.status = status
  }
}

async function requisitar(metodo, caminho, corpo, { publico = false } = {}) {
  // Rotas públicas (ex.: ver um convite antes de criar a conta) vão sem token
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token && !publico) {
    throw new ErroApi('Sessão encerrada. Entre novamente.', 401)
  }

  let resposta
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method: metodo,
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(corpo !== undefined && { 'Content-Type': 'application/json' }),
      },
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    })
  } catch {
    throw new ErroApi('Sem conexão com o servidor. Verifique sua internet.', 0)
  }

  if (resposta.status === 401 && !publico) {
    // Token expirado ou inválido: encerra a sessão e o app volta para o login
    await supabase.auth.signOut()
    throw new ErroApi('Sessão expirada. Entre novamente.', 401)
  }
  if (resposta.status === 204) return null

  const conteudo = await resposta.json().catch(() => null)
  if (!resposta.ok) {
    const mensagem =
      typeof conteudo?.detail === 'string'
        ? conteudo.detail
        : 'Algo deu errado. Tente novamente em instantes.'
    throw new ErroApi(mensagem, resposta.status)
  }
  return conteudo
}

export const api = {
  get: (caminho) => requisitar('GET', caminho),
  post: (caminho, corpo) => requisitar('POST', caminho, corpo),
  put: (caminho, corpo) => requisitar('PUT', caminho, corpo),
  patch: (caminho, corpo) => requisitar('PATCH', caminho, corpo),
  delete: (caminho) => requisitar('DELETE', caminho),
  publico: {
    get: (caminho) => requisitar('GET', caminho, undefined, { publico: true }),
  },
}
