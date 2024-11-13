# seed_product_sales.py
from app import app, db, User, Item, Sale
from datetime import datetime, timedelta
import random

def create_sample_sales_by_product():
    with app.app_context():
        user = User.query.first()
        if not user:
            print("Nenhum usuário encontrado!")
            return

        items = Item.query.filter_by(user_id=user.id).all()
        if not items:
            print("Nenhum item encontrado!")
            return

        start_date = datetime.now() - timedelta(days=60)
        sales_to_add = []

        # Para cada item
        for item in items:
            # Gerar 40-50 vendas por item
            num_sales = random.randint(40, 50)
            
            for _ in range(num_sales):
                # Data aleatória nos últimos 60 dias
                random_days = random.randint(0, 59)
                sale_date = start_date + timedelta(days=random_days)
                
                # Quantidade aleatória entre 1 e 10
                quantity = random.randint(1, 10)
                
                sale = Sale(
                    item_id=item.id,
                    quantity=quantity,
                    sale_date=sale_date,
                    user_id=user.id
                )
                sales_to_add.append(sale)

        try:
            db.session.bulk_save_objects(sales_to_add)
            db.session.commit()
            print(f"Adicionadas {len(sales_to_add)} vendas de exemplo!")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao adicionar vendas: {str(e)}")

if __name__ == '__main__':
    create_sample_sales_by_product()