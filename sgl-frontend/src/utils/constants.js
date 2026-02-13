/**
 * Constantes compartilhadas do SGL
 * Centralizadas para evitar duplicação entre páginas
 */

export const UFS = [
  'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT',
  'PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO'
]

export const REGIOES = {
  'Norte':        ['AC','AM','AP','PA','RO','RR','TO'],
  'Nordeste':     ['AL','BA','CE','MA','PB','PE','PI','RN','SE'],
  'Centro-Oeste': ['DF','GO','MS','MT'],
  'Sudeste':      ['ES','MG','RJ','SP'],
  'Sul':          ['PR','RS','SC'],
}

export const MODALIDADES = [
  { id: 8,  nome: 'Pregão Eletrônico' },
  { id: 6,  nome: 'Pregão Presencial' },
  { id: 4,  nome: 'Concorrência Eletrônica' },
  { id: 5,  nome: 'Concorrência Presencial' },
  { id: 7,  nome: 'Dispensa de Licitação' },
  { id: 1,  nome: 'Leilão Eletrônico' },
  { id: 9,  nome: 'Leilão Presencial' },
  { id: 2,  nome: 'Diálogo Competitivo' },
  { id: 3,  nome: 'Concurso' },
  { id: 12, nome: 'Credenciamento' },
  { id: 13, nome: 'Pré-qualificação' },
]

export const STATUS_EDITAL = [
  { value: 'captado',     label: 'Captado' },
  { value: 'aprovado',    label: 'Aprovado' },
  { value: 'rejeitado',   label: 'Rejeitado' },
  { value: 'em_processo', label: 'Em Processo' },
  { value: 'em_disputa',  label: 'Em Disputa' },
  { value: 'ganho',       label: 'Ganho' },
  { value: 'perdido',     label: 'Perdido' },
  { value: 'cancelado',   label: 'Cancelado' },
]

export const STATUS_PROCESSO = [
  { value: 'montagem',     label: 'Montagem' },
  { value: 'cotacao',      label: 'Cotação' },
  { value: 'viabilidade',  label: 'Viabilidade' },
  { value: 'pronto',       label: 'Pronto p/ Disputa' },
  { value: 'em_disputa',   label: 'Em Disputa' },
  { value: 'ganho',        label: 'Ganho' },
  { value: 'perdido',      label: 'Perdido' },
  { value: 'concluido',    label: 'Concluído' },
  { value: 'cancelado',    label: 'Cancelado' },
]

export const PRIORIDADES = [
  { value: 'urgente', label: 'Urgente' },
  { value: 'alta',    label: 'Alta' },
  { value: 'media',   label: 'Média' },
  { value: 'baixa',   label: 'Baixa' },
]

export const SEGMENTOS = [
  'Material de Escritório',
  'Informática',
  'Limpeza e Higiene',
  'Alimentação',
  'Mobiliário',
  'Veículos e Peças',
  'Material de Construção',
  'Equipamentos Médicos',
  'Material Elétrico',
  'Uniformes e EPIs',
  'Medicamentos',
  'Material Gráfico',
  'Outros',
]

// Formatar valor em R$
export const formatCurrency = (value) => {
  if (!value && value !== 0) return '—'
  return `R$ ${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
}

// Formatar data
export const formatDate = (date) => {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('pt-BR')
}

// Formatar data e hora
export const formatDateTime = (date) => {
  if (!date) return '—'
  return new Date(date).toLocaleString('pt-BR')
}
