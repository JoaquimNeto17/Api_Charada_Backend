from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import firebase_admin
from firebase_admin import credentials, firestore
from auth import token_obrigatorio, gerar_token
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

CORS(app, origins="*")

ADM_USUARIO = os.getenv("ADM_USUARIO")
ADM_SENHA = os.getenv("ADM_SENHA")

# =========================================
#     FIREBASE / FIRESTORE
# =========================================
if os.getenv("VERCEL"):
    cred_json = os.getenv("FIREBASE_CREDENTIALS")

    if not cred_json:
        raise ValueError("FIREBASE_CREDENTIALS não encontrada")

    cred = credentials.Certificate(json.loads(cred_json))
else:
    cred = credentials.Certificate("firebase.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =========================================
#              ROTA PRINCIPAL
# =========================================
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "api": "Charadas",
        "version": "1.0",
        "autor": "Joaquim"
    }), 200


# =========================================
#               LOGIN
# =========================================
@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json()

    if not dados:
        return jsonify({"error": "Envie os dados para login!"}), 400

    usuario = dados.get("usuario")
    senha = dados.get("senha")

    if not usuario or not senha:
        return jsonify({"error": "Usuário e senha são obrigatórios!"}), 400

    if usuario == ADM_USUARIO and senha == ADM_SENHA:
        token = gerar_token(usuario)
        return jsonify({
            "message": "Login realizado com sucesso!",
            "token": token
        }), 200

    return jsonify({"error": "Usuário ou senha inválidos"}), 401


# =========================================
#            GET - LISTAR TODAS
# =========================================
@app.route("/charadas", methods=["GET"])
def get_charadas():
    charadas = []
    lista = db.collection("charadas").stream()

    for item in lista:
        charadas.append(item.to_dict())

    return jsonify(charadas), 200


# =========================================
#          GET - ALEATÓRIA
# =========================================
@app.route("/charadas/aleatoria", methods=["GET"])
def get_charada_random():
    charadas = []
    lista = db.collection("charadas").stream()

    for item in lista:
        charadas.append(item.to_dict())

    return jsonify(random.choice(charadas)), 200


# =========================================
#          GET - POR ID
# =========================================
@app.route("/charadas/<int:id>", methods=["GET"])
def get_charada_by_id(id):
    lista = db.collection("charadas").where("id", "==", id).stream()

    for item in lista:
        return jsonify(item.to_dict()), 200

    return jsonify({"error": "Charada não encontrada"}), 404


# =========================================
#          POST - ADICIONAR
# =========================================
@app.route("/charadas", methods=["POST"])
@token_obrigatorio
def post_charada():
    dados = request.get_json()

    if not dados or "pergunta" not in dados or "resposta" not in dados:
        return jsonify({"error": "Dados incompletos!"}), 400

    try:
        contador_ref = db.collection("contador").document("controle_id")
        contador_doc = contador_ref.get()
        ultimo_id = contador_doc.to_dict().get("ultimo_id")

        novo_id = ultimo_id + 1
        contador_ref.update({"ultimo_id": novo_id})

        db.collection("charadas").add({
            "id": novo_id,
            "pergunta": dados["pergunta"],
            "resposta": dados["resposta"]
        })

        return jsonify({"message": "Charada adicionada com sucesso!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================
#         PUT - ALTERAÇÃO TOTAL
# =========================================
@app.route("/charadas/<int:id>", methods=["PUT"])
@token_obrigatorio
def charadas_put(id):
    dados = request.get_json()

    if not dados or "pergunta" not in dados or "resposta" not in dados:
        return jsonify({"error": "Dados incompletos!"}), 400

    try:
        docs = db.collection("charadas").where("id", "==", id).limit(1).get()

        if not docs:
            return jsonify({"error": "Charada não encontrada!"}), 404

        for doc in docs:
            doc_ref = db.collection("charadas").document(doc.id)
            doc_ref.update({
                "pergunta": dados["pergunta"],
                "resposta": dados["resposta"]
            })

        return jsonify({"message": "Charada alterada com sucesso!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================
#       PATCH - ALTERAÇÃO PARCIAL
# =========================================
@app.route("/charadas/<int:id>", methods=["PATCH"])
@token_obrigatorio
def charadas_patch(id):
    dados = request.get_json()

    if not dados or ("pergunta" not in dados and "resposta" not in dados):
        return jsonify({"error": "Dados incompletos!"}), 400

    try:
        docs = db.collection("charadas").where("id", "==", id).limit(1).get()

        if not docs:
            return jsonify({"error": "Charada não encontrada!"}), 404

        doc_ref = db.collection("charadas").document(docs[0].id)

        update_charadas = {}

        if "pergunta" in dados:
            update_charadas["pergunta"] = dados["pergunta"]

        if "resposta" in dados:
            update_charadas["resposta"] = dados["resposta"]

        doc_ref.update(update_charadas)

        return jsonify({"message": "Charada alterada com sucesso!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================
#             DELETE
# =========================================
@app.route("/charadas/<int:id>", methods=["DELETE"])
@token_obrigatorio
def charadas_delete(id):
    docs = db.collection("charadas").where("id", "==", id).limit(1).get()

    if not docs:
        return jsonify({"message": "Charada não encontrada!"}), 404

    doc_ref = db.collection("charadas").document(docs[0].id)
    doc_ref.delete()

    return jsonify({"message": "Charada excluída com sucesso!"}), 200


# =========================================
#        TRATAMENTO DE ERROS
# =========================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Página não encontrada!"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor!"}), 500


if __name__ == "__main__":
    app.run(debug=True)