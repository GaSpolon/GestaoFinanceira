from dotenv import load_dotenv
load_dotenv()
import os
from datetime import date, datetime, timedelta
from calendar import monthrange

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash

from models import db, Categoria, Transacao, CategoriaInvestimento, MovimentacaoInvestimento


def criar_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "instance", "financas.db"
        ),
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Migracoes: adiciona colunas se nao existirem
        for tabela, col, tipo in [
            ("transacoes", "forma_pagamento", "VARCHAR(10)"),
            ("transacoes", "identificador", "VARCHAR(100)"),
            ("transacoes", "origem_importacao", "VARCHAR(50)"),
            ("movimentacoes_investimento", "identificador", "VARCHAR(100)"),
            ("movimentacoes_investimento", "origem_importacao", "VARCHAR(50)"),
        ]:
            try:
                db.session.execute(db.text(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        _semear_categorias()
        _semear_categorias_investimento()

    return app


def _semear_categorias_investimento():
    """Cria categorias de investimento padrao."""
    if CategoriaInvestimento.query.first() is not None:
        return
    padrao = [
        ("Renda Fixa", "#17a2b8"),
        ("Acoes", "#6f42c1"),
        ("Fundos Imobiliarios", "#e83e8c"),
        ("Tesouro Direto", "#28a745"),
        ("CDB / LC", "#fd7e14"),
        ("Criptomoedas", "#ffc107"),
        ("Previdencia Privada", "#007bff"),
        ("Outros Investimentos", "#6c757d"),
    ]
    for nome, cor in padrao:
        db.session.add(CategoriaInvestimento(nome=nome, cor=cor))
    db.session.commit()


def _semear_categorias():
    """Cria categorias padrão caso o banco esteja vazio."""
    if Categoria.query.first() is not None:
        return
    padrao = [
        ("Salario", "entrada", "#28a745"),
        ("Freelance", "entrada", "#20c997"),
        ("Investimentos", "entrada", "#17a2b8"),
        ("Alimentacao", "saida", "#dc3545"),
        ("Moradia", "saida", "#fd7e14"),
        ("Transporte", "saida", "#ffc107"),
        ("Entretenimento", "saida", "#6f42c1"),
        ("Saude", "saida", "#e83e8c"),
        ("Educacao", "saida", "#007bff"),
        ("Contas Fixas", "saida", "#343a40"),
        ("Vestuario", "saida", "#20c997"),
        ("Outros", "saida", "#6c757d"),
    ]
    for nome, tipo, cor in padrao:
        db.session.add(Categoria(nome=nome, tipo=tipo, cor=cor))
    db.session.commit()



app = criar_app()


# ─── Utilitarios de periodo ─────────────────────────────────────────────


def _parse_periodo(periodo, valor):
    """Retorna (data_inicio, data_fim) dado um periodo e valor."""
    hoje = date.today()
    if not valor:
        valor = _periodo_padrao(periodo, hoje)

    if periodo == "mensal":
        ano, mes = int(valor[:4]), int(valor[5:7])
        _, ultimo = monthrange(ano, mes)
        return date(ano, mes, 1), date(ano, mes, ultimo)

    elif periodo == "trimestral":
        ano = int(valor[:4])
        q = int(valor[6])
        mes_inicio = (q - 1) * 3 + 1
        _, ultimo = monthrange(ano, mes_inicio + 2)
        return date(ano, mes_inicio, 1), date(ano, mes_inicio + 2, ultimo)

    elif periodo == "semestral":
        ano = int(valor[:4])
        s = int(valor[6])
        mes_inicio = 1 if s == 1 else 7
        mes_fim = 6 if s == 1 else 12
        _, ultimo = monthrange(ano, mes_fim)
        return date(ano, mes_inicio, 1), date(ano, mes_fim, ultimo)

    else:  # anual
        ano = int(valor[:4])
        return date(ano, 1, 1), date(ano, 12, 31)


def _periodo_padrao(periodo, hoje):
    """Valor default para o periodo atual."""
    if periodo == "mensal":
        return hoje.strftime("%Y-%m")
    elif periodo == "trimestral":
        q = (hoje.month - 1) // 3 + 1
        return f"{hoje.year}-Q{q}"
    elif periodo == "semestral":
        s = 1 if hoje.month <= 6 else 2
        return f"{hoje.year}-S{s}"
    else:
        return str(hoje.year)


def _gerar_meses_no_periodo(inicio, fim):
    """Retorna lista de (ano, mes) entre duas datas."""
    meses = []
    cursor = date(inicio.year, inicio.month, 1)
    while cursor <= fim:
        meses.append((cursor.year, cursor.month))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return meses


# ─── Dashboard ──────────────────────────────────────────────────────────


@app.route("/")
def dashboard():
    periodos_disponiveis = [
        ("mensal", "Mensal"),
        ("trimestral", "Trimestral"),
        ("semestral", "Semestral"),
        ("anual", "Anual"),
    ]
    return render_template(
        "dashboard.html",
        periodos_disponiveis=periodos_disponiveis,
    )


@app.route("/api/dados")
def api_dados():
    periodo = request.args.get("periodo", "mensal")
    valor = request.args.get("valor", "")
    data_inicio, data_fim = _parse_periodo(periodo, valor)

    transacoes = Transacao.query.filter(
        Transacao.data >= data_inicio, Transacao.data <= data_fim
    ).all()

    total_entradas = sum(t.valor for t in transacoes if t.tipo == "entrada")
    total_saidas = sum(t.valor for t in transacoes if t.tipo == "saida")
    saldo = total_entradas - total_saidas

    # Gastos por categoria (apenas saidas)
    categorias_gasto = {}
    for t in transacoes:
        if t.tipo == "saida":
            nome = t.categoria.nome if t.categoria else "Sem categoria"
            cor = t.categoria.cor if t.categoria else "#6c757d"
            if nome not in categorias_gasto:
                categorias_gasto[nome] = {"valor": 0, "cor": cor}
            categorias_gasto[nome]["valor"] += t.valor

    pie_labels = list(categorias_gasto.keys())
    pie_data = [v["valor"] for v in categorias_gasto.values()]
    pie_colors = [v["cor"] for v in categorias_gasto.values()]

    # ── Credito ──────────────────────────────────────────────────
    total_credito = sum(t.valor for t in transacoes if t.tipo == "saida" and t.forma_pagamento == "credito")
    total_debito = sum(t.valor for t in transacoes if t.tipo == "saida" and t.forma_pagamento == "debito")

    # Gastos credito por categoria
    credito_cats = {}
    for t in transacoes:
        if t.tipo == "saida" and t.forma_pagamento == "credito":
            nome = t.categoria.nome if t.categoria else "Sem categoria"
            cor = t.categoria.cor if t.categoria else "#6c757d"
            if nome not in credito_cats:
                credito_cats[nome] = {"valor": 0, "cor": cor}
            credito_cats[nome]["valor"] += t.valor

    credito_pie_labels = list(credito_cats.keys())
    credito_pie_data = [v["valor"] for v in credito_cats.values()]
    credito_pie_colors = [v["cor"] for v in credito_cats.values()]

    # Evolucao mensal
    meses = _gerar_meses_no_periodo(data_inicio, data_fim)
    evolucao_labels = []
    receitas_mensais = []
    despesas_mensais = []
    credito_mensal = []
    for ano, mes in meses:
        label = f"{mes:02d}/{ano}"
        receitas_mensais.append(
            sum(
                t.valor
                for t in transacoes
                if t.tipo == "entrada" and t.data.year == ano and t.data.month == mes
            )
        )
        despesas_mensais.append(
            sum(
                t.valor
                for t in transacoes
                if t.tipo == "saida" and t.data.year == ano and t.data.month == mes
            )
        )
        credito_mensal.append(
            sum(
                t.valor
                for t in transacoes
                if t.tipo == "saida" and t.forma_pagamento == "credito"
                and t.data.year == ano and t.data.month == mes
            )
        )
        evolucao_labels.append(label)

    saldo_acumulado = []
    acum = 0
    for i in range(len(meses)):
        acum += receitas_mensais[i] - despesas_mensais[i]
        saldo_acumulado.append(round(acum, 2))

    return jsonify(
        {
            "total_entradas": round(total_entradas, 2),
            "total_saidas": round(total_saidas, 2),
            "saldo": round(saldo, 2),
            "total_credito": round(total_credito, 2),
            "total_debito": round(total_debito, 2),
            "pie_labels": pie_labels,
            "pie_data": [round(v, 2) for v in pie_data],
            "pie_colors": pie_colors,
            "credito_pie_labels": credito_pie_labels,
            "credito_pie_data": [round(v, 2) for v in credito_pie_data],
            "credito_pie_colors": credito_pie_colors,
            "evolucao_labels": evolucao_labels,
            "receitas_mensais": [round(v, 2) for v in receitas_mensais],
            "despesas_mensais": [round(v, 2) for v in despesas_mensais],
            "credito_mensal": [round(v, 2) for v in credito_mensal],
            "saldo_acumulado": saldo_acumulado,
        }
    )


@app.route("/api/investimentos")
def api_investimentos():
    periodo = request.args.get("periodo", "mensal")
    valor = request.args.get("valor", "")
    data_inicio, data_fim = _parse_periodo(periodo, valor)

    movimentacoes = MovimentacaoInvestimento.query.filter(
        MovimentacaoInvestimento.data >= data_inicio,
        MovimentacaoInvestimento.data <= data_fim,
    ).all()

    total_aportes = sum(m.valor for m in movimentacoes if m.tipo == "aporte")
    total_resgates = sum(m.valor for m in movimentacoes if m.tipo == "resgate")
    saldo_periodo = total_aportes - total_resgates

    cats = {}
    for m in movimentacoes:
        nome = m.categoria.nome if m.categoria else "Sem categoria"
        cor = m.categoria.cor if m.categoria else "#6c757d"
        if nome not in cats:
            cats[nome] = {"valor": 0, "cor": cor}
        if m.tipo == "aporte":
            cats[nome]["valor"] += m.valor
        else:
            cats[nome]["valor"] -= m.valor
    pie_labels = [k for k, v in cats.items() if v["valor"] > 0]
    pie_data = [v["valor"] for v in cats.values() if v["valor"] > 0]
    pie_colors = [v["cor"] for k, v in cats.items() if v["valor"] > 0]

    meses = _gerar_meses_no_periodo(data_inicio, data_fim)
    evolucao_labels = []
    aportes_mensais = []
    resgates_mensais = []
    saldo_acumulado = []
    acum = 0
    for ano, mes in meses:
        label = f"{mes:02d}/{ano}"
        ap = sum(
            m.valor for m in movimentacoes
            if m.tipo == "aporte" and m.data.year == ano and m.data.month == mes
        )
        re = sum(
            m.valor for m in movimentacoes
            if m.tipo == "resgate" and m.data.year == ano and m.data.month == mes
        )
        aportes_mensais.append(round(ap, 2))
        resgates_mensais.append(round(re, 2))
        acum += ap - re
        saldo_acumulado.append(round(acum, 2))
        evolucao_labels.append(label)

    return jsonify({
        "total_aportes": round(total_aportes, 2),
        "total_resgates": round(total_resgates, 2),
        "saldo_periodo": round(saldo_periodo, 2),
        "pie_labels": pie_labels,
        "pie_data": [round(v, 2) for v in pie_data],
        "pie_colors": pie_colors,
        "evolucao_labels": evolucao_labels,
        "aportes_mensais": [round(v, 2) for v in aportes_mensais],
        "resgates_mensais": [round(v, 2) for v in resgates_mensais],
        "saldo_acumulado": saldo_acumulado,
    })


# ─── Transacoes (formulario apenas) ─────────────────────────────────────


@app.route("/transacoes", methods=["GET", "POST"])
def transacoes():
    categorias = Categoria.query.order_by(Categoria.nome).all()

    if request.method == "POST":
        tipo = request.form["tipo"]
        descricao = request.form["descricao"].strip()
        try:
            valor = float(request.form["valor"].replace(",", "."))
        except (ValueError, KeyError):
            flash("Valor invalido.", "danger")
            return redirect(url_for("transacoes"))
        categoria_id = int(request.form["categoria_id"])
        try:
            data = date.fromisoformat(request.form["data"])
        except (ValueError, KeyError):
            data = date.today()
        forma_pagamento = request.form.get("forma_pagamento", "") or None

        if valor <= 0:
            flash("O valor deve ser positivo.", "danger")
            return redirect(url_for("transacoes"))
        if not descricao:
            flash("A descricao nao pode ficar vazia.", "danger")
            return redirect(url_for("transacoes"))

        t = Transacao(
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            data=data,
            categoria_id=categoria_id,
            forma_pagamento=forma_pagamento,
        )
        db.session.add(t)
        db.session.commit()
        flash("Transacao registrada com sucesso!", "success")
        return redirect(url_for("transacoes"))

    today = date.today().isoformat()
    return render_template("transacoes.html", categorias=categorias, hoje=today)


# ─── Investimentos (formulario apenas) ──────────────────────────────────


@app.route("/investimentos", methods=["GET", "POST"])
def investimentos():
    categorias = CategoriaInvestimento.query.order_by(CategoriaInvestimento.nome).all()

    if request.method == "POST":
        tipo = request.form["tipo"]
        descricao = request.form["descricao"].strip()
        try:
            valor = float(request.form["valor"].replace(",", "."))
        except (ValueError, KeyError):
            flash("Valor invalido.", "danger")
            return redirect(url_for("investimentos"))
        categoria_id = int(request.form["categoria_id"])
        try:
            data = date.fromisoformat(request.form["data"])
        except (ValueError, KeyError):
            data = date.today()

        if valor <= 0:
            flash("O valor deve ser positivo.", "danger")
            return redirect(url_for("investimentos"))
        if not descricao:
            flash("A descricao nao pode ficar vazia.", "danger")
            return redirect(url_for("investimentos"))

        m = MovimentacaoInvestimento(
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            data=data,
            categoria_id=categoria_id,
        )
        db.session.add(m)
        db.session.commit()
        flash("Movimentacao registrada com sucesso!", "success")
        return redirect(url_for("investimentos"))

    total_aportes = db.session.query(db.func.coalesce(db.func.sum(MovimentacaoInvestimento.valor), 0))\
        .filter(MovimentacaoInvestimento.tipo == "aporte").scalar()
    total_resgates = db.session.query(db.func.coalesce(db.func.sum(MovimentacaoInvestimento.valor), 0))\
        .filter(MovimentacaoInvestimento.tipo == "resgate").scalar()
    saldo_total = total_aportes - total_resgates

    today = date.today().isoformat()
    return render_template(
        "investimentos.html",
        categorias=categorias,
        hoje=today,
        total_aportes=total_aportes,
        total_resgates=total_resgates,
        saldo_total=saldo_total,
    )


# ─── Historico unificado ────────────────────────────────────────────────


@app.route("/historico", methods=["GET"])
def historico():
    filtro_origem = request.args.get("origem", "")
    filtro_tipo = request.args.get("tipo", "")
    filtro_data_inicio = request.args.get("data_inicio", "")
    filtro_data_fim = request.args.get("data_fim", "")

    registros = []

    # Busca transacoes
    if filtro_origem in ("", "transacao"):
        q = Transacao.query
        if filtro_tipo in ("entrada", "saida"):
            q = q.filter(Transacao.tipo == filtro_tipo)
        if filtro_data_inicio:
            q = q.filter(Transacao.data >= date.fromisoformat(filtro_data_inicio))
        if filtro_data_fim:
            q = q.filter(Transacao.data <= date.fromisoformat(filtro_data_fim))
        for t in q.order_by(Transacao.data.desc(), Transacao.id.desc()).all():
            registros.append({
                "id": t.id,
                "origem": "transacao",
                "data": t.data,
                "tipo": t.tipo,
                "tipo_display": "Entrada" if t.tipo == "entrada" else "Saida",
                "forma_pagamento": t.forma_pagamento,
                "descricao": t.descricao,
                "nome_categoria": t.categoria.nome if t.categoria else "---",
                "cor_categoria": t.categoria.cor if t.categoria else "#6c757d",
                "categoria_id": t.categoria_id,
                "valor": t.valor,
                "valor_display": t.valor if t.tipo == "entrada" else -t.valor,
                "valor_formatado": f"R$ {t.valor:.2f}",
            })

    # Busca investimentos
    if filtro_origem in ("", "investimento"):
        q = MovimentacaoInvestimento.query
        if filtro_tipo in ("aporte", "resgate"):
            q = q.filter(MovimentacaoInvestimento.tipo == filtro_tipo)
        if filtro_data_inicio:
            q = q.filter(MovimentacaoInvestimento.data >= date.fromisoformat(filtro_data_inicio))
        if filtro_data_fim:
            q = q.filter(MovimentacaoInvestimento.data <= date.fromisoformat(filtro_data_fim))
        for m in q.order_by(MovimentacaoInvestimento.data.desc(), MovimentacaoInvestimento.id.desc()).all():
            registros.append({
                "id": m.id,
                "origem": "investimento",
                "data": m.data,
                "tipo": m.tipo,
                "tipo_display": "Aporte" if m.tipo == "aporte" else "Resgate",
                "forma_pagamento": None,
                "descricao": m.descricao,
                "nome_categoria": m.categoria.nome if m.categoria else "---",
                "cor_categoria": m.categoria.cor if m.categoria else "#6c757d",
                "categoria_id": m.categoria_id,
                "valor": m.valor,
                "valor_display": m.valor if m.tipo == "aporte" else -m.valor,
                "valor_formatado": f"R$ {m.valor:.2f}",
            })

    # Ordena por data descendente
    registros.sort(key=lambda r: (r["data"], r["id"]), reverse=True)

    categorias_todas = Categoria.query.order_by(Categoria.tipo, Categoria.nome).all()
    categorias_investimento_todas = CategoriaInvestimento.query.order_by(CategoriaInvestimento.nome).all()

    return render_template(
        "historico.html",
        registros=registros,
        filtro_origem=filtro_origem,
        filtro_tipo=filtro_tipo,
        filtro_data_inicio=filtro_data_inicio,
        filtro_data_fim=filtro_data_fim,
        categorias_todas=categorias_todas,
        categorias_investimento_todas=categorias_investimento_todas,
    )


@app.route("/historico/<origem>/<int:id>/excluir", methods=["POST"])
def excluir_do_historico(origem, id):
    if origem == "transacao":
        obj = db.session.get(Transacao, id)
        if obj:
            db.session.delete(obj)
            db.session.commit()
            flash("Transacao excluida.", "success")
        else:
            flash("Transacao nao encontrada.", "danger")
    elif origem == "investimento":
        obj = db.session.get(MovimentacaoInvestimento, id)
        if obj:
            db.session.delete(obj)
            db.session.commit()
            flash("Movimentacao excluida.", "success")
        else:
            flash("Movimentacao nao encontrada.", "danger")
    return redirect(url_for("historico"))


@app.route("/historico/transacao/<int:id>/editar", methods=["POST"])
def editar_transacao_historico(id):
    t = db.session.get(Transacao, id)
    if not t:
        flash("Transacao nao encontrada.", "danger")
        return redirect(url_for("historico"))
    t.tipo = request.form["tipo"]
    t.descricao = request.form["descricao"].strip()
    try:
        t.valor = abs(float(request.form["valor"].replace(",", ".")))
    except (ValueError, KeyError):
        flash("Valor invalido.", "danger")
        return redirect(url_for("historico"))
    try:
        t.data = date.fromisoformat(request.form["data"])
    except (ValueError, KeyError):
        pass
    t.categoria_id = int(request.form["categoria_id"])
    t.forma_pagamento = request.form.get("forma_pagamento") or None
    db.session.commit()
    flash("Transacao atualizada com sucesso!", "success")
    return redirect(url_for("historico"))


@app.route("/historico/investimento/<int:id>/editar", methods=["POST"])
def editar_investimento_historico(id):
    m = db.session.get(MovimentacaoInvestimento, id)
    if not m:
        flash("Movimentacao nao encontrada.", "danger")
        return redirect(url_for("historico"))
    m.tipo = request.form["tipo"]
    m.descricao = request.form["descricao"].strip()
    try:
        m.valor = abs(float(request.form["valor"].replace(",", ".")))
    except (ValueError, KeyError):
        flash("Valor invalido.", "danger")
        return redirect(url_for("historico"))
    try:
        m.data = date.fromisoformat(request.form["data"])
    except (ValueError, KeyError):
        pass
    m.categoria_id = int(request.form["categoria_id"])
    db.session.commit()
    flash("Movimentacao de investimento atualizada com sucesso!", "success")
    return redirect(url_for("historico"))
# ─── Tendencias ─────────────────────────────────────────────────────────


@app.route("/tendencias")
def tendencias():
    categorias = Categoria.query.filter_by(tipo="saida").order_by(Categoria.nome).all()
    periodos_disponiveis = [
        ("mensal", "Mensal"),
        ("trimestral", "Trimestral"),
        ("semestral", "Semestral"),
        ("anual", "Anual"),
    ]
    return render_template(
        "tendencias.html",
        categorias=categorias,
        periodos_disponiveis=periodos_disponiveis,
    )


@app.route("/api/tendencias")
def api_tendencias():
    categoria_id = request.args.get("categoria_id", type=int)
    periodo = request.args.get("periodo", "mensal")
    valor = request.args.get("valor", "")
    data_inicio, data_fim = _parse_periodo(periodo, valor)

    q = Transacao.query.filter(
        Transacao.tipo == "saida",
        Transacao.data >= data_inicio,
        Transacao.data <= data_fim,
    )
    if categoria_id:
        q = q.filter(Transacao.categoria_id == categoria_id)

    transacoes = q.all()

    meses = _gerar_meses_no_periodo(data_inicio, data_fim)
    evolucao_labels = []
    gastos_mensais = []
    for ano, mes in meses:
        label = f"{mes:02d}/{ano}"
        gastos_mensais.append(
            sum(
                t.valor
                for t in transacoes
                if t.data.year == ano and t.data.month == mes
            )
        )
        evolucao_labels.append(label)

    total_periodo = sum(gastos_mensais)

    return jsonify({
        "evolucao_labels": evolucao_labels,
        "gastos_mensais": [round(v, 2) for v in gastos_mensais],
        "total_periodo": round(total_periodo, 2),
    })


# ─── Importacao de CSV ──────────────────────────────────────────────────


@app.route("/api/importar", methods=["POST"])
def api_importar():
    """Recebe upload de arquivo CSV do Nubank e processa via importar_csv."""
    if "arquivo" not in request.files:
        return jsonify({"ok": False, "erro": "Nenhum arquivo enviado."}), 400
    arquivo = request.files["arquivo"]
    if arquivo.filename == "":
        return jsonify({"ok": False, "erro": "Nome de arquivo vazio."}), 400

    import tempfile, os
    from importar_csv import processar_arquivo_csv
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
        arquivo.save(tmp.name)
        tmp_path = tmp.name

    try:
        resultado = processar_arquivo_csv(Path(tmp_path))
        db.session.commit()
        return jsonify({"ok": True, **resultado})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─── Categorias (transacoes + investimentos) ────────────────────────────


@app.route("/categorias")
def categorias():
    todas = Categoria.query.order_by(Categoria.tipo, Categoria.nome).all()
    todas_inv = CategoriaInvestimento.query.order_by(CategoriaInvestimento.nome).all()
    return render_template("categorias.html", categorias=todas, categorias_investimento=todas_inv)
@app.route("/categorias/criar", methods=["POST"])
def criar_categoria():
    nome = request.form["nome"].strip()
    tipo = request.form["tipo"]
    cor = request.form.get("cor", "#6c757d")

    if not nome:
        flash("O nome da categoria nao pode ficar vazio.", "danger")
        return redirect(url_for("categorias"))
    if Categoria.query.filter_by(nome=nome).first():
        flash("Ja existe uma categoria com esse nome.", "danger")
        return redirect(url_for("categorias"))

    c = Categoria(nome=nome, tipo=tipo, cor=cor)
    db.session.add(c)
    db.session.commit()
    flash("Categoria criada com sucesso!", "success")
    return redirect(url_for("categorias"))


@app.route("/categorias/<int:id>/excluir", methods=["POST"])
def excluir_categoria(id):
    c = db.session.get(Categoria, id)
    if c:
        if c.transacoes.count() > 0:
            flash("Nao e possivel excluir uma categoria com transacoes vinculadas.", "danger")
            return redirect(url_for("categorias"))
        db.session.delete(c)
        db.session.commit()
        flash("Categoria excluida.", "success")
    else:
        flash("Categoria nao encontrada.", "danger")
    return redirect(url_for("categorias"))


@app.route("/categorias/<int:id>/editar", methods=["POST"])
def editar_categoria(id):
    c = db.session.get(Categoria, id)
    if not c:
        flash("Categoria nao encontrada.", "danger")
        return redirect(url_for("categorias"))
    nome = request.form["nome"].strip()
    tipo = request.form["tipo"]
    cor = request.form.get("cor", c.cor)
    if not nome:
        flash("O nome da categoria nao pode ficar vazio.", "danger")
        return redirect(url_for("categorias"))
    existente = Categoria.query.filter(Categoria.nome == nome, Categoria.id != id).first()
    if existente:
        flash("Ja existe uma categoria com esse nome.", "danger")
        return redirect(url_for("categorias"))
    c.nome = nome
    c.tipo = tipo
    c.cor = cor
    db.session.commit()
    flash("Categoria atualizada com sucesso!", "success")
    return redirect(url_for("categorias"))


@app.route("/categorias/investimento/criar", methods=["POST"])
def criar_categoria_investimento():
    nome = request.form["nome"].strip()
    cor = request.form.get("cor", "#6c757d")

    if not nome:
        flash("O nome da categoria nao pode ficar vazio.", "danger")
        return redirect(url_for("categorias"))
    if CategoriaInvestimento.query.filter_by(nome=nome).first():
        flash("Ja existe uma categoria com esse nome.", "danger")
        return redirect(url_for("categorias"))

    c = CategoriaInvestimento(nome=nome, cor=cor)
    db.session.add(c)
    db.session.commit()
    flash("Categoria de investimento criada com sucesso!", "success")
    return redirect(url_for("categorias"))



@app.route("/categorias/investimento/<int:id>/editar", methods=["POST"])
def editar_categoria_investimento(id):
    c = db.session.get(CategoriaInvestimento, id)
    if not c:
        flash("Categoria nao encontrada.", "danger")
        return redirect(url_for("categorias"))
    nome = request.form["nome"].strip()
    cor = request.form.get("cor", c.cor)
    if not nome:
        flash("O nome da categoria nao pode ficar vazio.", "danger")
        return redirect(url_for("categorias"))
    existente = CategoriaInvestimento.query.filter(
        CategoriaInvestimento.nome == nome, CategoriaInvestimento.id != id
    ).first()
    if existente:
        flash("Ja existe uma categoria com esse nome.", "danger")
        return redirect(url_for("categorias"))
    c.nome = nome
    c.cor = cor
    db.session.commit()
    flash("Categoria de investimento atualizada com sucesso!", "success")
    return redirect(url_for("categorias"))

@app.route("/categorias/investimento/<int:id>/excluir", methods=["POST"])
def excluir_categoria_investimento(id):
    c = db.session.get(CategoriaInvestimento, id)
    if c:
        if c.movimentacoes.count() > 0:
            flash("Nao e possivel excluir uma categoria com movimentacoes vinculadas.", "danger")
            return redirect(url_for("categorias"))
        db.session.delete(c)
        db.session.commit()
        flash("Categoria de investimento excluida.", "success")
    else:
        flash("Categoria nao encontrada.", "danger")
    return redirect(url_for("categorias"))


# ─── Inicializacao ──────────────────────────────────────────────────────

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(debug=debug, host="127.0.0.1", port=5000)
