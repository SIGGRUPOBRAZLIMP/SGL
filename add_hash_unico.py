"""
Migração: adicionar coluna hash_unico ao modelo Edital (se não existir).
Rodar uma vez: python add_hash_unico.py
"""
import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(__file__))

from sgl.app import create_app
from sgl.models.database import db

app = create_app()

with app.app_context():
    # Verificar se coluna existe
    from sqlalchemy import inspect, text
    
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('edital')]
    
    if 'hash_unico' not in columns:
        print("Adicionando coluna hash_unico à tabela edital...")
        db.session.execute(text(
            "ALTER TABLE edital ADD COLUMN hash_unico VARCHAR(64)"
        ))
        db.session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_edital_hash_unico ON edital(hash_unico)"
        ))
        db.session.commit()
        print("✅ Coluna hash_unico adicionada com sucesso!")
    else:
        print("✅ Coluna hash_unico já existe.")
    
    if 'plataforma_origem' not in columns:
        print("Adicionando coluna plataforma_origem à tabela edital...")
        db.session.execute(text(
            "ALTER TABLE edital ADD COLUMN plataforma_origem VARCHAR(50) DEFAULT 'pncp'"
        ))
        db.session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_edital_plataforma ON edital(plataforma_origem)"
        ))
        db.session.commit()
        print("✅ Coluna plataforma_origem adicionada com sucesso!")
    else:
        print("✅ Coluna plataforma_origem já existe.")
    
    print("\nColunas atuais da tabela edital:")
    for col in inspector.get_columns('edital'):
        print(f"  - {col['name']}: {col['type']}")
