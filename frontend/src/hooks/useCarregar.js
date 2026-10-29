// Carrega dados da API e expõe estados de carregamento e erro.
//
// Com `chave` (normalmente o endereço da API), a última resposta fica guardada na
// memória: ao voltar para uma tela, os dados aparecem na hora e são atualizados por
// trás (a tela fica levemente apagada enquanto `carregando`).
import { useCallback, useEffect, useState } from 'react'

const memoria = new Map() // chave -> última resposta

// Ao sair da conta, nada do usuário anterior pode aparecer para o próximo
export function limparMemoria() {
  memoria.clear()
}

export function useCarregar(funcao, dependencias = [], chave = null) {
  const [dados, setDadosLocal] = useState(() => (chave ? memoria.get(chave) ?? null : null))
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState(null)

  // Atualizações otimistas da tela também atualizam a memória
  const setDados = useCallback(
    (valor) =>
      setDadosLocal((atual) => {
        const novo = typeof valor === 'function' ? valor(atual) : valor
        if (chave) memoria.set(chave, novo)
        return novo
      }),
    [chave],
  )

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const executar = useCallback(funcao, dependencias)

  const recarregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      setDados(await executar())
    } catch (e) {
      setErro(e.message)
    } finally {
      setCarregando(false)
    }
  }, [executar, setDados])

  useEffect(() => {
    let ativo = true
    // Trocou de mês/filtro: mostra na hora o que já estava guardado para ele
    if (chave && memoria.has(chave)) setDadosLocal(memoria.get(chave))
    setCarregando(true)
    setErro(null)
    executar()
      .then((resultado) => ativo && setDados(resultado))
      .catch((e) => ativo && setErro(e.message))
      .finally(() => ativo && setCarregando(false))
    return () => {
      ativo = false // ignora respostas de uma navegação anterior
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executar])

  return { dados, carregando, erro, recarregar, setDados }
}
