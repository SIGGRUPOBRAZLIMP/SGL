import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getEdital, extrairItensAI, classificarEdital, resumirEdital, decidirTriagem } from '../services/api'
import { ArrowLeft, Brain, FileText, Tag, Sparkles, CheckCircle, XCircle, Loader2 } from 'lucide-react'

export default function EditalDetalhe() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [edital, setEdital] = useState(null)
  const [loading, setLoading] = useState(true)
  const [aiLoading, setAiLoading] = useState('')
  const [aiResult, setAiResult] = useState(null)
  const [aiError, setAiError] = useState('')

  useEffect(() => {
    loadEdital()
  }, [id])

  const loadEdital = async () => {
    try {
      const r = await getEdital(id)
      setEdital(r.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleExtrairItens = async () => {
    setAiLoading('extrair')
    setAiError('')
    setAiResult(null)
    try {
      const r = await extrairItensAI(id)
      setAiResult({ tipo: 'itens', data: r.data })
    } catch (err) {
      setAiError(err.response?.data?.error || 'Erro na extração AI')
    } finally {
      setAiLoading('')
    }
  }

  const handleClassificar = async () => {
    setAiLoading('classificar')
    setAiError('')
    setAiResult(null)
    try {
      const r = await classificarEdital(id, ['material_escritorio', 'informatica', 'limpeza', 'alimentacao', 'construcao', 'veiculos', 'mobiliario'])
      setAiResult({ tipo: 'classificacao', data: r.data })
    } catch (err) {
      setAiError(err.response?.data?.error || 'Erro na classificação AI')
    } finally {
      setAiLoading('')
    }
  }

  const handleResumir = async () => {
    setAiLoading('resumir')
    setAiError('')
    setAiResult(null)
    try {
      const r = await resumirEdital(id)
      setAiResult({ tipo: 'resumo', data: r.data })
    } catch (err) {
      setAiError(err.response?.data?.error || 'Erro no resumo AI')
    } finally {
      setAiLoading('')
    }
  }

  const handleTriagem = async (decisao) => {
    try {
      await decidirTriagem(id, { decisao, prioridade: 'media' })
      loadEdital()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="flex items-center justify-center py-20"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div></div>
  if (!edital) return <div className="text-center py-20 text-gray-400">Edital não encontrado</div>

  return (
    <div>
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={18} /> Voltar
      </button>

      {/* Header */}
      <div className="card mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 mb-1">{edital.orgao_razao_social}</h1>
            <p className="text-gray-600 mb-3">{edital.objeto_resumo || edital.objeto_completo || 'Sem descrição'}</p>
            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
              {edital.numero_controle_pncp && <span><strong>PNCP:</strong> {edital.numero_controle_pncp}</span>}
              {edital.uf && <span><strong>UF:</strong> {edital.uf}</span>}
              {edital.municipio && <span><strong>Município:</strong> {edital.municipio}</span>}
              {edital.modalidade_nome && <span><strong>Modalidade:</strong> {edital.modalidade_nome}</span>}
              {edital.plataforma_origem && <span><PlataformaBadge plataforma={edital.plataforma_origem} /></span>}
              {edital.srp !== null && <span><strong>SRP:</strong> {edital.srp ? 'Sim' : 'Não'}</span>}
            </div>
          </div>
          <div className="text-right">
            {edital.valor_estimado && (
              <p className="text-2xl font-bold text-primary-600">
                R$ {Number(edital.valor_estimado).toLocaleString('pt-BR')}
              </p>
            )}
            <StatusBadge status={edital.status} />
          </div>
        </div>

        {/* Datas */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-4 border-t border-gray-100">
          <DateInfo label="Publicação" date={edital.data_publicacao} />
          <DateInfo label="Abertura Propostas" date={edital.data_abertura_proposta} />
          <DateInfo label="Encerramento" date={edital.data_encerramento_proposta} />
          <DateInfo label="Certame" date={edital.data_certame} />
        </div>
      </div>

      {/* Ações de Triagem */}
      {edital.status === 'captado' && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Triagem</h2>
          <div className="flex gap-3">
            <button onClick={() => handleTriagem('aprovado')} className="btn-success flex items-center gap-2">
              <CheckCircle size={18} /> Aprovar
            </button>
            <button onClick={() => handleTriagem('rejeitado')} className="btn-danger flex items-center gap-2">
              <XCircle size={18} /> Rejeitar
            </button>
          </div>
        </div>
      )}

      {/* Ações AI */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Brain size={20} className="text-primary-600" />
          Inteligência Artificial (Claude)
        </h2>
        <p className="text-sm text-gray-500 mb-4">Use a IA para analisar este edital automaticamente</p>

        <div className="flex flex-wrap gap-3">
          <button onClick={handleExtrairItens} disabled={!!aiLoading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {aiLoading === 'extrair' ? <Loader2 size={18} className="animate-spin" /> : <FileText size={18} />}
            Extrair Itens
          </button>
          <button onClick={handleClassificar} disabled={!!aiLoading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {aiLoading === 'classificar' ? <Loader2 size={18} className="animate-spin" /> : <Tag size={18} />}
            Classificar Relevância
          </button>
          <button onClick={handleResumir} disabled={!!aiLoading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {aiLoading === 'resumir' ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />}
            Resumo Executivo
          </button>
        </div>

        {aiError && (
          <div className="mt-4 p-4 bg-danger-50 text-danger-700 rounded-lg text-sm">
            {aiError}
          </div>
        )}

        {aiResult && (
          <div className="mt-4 p-4 bg-primary-50 rounded-lg">
            {aiResult.tipo === 'itens' && (
              <div>
                <h3 className="font-semibold text-primary-900 mb-2">Itens Extraídos ({aiResult.data.total_itens || 0})</h3>
                {aiResult.data.itens?.map((item, i) => (
                  <div key={i} className="flex justify-between items-center py-2 border-b border-primary-100 last:border-0 text-sm">
                    <div>
                      <span className="text-gray-500 mr-2">#{item.numero_item || i + 1}</span>
                      <span className="text-gray-900">{item.descricao?.substring(0, 80)}</span>
                    </div>
                    <div className="text-right text-gray-600">
                      {item.quantidade} {item.unidade_compra} — R$ {item.preco_unitario_maximo}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {aiResult.tipo === 'classificacao' && (
              <div>
                <h3 className="font-semibold text-primary-900 mb-2">Classificação de Relevância</h3>
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">{JSON.stringify(aiResult.data, null, 2)}</pre>
              </div>
            )}
            {aiResult.tipo === 'resumo' && (
              <div>
                <h3 className="font-semibold text-primary-900 mb-2">Resumo Executivo</h3>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{aiResult.data.resumo || JSON.stringify(aiResult.data, null, 2)}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Objeto Completo */}
      {edital.objeto_completo && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Objeto Completo</h2>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{edital.objeto_completo}</p>
        </div>
      )}
    </div>
  )
}

function DateInfo({ label, date }) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-medium text-gray-700">
        {date ? new Date(date).toLocaleDateString('pt-BR') : '—'}
      </p>
    </div>
  )
}

function StatusBadge({ status }) {
  const styles = {
    captado: 'bg-blue-100 text-blue-700',
    aprovado: 'bg-green-100 text-green-700',
    rejeitado: 'bg-red-100 text-red-700',
    em_processo: 'bg-yellow-100 text-yellow-700',
  }
  return <span className={`badge mt-2 ${styles[status] || 'bg-gray-100 text-gray-700'}`}>{status || 'captado'}</span>
}

const PLATAFORMA_CONFIG = {
  pncp:            { label: 'PNCP',     bg: 'bg-blue-100',   text: 'text-blue-700' },
  bbmnet:          { label: 'BBMNET',   bg: 'bg-green-100',  text: 'text-green-700' },
  licitardigital:  { label: 'Licitar Digital', bg: 'bg-purple-100', text: 'text-purple-700' },
  comprasgov:      { label: 'ComprasGov', bg: 'bg-orange-100', text: 'text-orange-700' },
}

function PlataformaBadge({ plataforma }) {
  const config = PLATAFORMA_CONFIG[plataforma] || { label: plataforma || '—', bg: 'bg-gray-100', text: 'text-gray-600' }
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  )
}
