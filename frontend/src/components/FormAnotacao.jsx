// Anotação rápida: só o texto é obrigatório; o resto fica em "mais detalhes".
import { useState } from 'react'
import { ChevronDown, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { lerValor, valorParaCampo } from '../lib/formato'
import { useDados } from '../contexts/DadosContext'
import { AreaTexto, Botao, Campo, CampoValor, Interruptor, MensagemErro, Opcoes } from './ui'

export default function FormAnotacao({ anotacao, onSalvo, pessoas = [] }) {
  const { dadosMudaram, avisar, excluir } = useDados()
  const [texto, setTexto] = useState(anotacao?.texto ?? '')
  const [tipo, setTipo] = useState(anotacao?.tipo ?? 'Lembrete')
  const [dataAnot, setDataAnot] = useState(anotacao?.data ?? '')
  const [valor, setValor] = useState(valorParaCampo(anotacao?.valor))
  const [pessoa, setPessoa] = useState(anotacao?.pessoa ?? '')
  const [entraNoSaldo, setEntraNoSaldo] = useState(anotacao?.entra_no_saldo ?? false)
  const [detalhes, setDetalhes] = useState(
    Boolean(anotacao && (anotacao.data || anotacao.valor || anotacao.pessoa || anotacao.tipo !== 'Lembrete')),
  )
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  const salvar = async (e) => {
    e.preventDefault()
    if (!texto.trim()) return setErro('Escreva a anotação.')
    const numero = lerValor(valor)
    if (Number.isNaN(numero) || (numero !== null && numero <= 0)) return setErro('Valor inválido.')
    setSalvando(true)
    setErro(null)
    const corpo = {
      texto,
      tipo,
      data: dataAnot || null,
      valor: numero,
      pessoa: pessoa || null,
      entra_no_saldo: tipo !== 'Lembrete' && entraNoSaldo,
      concluida: anotacao?.concluida ?? false,
    }
    try {
      const salva = anotacao
        ? await api.put(`/anotacoes/${anotacao.id}`, corpo)
        : await api.post('/anotacoes', corpo)
      avisar(anotacao ? 'Anotação atualizada' : 'Anotação criada')
      dadosMudaram()
      onSalvo?.(salva)
    } catch (e) {
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  const podeEntrarNoSaldo = tipo !== 'Lembrete'

  return (
    <form onSubmit={salvar} className="space-y-4">
      <AreaTexto
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder="Ex.: pagar fulano dia 20"
        autoFocus={!anotacao}
        maxLength={300}
        aria-label="Anotação"
      />

      <button type="button" onClick={() => setDetalhes(!detalhes)} className="flex items-center gap-1 text-sm text-suave">
        <ChevronDown className={`size-4 transition ${detalhes ? 'rotate-180' : ''}`} /> Mais detalhes
      </button>
      {detalhes && (
        <div className="space-y-4">
          <Opcoes rotulo="Tipo" opcoes={['Lembrete', 'A pagar', 'A receber']} valor={tipo} onChange={setTipo} />
          <div className="grid grid-cols-2 gap-3">
            <Campo rotulo="Data" type="date" value={dataAnot} onChange={(e) => setDataAnot(e.target.value)} />
            <CampoValor rotulo="Valor" value={valor} onChange={(e) => setValor(e.target.value)} />
          </div>
          <Campo rotulo="Pessoa" value={pessoa} onChange={(e) => setPessoa(e.target.value)} list="lista-pessoas" maxLength={120} />
          <datalist id="lista-pessoas">
            {pessoas.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
          {podeEntrarNoSaldo && (
            <Interruptor
              rotulo="Somar no saldo do mês"
              dica={dataAnot && valor ? 'Entra como despesa/receita no mês da data' : 'Precisa de data e valor'}
              checked={entraNoSaldo}
              onChange={setEntraNoSaldo}
            />
          )}
        </div>
      )}

      {erro && <MensagemErro mensagem={erro} />}
      <div className="flex gap-2">
        {anotacao && (
          <Botao
            type="button"
            variante="perigo"
            onClick={async () => (await excluir(`/anotacoes/${anotacao.id}`, 'esta anotação')) && onSalvo?.()}
          >
            <Trash2 className="size-4" /> Excluir
          </Botao>
        )}
        <Botao type="submit" carregando={salvando} className="flex-1">
          Salvar
        </Botao>
      </div>
    </form>
  )
}
