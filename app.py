# app.py
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'error'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    items = db.relationship('Item', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Item Model
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    quantity = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'quantity': self.quantity,
            'sale_date': self.sale_date.strftime('%Y-%m-%d'),
            'user_id': self.user_id
        }

# Create tables
with app.app_context():
    db.create_all()

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))

        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if user_exists:
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        
        if email_exists:
            flash('Email already registered!', 'error')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/reports', methods=['GET'])
@login_required
def reports():
    # Buscar todos os itens do usuário
    items = Item.query.filter_by(user_id=current_user.id).all()
    
    if not items:
        flash('Você precisa cadastrar produtos primeiro!', 'warning')
        return render_template('reports.html', predictions=None, has_enough_data=False)
    
    # Dicionário para armazenar previsões de cada produto
    product_predictions = {}
    product_statistics = {}
    
    for item in items:
        # Buscar vendas específicas deste produto
        sales = Sale.query.filter_by(user_id=current_user.id, item_id=item.id).all()
        
        if len(sales) < 30:
            product_statistics[item.name] = {
                'total_sales': len(sales),
                'total_quantity': sum(sale.quantity for sale in sales),
                'average_quantity': round(sum(sale.quantity for sale in sales) / len(sales), 2) if sales else 0,
                'needs_more_data': True
            }
            continue
            
        # Converter vendas para DataFrame
        sales_data = pd.DataFrame([sale.to_dict() for sale in sales])
        sales_data['sale_date'] = pd.to_datetime(sales_data['sale_date'])
        
        # Criar features para previsão
        sales_data['day_of_week'] = sales_data['sale_date'].dt.dayofweek
        sales_data['month'] = sales_data['sale_date'].dt.month
        sales_data['day'] = sales_data['sale_date'].dt.day
        
        # Preparar features e target
        X = sales_data[['day_of_week', 'month', 'day']]
        y = sales_data['quantity']
        
        # Escalar features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Treinar o modelo
        model = LinearRegression()
        model.fit(X_scaled, y)
        
        # Gerar previsões para os próximos 30 dias
        future_dates = pd.date_range(start=datetime.now(), periods=30, freq='D')
        future_features = pd.DataFrame({
            'day_of_week': future_dates.dayofweek,
            'month': future_dates.month,
            'day': future_dates.day
        })
        
        # Escalar features futuras e fazer previsões
        future_features_scaled = scaler.transform(future_features)
        predictions = model.predict(future_features_scaled)
        
        # Calcular métricas de performance do modelo
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        
        # Preparar dados de previsão
        prediction_data = []
        total_predicted = 0
        for date, pred in zip(future_dates, predictions):
            predicted_value = max(0, round(pred))
            total_predicted += predicted_value
            prediction_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'predicted_sales': predicted_value
            })
        
        # Calcular estatísticas
        product_statistics[item.name] = {
            'total_sales': len(sales),
            'total_quantity': sum(sale.quantity for sale in sales),
            'average_quantity': round(sum(sale.quantity for sale in sales) / len(sales), 2),
            'predicted_next_30_days': total_predicted,
            'average_predicted_daily': round(total_predicted / 30, 2),
            'model_accuracy': round(test_score * 100, 2),
            'needs_more_data': False
        }
        
        product_predictions[item.name] = {
            'predictions': prediction_data,
            'train_score': f"{train_score:.2f}",
            'test_score': f"{test_score:.2f}"
        }
    
    return render_template(
        'reports.html',
        product_predictions=product_predictions,
        product_statistics=product_statistics,
        has_predictions=bool(product_predictions)
    )

# Add a route to record new sales
@app.route('/record_sale', methods=['POST'])
@login_required
def record_sale():
    try:
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])
        
        # Verify item belongs to user
        item = Item.query.get_or_404(item_id)
        if item.user_id != current_user.id:
            flash('Access denied!', 'error')
            return redirect(url_for('index'))
        
        # Create new sale record
        sale = Sale(
            item_id=item_id,
            quantity=quantity,
            user_id=current_user.id
        )
        
        db.session.add(sale)
        db.session.commit()
        
        flash('Sale recorded successfully!', 'success')
        return redirect(url_for('reports'))
        
    except Exception as e:
        flash(f'Error recording sale: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password!', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Protected CRUD routes
@app.route('/')
@login_required
def index():
    items = Item.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', items=items)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        quantity = int(request.form['quantity'])
        
        new_item = Item(
            name=name, 
            description=description, 
            quantity=quantity,
            user_id=current_user.id
        )
        
        db.session.add(new_item)
        db.session.commit()
        
        flash('Item added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    item = Item.query.get_or_404(id)
    
    # Check if the item belongs to the current user
    if item.user_id != current_user.id:
        flash('Access denied!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        item.quantity = int(request.form['quantity'])
        
        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit.html', item=item)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    item = Item.query.get_or_404(id)
    
    # Check if the item belongs to the current user
    if item.user_id != current_user.id:
        flash('Access denied!', 'error')
        return redirect(url_for('index'))
        
    db.session.delete(item)
    db.session.commit()
    
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('index'))

from flask import Flask, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

# Your existing imports and app configuration here...

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

# @app.route('/add')
# @login_required
# def add():
#     return render_template('add.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)