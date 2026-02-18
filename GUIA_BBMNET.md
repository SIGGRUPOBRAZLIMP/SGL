# Scraper BBMNET - Integração com SGL

## O que é
Scraper para capturar editais do portal BBMNET (bbmnetlicitacoes.com.br).
Usa autenticação Keycloak OAuth2 e API REST interna do BBMNET.

## Teste rápido

```powershell
cd "C:\SGL-SISTEMA DE GESTAO DE LICITACOES"
python testar_bbmnet.py
```

Se funcionar, você verá:
- ✅ Autenticado com sucesso
- ✅ Total de editais por UF
- ✅ Detalhes de um edital
- ✅ Conversão para formato SGL

## Arquivos

| Arquivo | Destino | Descrição |
|---------|---------|-----------|
| `bbmnet_scraper.py` | `sgl/services/bbmnet_scraper.py` | Scraper principal |
| `testar_bbmnet.py` | raiz do projeto (temporário) | Script de teste |

## Variáveis de ambiente necessárias

Adicionar no Render (Settings > Environment):

```
BBMNET_USERNAME=07923334625
BBMNET_PASSWORD=Gbraz24@
```

## Como a integração funciona

Após o teste, o scraper será integrado ao `captacao_service.py` para:
1. Rodar junto com a captação PNCP no scheduler
2. Salvar editais BBMNET na mesma tabela `edital` do SGL
3. Deduplicar via `hash_unico` (campo já existente)
4. Aparecer na mesma tela de editais do frontend

## API descoberta

- **Token**: POST `https://auth.bbmnet.com.br/realms/BBM/protocol/openid-connect/token`
- **Listagem**: GET `https://bbmnet-cadastro-editais-backend-z7knklmt7a-rj.a.run.app/api/Editais/Participantes?Take=50&Skip=0&Uf=RJ&ModalidadeId=3`
- **Detalhe**: GET `https://bbmnet-cadastro-editais-backend-z7knklmt7a-rj.a.run.app/api/Editais/{uniqueId}`
- **Auth**: Keycloak OAuth2 (password grant ou Authorization Code + PKCE)
