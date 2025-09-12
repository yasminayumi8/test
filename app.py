from functools import wraps

from flask import Flask, request, jsonify, redirect
from flask_pydantic_spec import FlaskPydanticSpec
from flask_jwt_extended import get_jwt_identity, JWTManager, create_access_token, jwt_required
from sqlalchemy import select
from sqlalchemy.testing import db

from models import SessionLocal, Usuario, Produto, Blog, Movimentacao

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
                    dados.get('password_hash', dados.get('papel'))]):
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
        return jsonify({'erro': str(e)}), 400
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
        if not dados["data1"] or not dados['status'] or not dados['quantidade'] or not dados['produto_id']:
            return jsonify({'mensagem': 'Erro de cadasro'}), 400

        novo_movimentacao = Movimentacao(
            data1=dados["data1"],
            status=dados["status"],
            quantidade=dados["quantidade"],
            produto_id=dados["produto_id"],
        )
        novo_movimentacao.save(db)
        movimentacao_response = novo_movimentacao.serialize_movimentacao()
        movimentacao_response["ID_movimentacao"] = novo_movimentacao.ID_movimentacao
        return jsonify(movimentacao_response), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()





if __name__ == '__main__':
    app.run(debug=True)