// Link de convite (/convite/TOKEN): mostra para quem é, cria a conta ou entra,
// e liga o login à casa. Funciona antes do login (é a porta de entrada de quem é novo).
import { useEffect, useState } from 'react'
import { CheckCircle2, Mail } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { Abas, Botao, Campo, Carregando, MensagemErro } from '../components/ui'

export default function Convite({ token }) {
  const { sessao, entrar, sair, criarConta } = useAuth()
  const [info, setInfo] = useState(null)
  const [erroInfo, setErroInfo] = useState(null)
  const [aba, setAba] = useState('criar')
  const [senha, setSenha] = useState('')
  const [senha2, setSenha2] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState(null)
  const [aguardandoEmail, setAguardandoEmail] = useState(false)

  useEffect(() => {
    api.publico.get(`/convites/${encodeURIComponent(token)}`).then(setInfo).catch((e) => setErroInfo(e.message))
  }, [token])

  const aceitar = async () => {
    setEnviando(true)
    setErro(null)
    try {
      await api.post(`/convites/${encodeURIComponent(token)}/aceitar`)
      window.location.replace('/') // recarrega já dentro da casa
    } catch (e) {
      setErro(e.message)
      setEnviando(false)
    }
  }

  const enviar = async (e) => {
    e.preventDefault()
    setErro(null)
    if (aba === 'criar' && senha.length < 8) return setErro('Use uma senha com pelo menos 8 caracteres.')
    if (aba === 'criar' && senha !== senha2) return setErro('As senhas não são iguais.')
    setEnviando(true)
    try {
      if (aba === 'criar') {
        const { precisaConfirmar } = await criarConta(info.email, senha, window.location.href)
        if (precisaConfirmar) setAguardandoEmail(true)
      } else {
        await entrar(info.email, senha)
      }
    } catch (e) {
      setErro(e.message)
    } finally {
      setEnviando(false)
    }
  }

  const titulo = info?.tipo === 'membro'
    ? `Você foi convidado para a casa "${info.nome_casa}"`
    : 'Você foi convidado para o Controle Financeiro'

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-6 py-10">
      <img src="/icon.svg" alt="" className="mb-6 size-16" />
      {erroInfo && <MensagemErro mensagem={erroInfo} />}
      {!info && !erroInfo && <Carregando />}

      {info && (
        <>
          <h1 className="text-2xl font-bold">{titulo}</h1>
          <p className="mt-2 mb-6 text-suave">
            {info.tipo === 'membro'
              ? 'Vocês vão ver e organizar as mesmas finanças.'
              : info.nome_casa ? `Sua conta "${info.nome_casa}" fica pronta assim que você entrar.` : 'Sua conta fica pronta assim que você entrar.'}
          </p>

          {info.situacao !== 'pendente' ? (
            <MensagemErro mensagem={info.situacao === 'aceito' ? 'Esse convite já foi usado. Entre normalmente pela tela de login.' : 'Esse convite expirou. Peça um novo para quem te convidou.'} />
          ) : sessao ? (
            sessao.user.email?.toLowerCase() === info.email ? (
              <div className="space-y-4">
                <p className="flex items-center gap-2 rounded-xl bg-painel p-3 text-sm">
                  <CheckCircle2 className="size-4 text-positivo" aria-hidden /> Conectado como {info.email}
                </p>
                {erro && <MensagemErro mensagem={erro} />}
                <Botao onClick={aceitar} carregando={enviando} className="w-full">Aceitar convite e entrar</Botao>
              </div>
            ) : (
              <div className="space-y-4">
                <MensagemErro mensagem={`Este convite é para ${info.email}, mas você está conectado como ${sessao.user.email}.`} />
                <Botao variante="secundario" onClick={sair} className="w-full">Sair e entrar com {info.email}</Botao>
              </div>
            )
          ) : aguardandoEmail ? (
            <div className="space-y-2 rounded-2xl border border-borda bg-painel-2/60 p-4 text-sm">
              <p className="flex items-center gap-2 font-medium"><Mail className="size-4 text-saldo" aria-hidden /> Confirme seu e-mail</p>
              <p className="text-suave">
                Enviamos um link para <strong className="text-texto">{info.email}</strong>. Abra o e-mail e toque no link:
                você volta para esta página para aceitar o convite.
              </p>
            </div>
          ) : (
            <form onSubmit={enviar} className="space-y-4">
              <Abas abas={[{ valor: 'criar', rotulo: 'Criar conta' }, { valor: 'entrar', rotulo: 'Já tenho conta' }]} ativa={aba} onChange={setAba} />
              <Campo rotulo="E-mail" type="email" value={info.email} readOnly />
              <Campo rotulo="Senha" type="password" autoComplete={aba === 'criar' ? 'new-password' : 'current-password'} value={senha} onChange={(e) => setSenha(e.target.value)} required autoFocus />
              {aba === 'criar' && (
                <Campo rotulo="Repita a senha" type="password" autoComplete="new-password" value={senha2} onChange={(e) => setSenha2(e.target.value)} required />
              )}
              {erro && <MensagemErro mensagem={erro} />}
              <Botao type="submit" carregando={enviando} className="w-full">{aba === 'criar' ? 'Criar conta' : 'Entrar'}</Botao>
            </form>
          )}
        </>
      )}
    </main>
  )
}
