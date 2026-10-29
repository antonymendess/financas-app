// Tela de login (e-mail e senha do Supabase Auth). Conta nova só pelo link de convite.
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Botao, Campo, MensagemErro } from '../components/ui'

export default function Login() {
  const { entrar } = useAuth()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      await entrar(email.trim(), senha)
    } catch (e) {
      setErro(e.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-6">
      <img src="/icon.svg" alt="" className="mb-8 size-11" />
      <h1 className="text-2xl font-semibold tracking-tight">Controle Financeiro</h1>
      <p className="mt-1 mb-10 text-sm text-suave">Entre para continuar</p>
      <form onSubmit={enviar} className="space-y-4">
        <Campo rotulo="E-mail" type="email" autoComplete="email" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Campo rotulo="Senha" type="password" autoComplete="current-password" value={senha} onChange={(e) => setSenha(e.target.value)} required />
        {erro && <MensagemErro mensagem={erro} />}
        <Botao type="submit" carregando={enviando} className="w-full">
          Entrar
        </Botao>
      </form>
      <p className="mt-6 text-center text-sm text-apagado">
        Recebeu um convite? Abra o link do convite para criar sua conta.
      </p>
    </main>
  )
}
