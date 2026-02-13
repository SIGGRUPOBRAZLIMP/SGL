# SGL — Sistema de Gestão de Licitações

Sistema completo para gestão do ciclo de vida de licitações públicas, desde a captação automática de editais até o pós-venda, com integração futura ao SIG (Sistema Integrado de Gestão) do Grupo Braz.

## Stack Tecnológica

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.11+ / Flask |
| Banco de Dados | PostgreSQL 15+ |
| ORM | SQLAlchemy + Alembic (migrations) |
| Autenticação | JWT (Flask-JWT-Extended) |
| AI / LLM | Claude API (Anthropic) — extração inteligente de editais |
| Filas | Celery + Redis |
| Storage | Cloudinary |
| PDF | pdfplumber + PyMuPDF + Tesseract OCR |

## Módulos

1. **Captação** — Busca automática no PNCP + scraping de plataformas
2. **Triagem** — Aprovação/rejeição de editais com pré-classificação AI
3. **Processos** — Distribuição e acompanhamento (Kanban)
4. **Cotação** — Planilha interativa com múltiplos fornecedores
5. **Análise de Viabilidade** — Cálculo automático de margem e aprovação
6. **Disputa** — Apoio à participação nos pregões
7. **Pós-Venda** — Planilha reajustada + integração SIG

## Endpoints Principais da API

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/login` | Autenticação |
| GET | `/api/editais` | Listar editais com filtros |
| POST | `/api/editais/captar` | Executar captação PNCP |
| POST | `/api/editais/:id/extrair-itens` | **Extração AI de itens** |
| POST | `/api/editais/:id/classificar` | **Classificação AI de relevância** |
| POST | `/api/editais/:id/resumir` | **Resumo AI do edital** |
| GET/PUT | `/api/triagem` | Gestão de triagem |
| CRUD | `/api/fornecedores` | Gestão de fornecedores |
| CRUD | `/api/processos` | Gestão de processos |
| POST | `/api/processos/:id/importar-itens-ai` | Importar itens AI → cotação |
| POST | `/api/processos/:id/analisar-viabilidade` | Análise automática |
| GET | `/api/dashboard/stats` | Estatísticas gerais |

## Setup

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# 3. Criar banco de dados
createdb sgl_db

# 4. Iniciar aplicação
python run.py

# 5. (Opcional) Iniciar Celery worker
celery -A sgl.tasks worker --loglevel=info
```

## Fontes de Dados

| Prioridade | Fonte | Método |
|:---:|---|---|
| 1 | **PNCP** (Portal Nacional) | API REST pública |
| 2 | **Compras.gov.br** | API REST pública |
| 3 | Alertas BLL/BNC por e-mail | Email parser |
| 4 | BLL, BNC, Licitanet | Web scraping |

## Integração com SIG

Dados fluem SGL → SIG: fornecedor vencedor, custo, marca, código, contrato público.
Estratégia: Fase 1 (export), Fase 2 (API), Fase 3 (sync automática).
