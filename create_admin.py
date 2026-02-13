import os
os.environ['DATABASE_URL'] = 'postgresql://sgl_user:dVWg2mQgCQi9g7qAwlxcNwD9gRcxpAMT@dpg-d67n20i4d50c73ahkipg-a.oregon-postgres.render.com/sgl_db_l72n'
from sgl.app import create_app
from sgl.models.database import db, Usuario

app = create_app('production')
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(email='admin@grupobraz.com').first():
        u = Usuario(nome='Helder Admin', email='admin@grupobraz.com', perfil='admin')
        u.set_senha('SGL@2025!')
        db.session.add(u)
        db.session.commit()
        print(f'Admin criado! ID: {u.id}')
    else:
        print('Admin ja existe')
