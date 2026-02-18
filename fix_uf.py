"""Fix UF extraction from PNCP API response"""
path = 'sgl/services/captacao_service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: _criar_edital - extrair UF de unidadeOrgao
old1 = "uf=contratacao.get('uf'),"
new1 = "uf=contratacao.get('unidadeOrgao', {}).get('ufSigla') or contratacao.get('uf'),"
content = content.replace(old1, new1)

# Fix 2: filtro check - mesma logica
old2 = "uf = contratacao.get('uf', '')"
new2 = "uf = contratacao.get('unidadeOrgao', {}).get('ufSigla') or contratacao.get('uf', '')"
content = content.replace(old2, new2)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print('OK - UF fix applied')
