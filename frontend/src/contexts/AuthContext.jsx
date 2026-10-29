// Guarda a sessão do usuário e avisa o app quando ela muda (login, logout, expiração).
import { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { limparMemoria } from '../hooks/useCarregar'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [sessao, setSessao] = useState(undefined) // undefined = ainda verificando

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSessao(data.session))
    const { data } = supabase.auth.onAuthStateChange((_evento, novaSessao) => {
      if (!novaSessao) limparMemoria() // saiu da conta
      setSessao(novaSessao)
    })
    return () => data.subscription.unsubscribe()
  }, [])

  const entrar = async (email, senha) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password: senha })
    if (error) {
      throw new Error(
        error.message === 'Invalid login credentials'
          ? 'E-mail ou senha incorretos.'
          : 'Não foi possível entrar. Tente novamente.',
      )
    }
  }

  const sair = () => {
    limparMemoria()
    return supabase.auth.signOut()
  }

  // Cadastro só acontece pela tela do convite. Se o Supabase exigir confirmação de
  // e-mail, a sessão vem vazia e o link do e-mail traz a pessoa de volta ao convite.
  const criarConta = async (email, senha, voltarPara) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password: senha,
      options: { emailRedirectTo: voltarPara },
    })
    if (error) {
      throw new Error(
        /already registered/i.test(error.message)
          ? 'Esse e-mail já tem conta. Use "Já tenho conta".'
          : /password/i.test(error.message)
            ? 'Senha fraca: use pelo menos 8 caracteres.'
            : 'Não foi possível criar a conta. Tente novamente.',
      )
    }
    return { precisaConfirmar: !data.session }
  }

  return (
    <AuthContext.Provider value={{ sessao, entrar, sair, criarConta }}>{children}</AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
