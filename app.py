from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, redirect
from flask_pydantic_spec import FlaskPydanticSpec
from flask_jwt_extended import get_jwt_identity, JWTManager, create_access_token, jwt_required
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.testing import db

from models import SessionLocal, Usuario, Produto, Blog, Movimentacao, Pedido

app = Flask(__name__)
spec = FlaskPydanticSpec( 'Flask',
                         title = 'Flask API',
                         version = '1.0.0')
spec.register(app)
app.config['SECRET_KEY'] = 'secret!'
jwt = JWTManager(app)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        print(f'c_user: {current_user}')
        db = SessionLocal()
        try:
            sql = select(Usuario).where(Usuario.email == current_user)
            user = db.execute(sql).scalar()
            print(f'teste admin: {user and user.papel == "usuario"} {user.papel}')
            if user and user.papel == "usuario":
                return fn(*args, **kwargs)
            return jsonify({"msg":"Acesso negado"}),403
        finally:
            db.close()
    return wrapper

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': 'Welcome to raizes do Brasil!',
    })


@app.route('/login', methods=['POST'])
def login():

    try:
        dados = request.get_json()


        email = dados['email']
        password_hash = dados['password_hash']
        print(f'email: {email}')
        print(f'password_hash: {password_hash}')

        db = SessionLocal()


        sql = select(Usuario).where(Usuario.email == email)
        user = db.execute(sql).scalar()
        print(f'user: {user}')

        if user and user.check_password(password_hash):
            print("if login")
            access_token = create_access_token(identity=str(user.email))
            return jsonify({
                "access_token": access_token,
                "papel": user.papel,
            }), 200
        return jsonify({"msg": "Credenciais inválidas"}), 401
    except Exception as e:
        print(e)
        return jsonify({"msg": str(e)}), 500
    finally:
        db.close()


@app.route('/cadastro/usuario', methods=['POST'])
def cadastrar_usuario():

    dados = request.get_json()
    db = SessionLocal()
    try:
        if not all([dados.get('nome'), dados.get('CPF'), dados.get('email'),
                    dados.get('password_hash'), dados.get('papel')]):

            return jsonify({'erro': "Campos obrigatórios (nome, email) não podem ser vazios"}), 400

        novo_usuario = Usuario(
            nome =dados['nome'],
            CPF =dados['CPF'],
            email=dados['email'],
            #password_hash=dados['password_hash'],
            papel=dados['papel'],
        )
        novo_usuario.set_password(dados['password_hash'])
        novo_usuario.save(db)
        usuario_response = novo_usuario.serialize_usuario()
        usuario_response["id"] = novo_usuario.id
        return jsonify(usuario_response), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()

@app.route('/cadastro/produto',methods=['POST'])

def cadastro_produto():

    dados = request.get_json()
    db = SessionLocal()
    try:
        if not dados['nome_produto'] or not dados['dimensao_produto'] or not dados['preco_produto'] or not \
        dados['peso_produto'] or not dados['cor_produto'] or not dados['descricao_produto']:
            return jsonify({"error", "preencher todos os campos"}), 400

        novo_produto = Produto(
                nome_produto=dados['nome_produto'],
                dimensao_produto=dados['dimensao_produto'],
                preco_produto=dados['preco_produto'],
                peso_produto=dados['peso_produto'],
                cor_produto=dados['cor_produto'],
                descricao_produto=dados['descricao_produto']
        )
        novo_produto.save(db)
        produto_response = novo_produto.serialize_produto()
        produto_response["id_produto"] = novo_produto.id_produto
        return jsonify(produto_response), 201
    except Exception as e:
        return jsonify({"error": "preencher todos os campos"}), 400
    finally:
        db.close()


@app.route('/cadastro/blog', methods=['POST'])
def cadastro_blog():


    dados = request.get_json()
    db = SessionLocal()

    try:
        if not dados["usuario_id"] or not dados["comentario"] or not dados["titulo"] or not dados["data"]:
            return jsonify({'mensagem': 'Erro de cadasro'}), 400

        novo_blog = Blog(
            usuario_id=dados["usuario_id"],
            comentario=dados["comentario"],
            titulo=dados["titulo"],
            data=dados["data"],
        )
        novo_blog.save(db)
        blog_response = novo_blog.serialize_blog()
        blog_response["id_blog"] = novo_blog.id_blog
        return jsonify(blog_response), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()


@app.route('/cadastro/movimentacao', methods=['POST'])
def cadastro_movimentacao():
    dados = request.get_json()
    db = SessionLocal()

    try:
        # Validação de campos obrigatórios
        campos_obrigatorios = ['quantidade', 'produto_id', 'data', 'status', 'usuario_id']
        if not all(campo in dados and dados[campo] for campo in campos_obrigatorios):
            return jsonify({'mensagem': 'Todos os campos são obrigatórios'}), 400

        # Conversão de data (caso esteja vindo como string)
        try:
            data_formatada = datetime.strptime(dados["data"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({'mensagem': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

        novo_movimentacao = Movimentacao(
            quantidade=int(dados["quantidade"]),
            produto_id=int(dados["produto_id"]),
            data=data_formatada,
            status=bool(dados["status"]),
            usuario_id=int(dados["usuario_id"]),
        )
        novo_movimentacao.save(db)

        resposta = novo_movimentacao.serialize_movimentacao()
        resposta["ID_movimentacao"] = novo_movimentacao.ID_movimentacao
        return jsonify(resposta), 201
    except Exception as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()

@app.route('/cadastro/pedido', methods=['POST'])
def cadastro_pedido():
    db = SessionLocal()
    try:
        dados = request.get_json()

        # Validação de campos obrigatórios
        campos_obrigatorios = ['produto_id', 'vendedor_id', 'quantidade', 'valor_total', 'endereco', 'usuario_id']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({'mensagem': 'Todos os campos são obrigatórios'}), 400

        # Criação do objeto Pedido
        pedido = Pedido(
            produto_id=dados["produto_id"],
            vendedor_id=dados["vendedor_id"],
            quantidade=dados["quantidade"],
            valor_total=dados["valor_total"],
            endereco=dados["endereco"],
            usuario_id=dados["usuario_id"]
        )

        # Salvando no banco
        pedido.save(db)

        # Retornando resposta com os dados do pedido criado
        return jsonify({
            'mensagem': 'Pedido cadastrado com sucesso',
            'pedido': pedido.serialize_pedido()
        }), 201


    except SQLAlchemyError as e:

        db.rollback()

        return jsonify({'erro': 'Erro no banco de dados', 'detalhes': str(e)}), 500

    except Exception as e:

        db.rollback()

        return jsonify({'erro': 'Erro inesperado', 'detalhes': str(e)}), 400

    finally:
        db.close()


@app.route('/consulta/usuario/<int:id>', methods=['GET'])
def consulta_usuario(id):
    db = SessionLocal()
    try:
        var_usuario = select(Usuario).where(Usuario.id == id)
        var_usuario = db.execute(var_usuario).scalar()
        print(var_usuario)
        usuario_resultado = {
            "id": var_usuario.id,
            "nome": var_usuario.nome,
            "email": var_usuario.email,
            "papel": var_usuario.papel,
        }
        print(usuario_resultado)
        return jsonify({'Usuario' :usuario_resultado}),200
    except ValueError:
        return jsonify({'mensagem':'Erro de cadasro'}), 400

@app.route('/consulta/produto/<int:id>', methods=['GET'])
def consulta_produto(id):
    try:
        var_produto = select(Produto).where(Produto.id == id)
        var_produto = db_session.execute(var_produto).scalar()
        print(var_produto)
        produto_resultado = {
            "nome": var_produto.nome,
            "dimensao": var_produto.dimensao,
            "preco": var_produto.preco,
            "peso": var_produto.peso,
            "cor": var_produto.cor,
            "descricao": var_produto.descricao,
        }
        print(produto_resultado)
        return jsonify({'Produto' :produto_resultado}),200
    except ValueError:
        return jsonify({'mensagem':'Erro de cadasro'}), 400





if __name__ == '__main__':
    app.run(debug=True)