/**
 * StatusBadge — Componente compartilhado para exibir status
 * Usado em: Dashboard, Editais, EditalDetalhe, Triagem, Processos
 */

const STATUS_CONFIG = {
  // Editais
  captado:       { label: 'Captado',        bg: 'bg-blue-100',   text: 'text-blue-700' },
  aprovado:      { label: 'Aprovado',       bg: 'bg-green-100',  text: 'text-green-700' },
  rejeitado:     { label: 'Rejeitado',      bg: 'bg-red-100',    text: 'text-red-700' },
  em_processo:   { label: 'Em Processo',    bg: 'bg-yellow-100', text: 'text-yellow-700' },
  em_disputa:    { label: 'Em Disputa',     bg: 'bg-purple-100', text: 'text-purple-700' },
  ganho:         { label: 'Ganho',          bg: 'bg-emerald-100',text: 'text-emerald-700' },
  perdido:       { label: 'Perdido',        bg: 'bg-gray-100',   text: 'text-gray-700' },
  cancelado:     { label: 'Cancelado',      bg: 'bg-gray-100',   text: 'text-gray-500' },

  // Processos
  montagem:      { label: 'Montagem',       bg: 'bg-blue-100',   text: 'text-blue-700' },
  cotacao:       { label: 'Cotação',        bg: 'bg-orange-100', text: 'text-orange-700' },
  viabilidade:   { label: 'Viabilidade',    bg: 'bg-yellow-100', text: 'text-yellow-700' },
  pronto:        { label: 'Pronto p/ Disputa', bg: 'bg-indigo-100', text: 'text-indigo-700' },
  concluido:     { label: 'Concluído',      bg: 'bg-green-100',  text: 'text-green-700' },

  // Prioridade
  alta:          { label: 'Alta',           bg: 'bg-red-100',    text: 'text-red-700' },
  media:         { label: 'Média',          bg: 'bg-yellow-100', text: 'text-yellow-700' },
  baixa:         { label: 'Baixa',          bg: 'bg-gray-100',   text: 'text-gray-600' },
  urgente:       { label: 'Urgente',        bg: 'bg-red-200',    text: 'text-red-800' },
}

export default function StatusBadge({ status, className = '' }) {
  const config = STATUS_CONFIG[status] || { label: status || '—', bg: 'bg-gray-100', text: 'text-gray-700' }
  return (
    <span className={`badge ${config.bg} ${config.text} ${className}`}>
      {config.label}
    </span>
  )
}

export function PrioridadeBadge({ prioridade, className = '' }) {
  return <StatusBadge status={prioridade} className={className} />
}
