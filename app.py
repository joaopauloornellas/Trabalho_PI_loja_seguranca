from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

app = Flask(__name__)
app.secret_key = "troque-esta-chave"

UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()

# Cada entidade = uma "tabela". Campo: (nome, rótulo, tipo, largura, opções)
# opções: lista fixa, ou nome de outra entidade (ex.: "categorias") para montar o select.
ENTIDADES = {
    "usuarios": {
        "titulo": "Usuários", "singular": "Usuário",
        "colunas": [("id", "ID"), ("nome", "Nome"), ("email", "Email"), ("celular", "Celular"), ("nivel", "Nível")],
        "campos": [
            ("nome", "Nome", "text", "col-md-6", None),
            ("email", "Email", "email", "col-md-6", None),
            ("celular", "Celular", "text", "col-md-3", None),
            ("nascimento", "Data de Nascimento", "date", "col-md-3", None),
            ("cpf", "CPF", "text", "col-md-3", None),
            ("nivel", "Nível de Acesso", "select", "col-md-3", ["Usuário", "Administrador"]),
            ("cep", "CEP", "text", "col-md-3", None),
            ("endereco", "Endereço", "text", "col-md-7", None),
            ("numero", "Número", "text", "col-md-2", None),
            ("complemento", "Complemento", "text", "col-md-4", None),
            ("cidade", "Cidade", "text", "col-md-4", None),
            ("estado", "Estado", "select", "col-md-4", UFS),
        ],
        "dados": [
            {"id": 1, "nome": "Usuário 1", "email": "user1@example.com", "celular": "1234567890", "nivel": "Usuário"},
            {"id": 2, "nome": "Usuário 2", "email": "user2@example.com", "celular": "9876543210", "nivel": "Administrador"},
        ],
    },
    "categorias": {
        "titulo": "Categorias", "singular": "Categoria",
        "colunas": [("id", "ID"), ("nome", "Nome"), ("descricao", "Descrição")],
        "campos": [
            ("nome", "Nome", "text", "col-md-4", None),
            ("descricao", "Descrição", "text", "col-md-8", None),
        ],
        "dados": [
            {"id": 1, "nome": "Câmeras", "descricao": "Câmeras IP, analógicas e Wi-Fi"},
            {"id": 2, "nome": "Alarmes", "descricao": "Centrais, sensores e sirenes"},
            {"id": 3, "nome": "Controle de Acesso", "descricao": "Fechaduras, leitores e interfones"},
        ],
    },
    "produtos": {
        "titulo": "Produtos", "singular": "Produto",
        "colunas": [("id", "ID"), ("nome", "Nome"), ("categoria", "Categoria"), ("preco", "Preço (R$)"), ("estoque", "Estoque")],
        "campos": [
            ("nome", "Nome", "text", "col-md-6", None),
            ("categoria", "Categoria", "select", "col-md-3", "categorias"),
            ("preco", "Preço (R$)", "number", "col-md-3", None),
            ("estoque", "Estoque", "number", "col-md-3", None),
            ("descricao", "Descrição", "text", "col-md-9", None),
        ],
        "dados": [
            {"id": 1, "nome": "Câmera IP Full HD", "categoria": "Câmeras", "preco": "299.90", "estoque": "25"},
            {"id": 2, "nome": "Central de Alarme 8 Zonas", "categoria": "Alarmes", "preco": "459.00", "estoque": "10"},
        ],
    },
}


@app.context_processor
def injetar_menu():
    return {"menu": ENTIDADES}


@app.before_request
def proteger():
    publico = request.endpoint in ("login", "static") or (
        request.endpoint == "cadastrar" and (request.view_args or {}).get("entidade") == "usuarios" and "id" not in request.view_args)
    if not publico and "usuario" not in session:
        return redirect(url_for("login"))


def get_ent(nome):
    if nome not in ENTIDADES:
        abort(404)
    return ENTIDADES[nome]


# ---------- Páginas sem menu ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("email") and request.form.get("senha"):
            session["usuario"] = request.form["email"]
            return redirect(url_for("dashboard"))
        flash("Informe e-mail e senha.")
    return render_template("login.html")


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("login"))


# ---------- Páginas com menu ----------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/<entidade>/listar")
def listar(entidade):
    return render_template("listar.html", ent=get_ent(entidade), entidade=entidade)


@app.route("/<entidade>/cadastrar", methods=["GET", "POST"])
@app.route("/<entidade>/<int:id>/editar", methods=["GET", "POST"])
def cadastrar(entidade, id=None):
    ent = get_ent(entidade)
    dados = ent["dados"]
    reg = {}
    if id:
        reg = next((r for r in dados if r["id"] == id), None)
        if reg is None:
            abort(404)
    if request.method == "POST":
        novo = {c[0]: request.form.get(c[0], "").strip() for c in ent["campos"]}
        if id:
            reg.update(novo)
        else:
            novo["id"] = max([r["id"] for r in dados], default=0) + 1
            dados.append(novo)
        flash(f"{ent['singular']} salvo com sucesso.")
        return redirect(url_for("listar", entidade=entidade))
    campos = []
    for nome, rotulo, tipo, col, op in ent["campos"]:
        if isinstance(op, str):  # opções vindas de outra tabela
            op = [r["nome"] for r in ENTIDADES[op]["dados"]]
        campos.append((nome, rotulo, tipo, col, op))
    return render_template("cadastrar.html", ent=ent, entidade=entidade, campos=campos, reg=reg, id=id)


@app.route("/<entidade>/<int:id>/excluir", methods=["POST"])
def excluir(entidade, id):
    ent = get_ent(entidade)
    ent["dados"][:] = [r for r in ent["dados"] if r["id"] != id]
    flash(f"{ent['singular']} excluído.")
    return redirect(url_for("listar", entidade=entidade))


if __name__ == "__main__":
    app.run(debug=True)
