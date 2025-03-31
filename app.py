from flask import Flask, render_template, request, redirect, url_for, session
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from flask import jsonify

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'  # Altere para uma chave segura

# Configuração do PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:d8nvsiszmPuabN25@willingly-dreamy-ferret.data-1.use1.tembo.io:5432/intranet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração de upload de imagens
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelo de Usuário
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identificacao = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)  # Agora armazena a senha diretamente
    permissao = db.Column(db.String(10), nullable=False)
    status = db.Column(db.Boolean, default=True)

# Modelo de Conteúdo
class Conteudos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)
    caminho_foto = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), nullable=False)  # Verifique se existe!


# Modelo de Vaga
class Vagas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

# Modelo de Ouvidoria
class Ouvidoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(255), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    telefone = db.Column(db.String(15), nullable=True)
    descricao = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=db.func.current_timestamp())

class Permissoes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f'<Ouvidoria {self.id} - {self.nome_completo}>'
    

# Rota de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificacao = request.form['identificacao']
        senha = request.form['senha']
        user = Users.query.filter_by(identificacao=identificacao, senha=senha).first()

        if user:
            # Verifica se o usuário está bloqueado
            if not user.status:  # status False significa bloqueado
                return "Este usuário está bloqueado. Não pode fazer login.", 403

            # Se o usuário estiver ativo, coloca os dados na sessão
            session['user_id'] = user.id
            session['permissao'] = user.permissao
            return redirect(url_for('index'))
        else:
            return "Login inválido!"

    return render_template('login.html')


# Rota de Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Página inicial
@app.route('/')
def index():
    conteudos = Conteudos.query.all()
    return render_template('index.html', conteudos=conteudos, permissao=session.get('permissao'))


# Painel administrativo
@app.route('/admin')
def admin():
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/admin/permissoes')
def listar_permissoes():
    permissoes = Permissoes.query.all()
    return render_template('permissoes.html', permissoes=permissoes)

@app.route('/admin/permissoes/create', methods=['GET', 'POST'])
def criar_permissao():
    if request.method == 'POST':
        nome = request.form['nome']
        if nome:
            nova_permissao = Permissoes(nome=nome)
            db.session.add(nova_permissao)
            db.session.commit()
            flash("Permissão criada com sucesso!", "success")
            return redirect(url_for('listar_permissoes'))
        else:
            flash("O nome da permissão é obrigatório!", "danger")

    return render_template('create_permissao.html')


# Lista de usuários
@app.route('/users')
def users():
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    users = Users.query.all()
    return render_template('users.html', users=users)

# Criar usuário
@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    if request.method == 'POST':
        identificacao = request.form['identificacao']
        senha = request.form['senha']  # Agora armazena diretamente
        permissao = request.form['permissao']

        novo_usuario = Users(identificacao=identificacao, senha=senha, permissao=permissao)
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('users'))

    return render_template('create_user.html')

# Editar usuário
@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    usuario = Users.query.get_or_404(id)

    if request.method == 'POST':
        # Pega os dados atualizados do formulário
        usuario.identificacao = request.form['identificacao']
        usuario.senha = request.form['senha']
        usuario.permissao = request.form['permissao']

        db.session.commit()  # Atualiza o usuário no banco de dados
        return redirect(url_for('users'))  # Redireciona para a lista de usuários

    return render_template('edit_user.html', usuario=usuario)

# Excluir usuário
@app.route('/delete_user/<int:id>', methods=['GET', 'POST'])
def delete_user(id):
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    usuario = Users.query.get_or_404(id)

    db.session.delete(usuario)  # Exclui o usuário do banco de dados
    db.session.commit()  # Confirma a exclusão

    return redirect(url_for('users'))  # Redireciona para a lista de usuários

# Rota para bloquear usuário
@app.route('/block_user/<int:id>')
def block_user(id):
    user = Users.query.get(id)
    if user:
        user.status = False  # Marca o usuário como bloqueado
        db.session.commit()
    return redirect(url_for('users'))  # Redireciona para a página de usuários

# Rota para desbloquear usuário
@app.route('/unblock_user/<int:id>')
def unblock_user(id):
    user = Users.query.get(id)
    if user:
        user.status = True  # Marca o usuário como desbloqueado
        db.session.commit()
    return redirect(url_for('users'))  # Redireciona para a página de usuários


# Administração de conteúdos
@app.route('/conteudos')
def conteudos():
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    conteudos = Conteudos.query.all()
    return render_template('conteudos.html', conteudos=conteudos)

# Criar conteúdo
@app.route('/create_conteudo', methods=['GET', 'POST'])
def create_conteudo():
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        link = request.form.get('link', '')
        caminho_foto = None

        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename:
                filename = secure_filename(foto.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto.save(filepath)
                caminho_foto = f"static/images/{filename}"

        # Aqui você define o valor padrão do status como True
        novo_conteudo = Conteudos(titulo=titulo, descricao=descricao, link=link, caminho_foto=caminho_foto, status=True)
        db.session.add(novo_conteudo)
        db.session.commit()

        return redirect(url_for('conteudos'))

    return render_template('create_conteudo.html')


# Rota para editar o conteúdo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/edit_conteudo/<int:id>', methods=['GET', 'POST'])
def edit_conteudo(id):
    conteudo = Conteudos.query.get_or_404(id)  # Recupera o conteúdo com o ID fornecido

    if request.method == 'POST':
        conteudo.titulo = request.form['titulo']
        conteudo.descricao = request.form['descricao']
        conteudo.link = request.form.get('link', '')

        # Verifica se foi enviado um arquivo
        if 'foto' in request.files:
            foto = request.files['foto']
            if foto and allowed_file(foto.filename):
                # Gera um nome seguro para o arquivo
                filename = secure_filename(foto.filename)
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Salva a imagem no servidor
                foto.save(foto_path)
                
                # Atualiza o caminho da foto no banco de dados
                conteudo.caminho_foto = f'images/{filename}'

        try:
            db.session.commit()
            flash('Conteúdo editado com sucesso!', 'success')
            return redirect(url_for('conteudos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao editar o conteúdo: {e}', 'danger')

    return render_template('edit_conteudo.html', conteudo=conteudo)


# Rota para excluir o conteúdo
@app.route('/delete_conteudo/<int:id>', methods=['POST'])
def delete_conteudo(id):
    conteudo = Conteudos.query.get_or_404(id)
    
    try:
        db.session.delete(conteudo)
        db.session.commit()
        flash('Conteúdo excluído com sucesso!', 'success')
        return redirect(url_for('conteudos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao excluir o conteúdo: {e}', 'danger')


# Rota para arquivar o conteúdo
@app.route('/archive_conteudo/<int:id>', methods=['POST'])
def archive_conteudo(id):
    conteudo = Conteudos.query.get_or_404(id)
    
    # Atualizando o campo de status para arquivado
    conteudo.status = False  # Definindo como False para indicar que o conteúdo foi arquivado
    try:
        db.session.commit()
        flash('Conteúdo arquivado com sucesso!', 'success')
        return redirect(url_for('conteudos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao arquivar o conteúdo: {e}', 'danger')

# Administração de Vagas
@app.route('/vagas')
def vagas():
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    vagas = Vagas.query.order_by(Vagas.data_criacao.desc()).all()
    return render_template('vagas.html', vagas=vagas)

# Criar Vaga
@app.route('/create_vaga', methods=['GET', 'POST'])
def create_vaga():
    if session.get('permissao') != 'Adm':
        return redirect(url_for('index'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        link = request.form.get('link', '')

        nova_vaga = Vagas(titulo=titulo, descricao=descricao, link=link)
        db.session.add(nova_vaga)
        db.session.commit()

        return redirect(url_for('vagas'))

    return render_template('create_vaga.html')

@app.route('/editar_vaga/<int:id>', methods=['GET', 'POST'])
def edit_vaga(id):
    # Buscar a vaga no banco de dados usando o ID
    vaga = Vagas.query.get_or_404(id)

    if request.method == 'POST':
        # Atualizar os campos com os dados do formulário
        vaga.titulo = request.form['titulo']
        vaga.descricao = request.form['descricao']
        vaga.link = request.form['link']
        vaga.data_criacao = request.form['data_criacao']

        # Salvar as alterações no banco de dados
        db.session.commit()

        # Redirecionar para a página de administração ou onde for necessário
        return redirect(url_for('vagas'))  # Substitua 'admin' pela sua rota de admin

    return render_template('edit_vaga.html', vaga=vaga)

from flask import jsonify

# Rota para obter as vagas em formato JSON
@app.route('/api/vagas')
def api_vagas():
    vagas = Vagas.query.all()  # ou sua consulta de vagas
    vagas_lista = []

    for vaga in vagas:
        vaga_data = {
            'titulo': vaga.titulo,
            'descricao': vaga.descricao,
            'link': vaga.link if vaga.link else ''
        }
        vagas_lista.append(vaga_data)
    
    return jsonify(vagas_lista)

# Rota para deletar a vaga
@app.route('/delete_vaga/<int:id>', methods=['POST'])
def delete_vaga(id):
    vaga = Vagas.query.get(id)
    if vaga:
        db.session.delete(vaga)
        db.session.commit()
    return redirect(url_for('vagas'))


# Rota para salvar os dados da ouvidoria
@app.route('/salvar_ouvidoria', methods=['POST'])
def salvar_ouvidoria():
    if request.method == 'POST':
        nome_completo = request.form['nome_completo']
        cpf = request.form['cpf']
        telefone = request.form['telefone']
        descricao = request.form['descricao']

        # Verificar se todos os campos foram preenchidos
        if not nome_completo or not cpf or not descricao:
            return "Todos os campos são obrigatórios!", 400

        # Verificar se o CPF já existe no banco
        usuario_existente = Ouvidoria.query.filter_by(cpf=cpf).first()
        if usuario_existente:
            return "Já existe uma ouvidoria registrada com esse CPF.", 400

        # Criar um novo registro de ouvidoria no banco de dados
        novo_registro = Ouvidoria(
            nome_completo=nome_completo,
            cpf=cpf,
            telefone=telefone,
            descricao=descricao
        )

        db.session.add(novo_registro)
        db.session.commit()

        return redirect(url_for('index'))  # Redireciona para a página inicial após o envio dos dados
    
@app.route('/ouvidoria')
def ouvidoria():
    # Recupera todos os registros da tabela Ouvidoria
    registros = Ouvidoria.query.all()
    
    # Renderiza o template 'ouvidoria.html' passando os registros
    return render_template('ouvidoria.html', registros=registros)


@app.route('/excluir_ouvidoria/<int:id>', methods=['POST'])
def deletar_ouvidoria(id):
    registro = Ouvidoria.query.get(id)
    db.session.delete(registro)
    db.session.commit()
    return redirect(url_for('ouvidoria'))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
