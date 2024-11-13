# create_db.py
from app import app, db

def init_db():
    with app.app_context():
        # Isso vai criar todas as tabelas
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    init_db()