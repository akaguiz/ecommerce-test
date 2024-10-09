from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)

# Configurar banco de dados SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///produtos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

db = SQLAlchemy(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo Produto
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Produto {self.nome}>'

# Modelo Usuário
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Criar banco de dados
with app.app_context():
    db.create_all()

# Função para carregar o usuário atual
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rota para criar novo usuário
@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verificar se o nome de usuário já existe
        usuario_existente = Usuario.query.filter_by(username=username).first()
        if usuario_existente:
            flash('Nome de usuário já está em uso.', 'danger')
            return redirect(url_for('registrar'))

        # Criar novo usuário
        novo_usuario = Usuario(username=username, password=password)
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash('Usuário criado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('registrar.html')

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('lista_produtos'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'danger')
    return render_template('login.html')


# Rota temporária para listar os usuários
@app.route('/listar_usuarios')
def listar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('listar_usuarios.html', usuarios=usuarios)

# Rota de logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

# Rota para alterar o nome de usuário e a senha
@app.route('/alterar_credenciais', methods=['GET', 'POST'])
@login_required
def alterar_credenciais():
    if request.method == 'POST':
        novo_username = request.form['username']
        nova_senha = request.form['password']

        # Verificar se o nome de usuário já existe
        usuario_existente = Usuario.query.filter_by(username=novo_username).first()
        if usuario_existente and usuario_existente.id != current_user.id:
            flash('Nome de usuário já está em uso por outro usuário.', 'danger')
            return redirect(url_for('alterar_credenciais'))

        # Atualizar as credenciais
        current_user.username = novo_username
        current_user.password = nova_senha
        db.session.commit()

        flash('Credenciais atualizadas com sucesso!', 'success')
        return redirect(url_for('lista_produtos'))
    
    return render_template('alterar_credenciais.html', usuario=current_user)

# Rota para listar produtos (apenas para usuários logados)
@app.route('/')
@login_required
def lista_produtos():
    produtos = Produto.query.all()
    return render_template('lista_produtos.html', produtos=produtos)

# Rota para criar novo produto
@app.route('/novo', methods=['GET', 'POST'])
@login_required
def criar_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = float(request.form['preco'])
        estoque = int(request.form['estoque'])
        novo_produto = Produto(nome=nome, descricao=descricao, preco=preco, estoque=estoque)
        db.session.add(novo_produto)
        db.session.commit()
        return redirect(url_for('lista_produtos'))
    return render_template('form_produto.html')

# Rota para atualizar produto
@app.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def atualizar_produto(id):
    produto = Produto.query.get_or_404(id)
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.descricao = request.form['descricao']
        produto.preco = float(request.form['preco'])
        produto.estoque = int(request.form['estoque'])
        db.session.commit()
        return redirect(url_for('lista_produtos'))
    return render_template('form_produto.html', produto=produto)

# Rota para deletar produto
@app.route('/<int:id>/deletar', methods=['GET', 'POST'])
@login_required
def deletar_produto(id):
    produto = Produto.query.get_or_404(id)
    if request.method == 'POST':
        db.session.delete(produto)
        db.session.commit()
        return redirect(url_for('lista_produtos'))
    return render_template('deletar_produto.html', produto=produto)

if __name__ == '__main__':
    app.run(debug=True)