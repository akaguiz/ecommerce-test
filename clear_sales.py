# clear_sales.py
from app import app, db, Sale

def clear_sales():
    with app.app_context():
        try:
            Sale.query.delete()
            db.session.commit()
            print("Todas as vendas foram removidas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao remover vendas: {str(e)}")

if __name__ == '__main__':
    clear_sales()