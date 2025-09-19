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
    db = SessionLocal()
    try:
        # busca o produto pelo id_produto
        var_produto = db.execute(
            select(Produto).where(Produto.id_produto == id)
        ).scalars().first()

        # se não encontrar, retorna 404
        if not var_produto:
            return jsonify({'mensagem': 'Produto não encontrado'}), 404

        # monta o dicionário com os dados
        produto_resultado = {
            "id_produto": var_produto.id_produto,
            "nome_produto": var_produto.nome_produto,
            "dimensao_produto": var_produto.dimensao_produto,
            "preco_produto": var_produto.preco_produto,
            "peso_produto": var_produto.peso_produto,
            "cor_produto": var_produto.cor_produto,
            "descricao_produto": var_produto.descricao_produto,
        }

        return jsonify({'Produto': produto_resultado}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro de consulta: {str(e)}'}), 400

    finally:
        db.close()


@app.route('/consulta/blog/<int:id>', methods=['GET'])
def consulta_blog_id(id):
    db = SessionLocal()
    try:
        var_blog = select(Blog).where(Blog.usuario_id == id)
        var_blog = db.execute(var_blog).scalar()

        if not var_blog:
            return jsonify({'mensagem': 'Blog não encontrado'}), 404

        blog_resultado = {
            "usuario_id": var_blog.usuario_id,
            "comentario": var_blog.comentario,
            "titulo": var_blog.titulo,
            "data": var_blog.data,
        }
        return jsonify({'blog': blog_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro de consulta: {str(e)}'}), 400
    finally:
        db.close()

@app.route('/consulta/pedido/<int:id>', methods=['GET'])
def consulta_pedido_id(id):
    db = SessionLocal()
    try:
        var_pedido = select(Pedido).where(Pedido.ID_pedido == id)
        var_pedido = db.execute(var_pedido).scalars().first()

        if not var_pedido:
            return jsonify({'mensagem': 'Pedido não encontrado'}), 404

        pedido_resultado = var_pedido.serialize_pedido()

        return jsonify({'pedido': pedido_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro interno: {str(e)}'}), 500
    finally:
        db.close()

@app.route('/consulta/movimentacao/<int:id>', methods=['GET'])
def consulta_movimentacao_id(id):
    db = SessionLocal()
    try:
        var_movimentacao = select(Movimentacao).where(Movimentacao.ID_movimentacao == id)
        var_movimentacao = db.execute(var_movimentacao).scalars().first()

        if not var_movimentacao:
            return jsonify({'mensagem': 'Movimentação não encontrada'}), 404

        movimentacao_resultado = var_movimentacao.serialize_movimentacao()

        return jsonify({'movimentacao': movimentacao_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro interno: {str(e)}'}), 500
    finally:
        db.close()


@app.route('/lista/usuario', methods=['GET'])
def lista_usuario():
    db = SessionLocal()
    try:
        resultado = db.execute(select(Usuario)).scalars()
        usuarios = [
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email
            }
            for u in resultado
        ]
        return jsonify({'usuarios': usuarios}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()


@app.route('/lista/produto/', methods=['GET'])
def lista_produto():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Produto)).scalars()  # Pega todos os produtos
        produtos = [
            {
                "id_produto": p.id_produto,
                "nome_produto": p.nome_produto,
                "dimensao_produto": p.dimensao_produto,
                "preco_produto": p.preco_produto,
                "peso_produto": p.peso_produto,
                "cor_produto": p.cor_produto,
                "descricao_produto": p.descricao_produto
            }
            for p in resultado
        ]
        return jsonify({'produtos': produtos}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão

from flask import Flask, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

@app.route('/lista/blog/', methods=['GET'])
def lista_blog():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Blog)).scalars()  # Pega todos os blogs
        blogs = [
            {
                "id_blog": b.id_blog,
                "usuario_id": b.usuario_id,
                "titulo": b.titulo,
                "data": b.data,
                "comentario": b.comentario
            }
            for b in resultado
        ]
        return jsonify({'blogs': blogs}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/lista/pedido/', methods=['GET'])
def lista_pedido():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Pedido)).scalars()  # Pega todos os pedidos
        pedidos = [
            {
                "ID_pedido": p.ID_pedido,
                "produto_id": p.produto_id,
                "usuario_id": p.usuario_id,
                "vendedor_id": p.vendedor_id,
                "quantidade": p.quantidade,
                "valor_total": p.valor_total,
                "endereco": p.endereco
            }
            for p in resultado
        ]
        return jsonify({'pedidos': pedidos}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/lista/movimentacao/', methods=['GET'])
def lista_movimentacao():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Movimentacao)).scalars()  # Pega todas as movimentações
        movimentacoes = [
            {
                "ID_movimentacao": m.ID_movimentacao,
                "quantidade": m.quantidade,
                "produto_id": m.produto_id,
                "data": m.data.isoformat(),  # converte Date para string JSON
                "status": m.status,
                "usuario_id": m.usuario_id
            }
            for m in resultado
        ]
        return jsonify({'movimentacoes': movimentacoes}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/atualizar/usuario/<int:id_usuario>', methods=['PUT'])
def atualizar_usuario(id_usuario):
    db = SessionLocal()  # Cria a sessão
    try:
        usuario = db.execute(
            select(Usuario).where(Usuario.id == id_usuario)
        ).scalar()

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['nome', 'cpf', 'email', 'papel']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        usuario.nome = dados['nome']
        usuario.cpf = dados['cpf']
        usuario.email = dados['email']
        usuario.papel = dados['papel']

        # Atualiza a senha se fornecida
        if 'password' in dados and dados['password']:
            usuario.set_password(dados['password'])

        db.commit()
        return jsonify({"mensagem": "Usuário atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Garante que a sessão seja fechada


@app.route('/atualizar/produto/<int:id_produto>', methods=['PUT'])
def atualizar_produto(id_produto):
    db = SessionLocal()  # Cria a sessão
    try:
        produto = db.execute(
            select(Produto).where(Produto.id_produto == id_produto)
        ).scalar()

        if not produto:
            return jsonify({'erro': 'Produto não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['nome_produto', 'dimensao_produto', 'preco_produto', 'peso_produto', 'descricao_produto']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        produto.nome_produto = dados['nome_produto']
        produto.dimensao_produto = dados['dimensao_produto']
        produto.preco_produto = dados['preco_produto']
        produto.peso_produto = dados['peso_produto']
        produto.cor_produto = dados.get('cor_produto')  # opcional
        produto.descricao_produto = dados['descricao_produto']

        db.commit()
        return jsonify({"mensagem": "Produto atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/atualizar/blog/<int:id_blog>', methods=['PUT'])
def atualizar_blog(id_blog):
    db = SessionLocal()  # Cria a sessão
    try:
        blog = db.execute(
            select(Blog).where(Blog.id_blog == id_blog)
        ).scalar()

        if not blog:
            return jsonify({'erro': 'Blog não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['titulo', 'data', 'comentario']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        blog.titulo = dados['titulo']
        blog.data = dados['data']
        blog.comentario = dados['comentario']
        blog.usuario_id = dados.get('usuario_id', blog.usuario_id)  # mantém valor antigo se não fornecido

        db.commit()
        return jsonify({"mensagem": "Blog atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/atualizar/pedido/<int:id_pedido>', methods=['PUT'])
def atualizar_pedido(id_pedido):
    db = SessionLocal()  # Cria a sessão
    try:
        pedido = db.execute(
            select(Pedido).where(Pedido.ID_pedido == id_pedido)
        ).scalar()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        dados = request.get_json()

        # Campos obrigatórios
        campos_obrigatorios = ['usuario_id', 'produto_id', 'quantidade', 'valor_total', 'endereco', 'vendedor_id']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        pedido.usuario_id = dados['usuario_id']
        pedido.produto_id = dados['produto_id']
        pedido.quantidade = dados['quantidade']
        pedido.valor_total = dados['valor_total']
        pedido.endereco = dados['endereco']
        pedido.vendedor_id = dados['vendedor_id']

        db.commit()
        return jsonify({"mensagem": "Pedido atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão

if __name__ == '__main__':
    app.run(debug=True)