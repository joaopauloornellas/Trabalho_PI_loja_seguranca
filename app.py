import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "troque-esta-chave"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # fotos de até 2 MB

UPLOAD_DIR = os.path.join(app.static_folder, "imgs", "uploads")
EXT_FOTO = {"png", "jpg", "jpeg", "gif", "webp"}

UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()

# Cada entidade = uma "tabela". Campo: (nome, rótulo, tipo, largura, opções)
# opções: lista fixa, ou nome de outra entidade (ex.: "categorias") para montar o select.
ENTIDADES = {
    "usuarios": {
        "titulo": "Usuários", "singular": "Usuário", "icone": "bi-people-fill", "admin_listar": True,
        "colunas": [("id", "ID"), ("foto", "Foto"), ("nome", "Nome"), ("email", "Email"), ("celular", "Celular"), ("nivel", "Nível")],
        "campos": [
            ("nome", "Nome", "text", "col-md-6", None),
            ("email", "Email", "email", "col-md-6", None),
            ("celular", "Celular", "text", "col-md-3", None),
            ("nascimento", "Data de Nascimento", "date", "col-md-3", None),
            ("cpf", "CPF", "text", "col-md-3", None),
            ("nivel", "Nível de Acesso", "select", "col-md-3", ["Usuário", "Administrador"]),
            ("senha", "Senha", "password", "col-md-3", None),
            ("cep", "CEP", "text", "col-md-3", None),
            ("endereco", "Endereço", "text", "col-md-4", None),
            ("numero", "Número", "text", "col-md-2", None),
            ("complemento", "Complemento", "text", "col-md-4", None),
            ("cidade", "Cidade", "text", "col-md-4", None),
            ("estado", "Estado", "select", "col-md-4", UFS),
            ("foto", "Foto", "file", "col-md-6", None),
        ],
        "dados": [
            {"id": 1, "nome": "Aluno GTI", "email": "gti.fatec@fatec.com", "celular": "1234567890", "nivel": "Usuário", "senha": generate_password_hash("gti2026")},
            {"id": 2, "nome": "Administrador", "email": "admin.fatec@fatec.com", "celular": "9876543210", "nivel": "Administrador", "senha": generate_password_hash("fatec2026")},
        ],
    },
    "categorias": {
        "titulo": "Categorias", "singular": "Categoria", "icone": "bi-tags-fill",
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
        "titulo": "Produtos", "singular": "Produto", "icone": "bi-camera-video-fill",
        "colunas": [("id", "ID"), ("foto", "Foto"), ("nome", "Nome"), ("categoria", "Categoria"), ("preco", "Preço (R$)"), ("estoque", "Estoque")],
        "campos": [
            ("nome", "Nome", "text", "col-md-6", None),
            ("categoria", "Categoria", "select", "col-md-3", "categorias"),
            ("preco", "Preço (R$)", "number", "col-md-3", None),
            ("estoque", "Estoque", "number", "col-md-3", None),
            ("descricao", "Descrição", "text", "col-md-9", None),
            ("foto", "Foto", "file", "col-md-6", None),
        ],
        "dados": [
            {"id": 1, "nome": "Câmera IP Full HD", "categoria": "Câmeras", "preco": "299.90", "estoque": "25"},
            {"id": 2, "nome": "Central de Alarme 8 Zonas", "categoria": "Alarmes", "preco": "459.00", "estoque": "10"},
        ],
    },
}


def eh_admin():
    return session.get("nivel") == "Administrador"


@app.context_processor
def injetar_contexto():
    return {"menu": ENTIDADES, "eh_admin": eh_admin()}


@app.before_request
def proteger():
    if request.endpoint not in ("login", "cadastro_publico", "static") and "usuario" not in session:
        return redirect(url_for("login"))


@app.errorhandler(413)
def muito_grande(e):
    flash("Imagem muito grande (máximo 2 MB).", "danger")
    return redirect(request.referrer or url_for("dashboard"))


@app.errorhandler(403)
def negado(e):
    flash("Acesso restrito ao administrador.", "danger")
    return redirect(url_for("dashboard"))


def get_ent(nome):
    if nome not in ENTIDADES:
        abort(404)
    return ENTIDADES[nome]


def preparar_campos(ent):
    campos = []
    for nome, rotulo, tipo, col, op in ent["campos"]:
        if isinstance(op, str):  # opções vindas de outra tabela
            op = [r["nome"] for r in ENTIDADES[op]["dados"]]
        campos.append((nome, rotulo, tipo, col, op))
    return campos


def email_existe(email, ignorar_id=None):
    return any(r["email"].lower() == email.lower() and r["id"] != ignorar_id
               for r in ENTIDADES["usuarios"]["dados"])


def salvar_foto(arquivo):
    """Grava a imagem em static/imgs/uploads com nome único. Retorna o nome ou None."""
    if not arquivo or not arquivo.filename:
        return None
    ext = arquivo.filename.rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
    if ext not in EXT_FOTO:
        flash("Formato de imagem inválido (use png, jpg, jpeg, gif ou webp).", "danger")
        return None
    nome = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    arquivo.save(os.path.join(UPLOAD_DIR, nome))
    return nome


def apagar_foto(nome):
    if nome:
        try:
            os.remove(os.path.join(UPLOAD_DIR, nome))
        except OSError:
            pass


def montar_registro(ent, form, files, atual=None, forcar=None):
    novo = {}
    for nome, _rotulo, tipo, *_ in ent["campos"]:
        valor = form.get(nome, "").strip() if tipo != "file" else ""
        if tipo == "file":
            novo[nome] = salvar_foto(files.get(nome)) or (atual or {}).get(nome, "")
        elif nome == "senha":  # nunca guarda a senha em texto puro
            novo[nome] = generate_password_hash(valor) if valor else (atual or {}).get("senha", "")
        else:
            novo[nome] = valor
    if forcar:
        novo.update(forcar)
    return novo


def proximo_id(dados):
    return max([r["id"] for r in dados], default=0) + 1


# ---------- Páginas sem menu ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        u = next((r for r in ENTIDADES["usuarios"]["dados"] if r["email"].lower() == email), None)
        if u and u.get("senha") and check_password_hash(u["senha"], senha):
            session.update(usuario=u["email"], nome=u["nome"], nivel=u["nivel"])
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro_publico():
    """Auto-cadastro: sempre cria usuário comum (nunca administrador)."""
    ent = ENTIDADES["usuarios"]
    campos = [c for c in preparar_campos(ent) if c[0] != "nivel"]
    reg = {}
    if request.method == "POST":
        reg = montar_registro(ent, request.form, request.files, forcar={"nivel": "Usuário"})
        if email_existe(reg["email"]):
            apagar_foto(reg.get("foto"))
            flash("E-mail já cadastrado.", "danger")
        else:
            reg["id"] = proximo_id(ent["dados"])
            ent["dados"].append(reg)
            flash("Cadastro realizado! Faça login.", "success")
            return redirect(url_for("login"))
    return render_template("cadastro_publico.html", campos=campos, reg=request.form if request.method == "POST" else {})


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
    ent = get_ent(entidade)
    if ent.get("admin_listar") and not eh_admin():
        abort(403)
    dados = ent["dados"]
    filtro = None
    if entidade == "produtos":  # ex.: /produtos/listar?categoria=Câmeras
        filtro = request.args.get("categoria")
        if filtro:
            dados = [r for r in dados if r.get("categoria") == filtro]
    return render_template("listar.html", ent=ent, entidade=entidade, dados=dados, filtro=filtro)


@app.route("/<entidade>/cadastrar", methods=["GET", "POST"])
@app.route("/<entidade>/<int:id>/editar", methods=["GET", "POST"])
def cadastrar(entidade, id=None):
    if not eh_admin():
        abort(403)
    ent = get_ent(entidade)
    dados = ent["dados"]
    reg = {}
    if id:
        reg = next((r for r in dados if r["id"] == id), None)
        if reg is None:
            abort(404)
    if request.method == "POST":
        novo = montar_registro(ent, request.form, request.files, reg if id else None)
        if entidade == "usuarios" and email_existe(novo["email"], id):
            if novo.get("foto") and novo["foto"] != reg.get("foto"):
                apagar_foto(novo["foto"])
            novo["foto"] = reg.get("foto", "")
            flash("E-mail já cadastrado.", "danger")
            reg = novo
        else:
            if id:
                if novo.get("foto") != reg.get("foto"):
                    apagar_foto(reg.get("foto"))
                reg.update(novo)
            else:
                novo["id"] = proximo_id(dados)
                dados.append(novo)
            flash(f"{ent['singular']} salvo com sucesso.", "success")
            return redirect(url_for("listar", entidade=entidade))
    return render_template("cadastrar.html", ent=ent, entidade=entidade,
                           campos=preparar_campos(ent), reg=reg, id=id)


@app.route("/<entidade>/<int:id>/excluir", methods=["POST"])
def excluir(entidade, id):
    if not eh_admin():
        abort(403)
    ent = get_ent(entidade)
    for r in ent["dados"]:
        if r["id"] == id:
            apagar_foto(r.get("foto"))
    ent["dados"][:] = [r for r in ent["dados"] if r["id"] != id]
    flash(f"{ent['singular']} excluído.", "success")
    return redirect(url_for("listar", entidade=entidade))


if __name__ == "__main__":
    app.run(debug=True)
