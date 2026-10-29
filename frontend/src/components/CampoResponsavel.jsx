// De quem é cada receita/conta: uma das pessoas da casa ou "Conjunto".
// Sem pessoas cadastradas, o campo não aparece (tudo fica no Conjunto).
import { useDados } from '../contexts/DadosContext'
import { Opcoes } from './ui'

// Cor fixa por pessoa (ordem de cadastro), usada em todas as telas
const CORES_PESSOAS = ['#3987e5', '#d55181', '#c98500', '#9085e9', '#199e70', '#e66767']
const COR_CONJUNTO = '#8a91a0'

export default function CampoResponsavel({ rotulo = 'De quem é', vazio = 'Conjunto', valor, onChange }) {
  const { opcoes } = useDados()
  if (!opcoes.responsaveis.length) return null
  return (
    <Opcoes
      rotulo={rotulo}
      opcoes={[{ valor: '', rotulo: vazio }, ...opcoes.responsaveis.map((r) => ({ valor: r.id, rotulo: <MarcaPessoa id={r.id} /> }))]}
      valor={valor ?? ''}
      onChange={onChange}
    />
  )
}

// Nome, cor e responsável "efetivo" (conta no cartão sem pessoa = dono do cartão)
export function useResponsaveis() {
  const { opcoes } = useDados()
  const porCadastro = [...opcoes.responsaveis].sort((a, b) => a.id - b.id)
  const nome = (id) => opcoes.responsaveis.find((r) => r.id === id)?.nome ?? 'Conjunto'
  const cor = (id) => {
    const i = porCadastro.findIndex((r) => r.id === id)
    return i < 0 ? COR_CONJUNTO : CORES_PESSOAS[i % CORES_PESSOAS.length]
  }
  const doCartao = (cartaoId) => opcoes.cartoes.find((c) => c.id === cartaoId)?.responsavel_id ?? null
  const efetivo = (item) => item.responsavel_id ?? (item.cartao_id ? doCartao(item.cartao_id) : null)
  return { lista: opcoes.responsaveis, ativo: opcoes.responsaveis.length > 0, nome, cor, efetivo }
}

// Bolinha colorida + nome da pessoa (ou "Conjunto")
export function MarcaPessoa({ id, className = '' }) {
  const { nome, cor } = useResponsaveis()
  return (
    <span className={`inline-flex min-w-0 items-center gap-1.5 ${className}`}>
      <span className="size-2 shrink-0 rounded-full" style={{ background: cor(id) }} aria-hidden />
      <span className="truncate">{nome(id)}</span>
    </span>
  )
}

// Converte o valor do campo para o corpo da requisição
export const responsavelParaApi = (valor) => (valor === '' || valor == null ? null : Number(valor))
