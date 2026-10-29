// Lançamento RÁPIDO no cartão: valor, descrição, cartão e parcelas.
// "Todo mês" cria uma conta fixa no cartão (assinatura, serviço) que entra em toda fatura.
// Data (hoje) e categoria ficam recolhidas em "mais detalhes".
import { useEffect, useState } from 'react'
import { ChevronDown, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { hojeIso, lerValor, mesAno, valorParaCampo } from '../lib/formato'
import { useDados } from '../contexts/DadosContext'
import CampoResponsavel, { responsavelParaApi } from './CampoResponsavel'
import CampoCategoria from './CampoCategoria'
import { Botao, Campo, CampoValor, MensagemErro, Opcoes } from './ui'

const ULTIMO_CARTAO = 'ultimo-cartao'

function lerUltimoCartao() {
  try {
    return localStorage.getItem(ULTIMO_CARTAO)
  } catch {
    return null
  }
}

const TODO_MES = 'todo-mes'

// Mesma regra do servidor (mes_da_fatura): "AAAA-MM" do mês em que a fatura é paga
function mesDaFatura(iso, cartao) {
  if (!iso || !cartao) return null
  const [ano, mes, dia] = iso.split('-').map(Number)
  let indice = ano * 12 + (mes - 1)
  if (!cartao.dia_fechamento || !cartao.dia_vencimento) indice += 1
  else {
    const ultimo = new Date(ano, mes, 0).getDate()
    if (dia > Math.min(cartao.dia_fechamento, ultimo)) indice += 1
    if (cartao.dia_vencimento <= cartao.dia_fechamento) indice += 1
  }
  return `${Math.floor(indice / 12)}-${String((indice % 12) + 1).padStart(2, '0')}`
}

export default function FormGastoCartao({ gasto, cartaoInicial, fixaInicial = false, onSalvo, onExcluir }) {
  const { opcoes, dadosMudaram, avisar } = useDados()
  const [valor, setValor] = useState(valorParaCampo(gasto?.valor_total))
  const [descricao, setDescricao] = useState(gasto?.descricao ?? '')
  const [cartaoId, setCartaoId] = useState(gasto?.cartao_id ?? cartaoInicial ?? lerUltimoCartao() ?? '')
  const [parcelas, setParcelas] = useState(gasto?.num_parcelas ?? (fixaInicial ? TODO_MES : 1))
  const todoMes = parcelas === TODO_MES
  const [dataCompra, setDataCompra] = useState(gasto?.data_compra ?? hojeIso())
  const [categoriaId, setCategoriaId] = useState(gasto?.categoria_id ?? '')
  const [responsavelId, setResponsavelId] = useState(gasto?.responsavel_id ?? '')
  const [detalhes, setDetalhes] = useState(false)
  const cartaoEscolhido = opcoes.cartoes.find((c) => String(c.id) === String(cartaoId))
  const fatura = mesDaFatura(dataCompra, cartaoEscolhido)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  // Pré-seleciona o último cartão usado (ou o primeiro da lista)
  useEffect(() => {
    const ids = opcoes.cartoes.map((c) => String(c.id))
    if (opcoes.cartoes.length && !ids.includes(String(cartaoId))) setCartaoId(opcoes.cartoes[0].id)
  }, [opcoes.cartoes, cartaoId])

  const salvar = async (e) => {
    e.preventDefault()
    const numero = lerValor(valor)
    if (!numero || numero <= 0) return setErro('Informe um valor maior que zero.')
    if (!descricao.trim()) return setErro('Informe uma descrição.')
    setSalvando(true)
    setErro(null)
    const categoria = categoriaId ? Number(categoriaId) : null
    const corpo = {
      valor_total: numero,
      descricao,
      cartao_id: Number(cartaoId),
      num_parcelas: Number(parcelas) || 1,
      data_compra: dataCompra,
      categoria_id: categoria,
      responsavel_id: responsavelParaApi(responsavelId),
    }
    try {
      let salvo
      if (todoMes) {
        // Conta fixa no cartão: vira uma despesa fixa com o cartão como forma de pagamento
        salvo = await api.post(`/cartoes/${cartaoId}/contas-fixas`, {
          descricao,
          valor_mensal: numero,
          data_inicio: dataCompra,
          categoria_id: categoria,
          responsavel_id: responsavelParaApi(responsavelId),
        })
      } else {
        salvo = gasto
          ? await api.put(`/gastos-cartao/${gasto.id}`, corpo)
          : await api.post('/gastos-cartao', corpo)
      }
      try {
        localStorage.setItem(ULTIMO_CARTAO, String(cartaoId))
      } catch {
        /* armazenamento indisponível: só não lembra o cartão */
      }
      avisar(todoMes ? 'Conta fixa criada no cartão' : gasto ? 'Gasto atualizado' : 'Gasto lançado')
      dadosMudaram()
      onSalvo?.(salvo)
    } catch (e) {
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-4">
      <CampoValor rotulo={todoMes ? 'Valor por mês' : 'Valor total'} value={valor} onChange={(e) => setValor(e.target.value)} autoFocus={!gasto} required />
      <Campo rotulo="Descrição" value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder={todoMes ? 'Ex.: Netflix' : 'Ex.: Mercado'} required maxLength={300} />
      <Opcoes
        rotulo="Cartão"
        opcoes={opcoes.cartoes.map((c) => ({ valor: c.id, rotulo: c.nome }))}
        valor={cartaoId}
        onChange={setCartaoId}
      />
      {fatura && (
        <p className="-mt-2 text-xs text-apagado">
          {todoMes ? '1ª cobrança' : '1ª parcela'} na fatura de <span className="text-suave">{mesAno(fatura)}</span>
          {' · '}
          <button type="button" className="text-saldo underline" onClick={() => setDetalhes(true)}>mudar data</button>
        </p>
      )}
      <CampoResponsavel rotulo="De quem é" vazio="Dono do cartão" valor={responsavelId} onChange={setResponsavelId} />
      <div className="flex items-end gap-2">
        <Opcoes
          rotulo="Parcelas"
          opcoes={[
            ...[1, 2, 3, 6, 10, 12].map((n) => ({ valor: n, rotulo: `${n}x` })),
            // Conta fixa só na criação (gasto avulso existente continua parcelado)
            ...(gasto ? [] : [{ valor: TODO_MES, rotulo: '↻ Todo mês' }]),
          ]}
          valor={parcelas}
          onChange={setParcelas}
        />
        {!todoMes && (
          <Campo className="w-20" type="number" min={1} max={600} inputMode="numeric" value={parcelas} onChange={(e) => setParcelas(e.target.value)} aria-label="Outro número de parcelas" />
        )}
      </div>
      {todoMes && (
        <p className="-mt-2 text-xs text-apagado">
          Assinatura ou serviço que você não vai cancelar tão cedo: entra em toda fatura, sem data de fim.
          Para encerrar depois, edite em Despesas e informe "Cancelei em".
        </p>
      )}

      <button type="button" onClick={() => setDetalhes(!detalhes)} className="flex items-center gap-1 text-sm text-suave">
        <ChevronDown className={`size-4 transition ${detalhes ? 'rotate-180' : ''}`} /> Mais detalhes
      </button>
      {detalhes && (
        <div className="space-y-4">
          <Campo rotulo={todoMes ? 'Data da 1ª cobrança' : 'Data da compra'} type="date" value={dataCompra} onChange={(e) => setDataCompra(e.target.value)} required />
          <CampoCategoria vazio="Sem categoria" value={categoriaId} onChange={setCategoriaId} />
        </div>
      )}

      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {onExcluir && (
          <Botao type="button" variante="perigo" onClick={onExcluir}>
            <Trash2 className="size-4" /> Excluir
          </Botao>
        )}
        <Botao type="submit" carregando={salvando} className="flex-1">
          {gasto ? 'Salvar' : todoMes ? 'Criar conta fixa' : 'Lançar gasto'}
        </Botao>
      </div>
    </form>
  )
}
