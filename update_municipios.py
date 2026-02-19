"""Atualizar município dos editais existentes extraindo do nome do órgão"""
import re
import sys
sys.path.insert(0, '.')
from sgl.app import create_app
app = create_app()

def extrair_municipio(nome_orgao):
    if not nome_orgao:
        return None
    match = re.search(r'(?:Municipal|Município|Municipio)\s+(?:De|de|DO|do|DA|da)\s+(.+?)(?:\s*[-/]|$)', nome_orgao)
    if match:
        return match.group(1).strip()
    if " de " in nome_orgao.lower():
        parts = nome_orgao.split(" de ")
        if len(parts) >= 3:
            return parts[-1].strip().rstrip("/")
    return None

with app.app_context():
    from sgl.models.database import db, Edital
    editais = Edital.query.filter(
        db.or_(Edital.municipio == None, Edital.municipio == '')
    ).all()
    print(f"Editais sem município: {len(editais)}")
    updated = 0
    for e in editais:
        muni = extrair_municipio(e.orgao_razao_social)
        if muni:
            e.municipio = muni
            updated += 1
    db.session.commit()
    print(f"Atualizados: {updated}")
