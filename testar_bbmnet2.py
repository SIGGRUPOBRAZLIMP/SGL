import sys
sys.path.insert(0, '.')
from sgl.services.bbmnet_scraper import BBMNETScraper

scraper = BBMNETScraper('07923334625', 'Gbraz24@')
scraper.autenticar()

for uf in ['RJ', 'SP']:
    result = scraper.buscar_editais(uf=uf, modalidade_id=3, take=50, skip=0)
    editais = result.get('editais', [])
    count = result.get('count', 0)
    print(f"\n=== {uf}: {count} total, {len(editais)} retornados ===")
    for e in editais:
        orgao = e.get('orgaoPromotor', {})
        nome = orgao.get('razaoSocial', '')
        obj = str(e.get('objeto', ''))[:60]
        num = e.get('numeroEdital', '')
        status = e.get('editalStatus', {}).get('name', '')
        print(f"  PE{num} | {nome[:40]} | {status} | {obj}")
