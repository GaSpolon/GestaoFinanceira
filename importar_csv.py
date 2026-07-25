"""Modulo de importacao de extratos CSV do Nubank.

Processa arquivos CSV na pasta instance/importar/ e importa transacoes
nao cadastradas, com deduplicacao por UUID (coluna Identificador).
"""

import csv
import shutil
from datetime import date, datetime
from pathlib import Path

from models import Categoria, Transacao, CategoriaInvestimento, MovimentacaoInvestimento

# ---------------------------------------------------------------------------
# Auto-categorizacao baseada em palavras-chave na descricao
# ---------------------------------------------------------------------------

CATEGORIA_KEYWORDS_ENTRADA = {
    "Pix": [
        "transferência recebida pelo pix", "transferencia recebida pelo pix",
        "transferência recebida -", "transferencia recebida -",
    ],
    "Salário": [
        "nexwave", "salario", "salário", "pagamento recebido",
    ],
    "Freelance": [
        "freelance", "gvs gramados", "projeto", "servico prestado",
        "serviço prestado",
    ],
}

CATEGORIA_KEYWORDS_SAIDA = {
    "Alimentação": [
        "restaurante", "lanchonete", "acai", "açaí", "burger",
        "pizza", "pastel", "alimento", "mercado", "supermercado",
        "savegnago", "carrefour", "sanduwish", "outback", "virele",
        "gibotti", "m c lutfi", "italin house",
        "hot tiger", "gaucho lanches", "cambi alimentos", "os pirata", "sao carlos drive", 
        "minimercado", "sorfrio", "padaria",
        "acougue", "hortifruti", "feira", "ifd*", "frogpay*",
        "99 food", "food", "comercio de alimentos", "rotisserie",
        "gelateria", "sorvete", "cacau", "doceria", "confeitaria",
        "rei dos pasteis", "san marin", "sanMarin",
        "cambI", "bella clean",
        "os pirata", "ital in house",
    ],
    "Transporte": [
        "posto", "combustivel", "gasolina", "auto posto",
        "estacionamento", "pedagio", "pedágio", "uber", "99 pop",
    ],
    "Fatura Crédito": [
        "pagamento recebido",
    ],
    "Saúde": [
        "farmacia", "farmácia", "rosar", "medico", "médico",
        "hospital", "clinica", "clínica", "psicologi",
        "dentista", "laboratorio", "laboratório", "exame",
        "plano de saude", "plano de saúde", "unimed", "bradesco saude",
    ],
    "Contas Fixas": [
        "telefonica", "vivo", "claro", "tim", "internet",
        "plano", "seguro", "streaming", "netflix", "spotify",
        "amazon prime", "disney", "hbo", "assinatura", "agua e esgoto", "água e esgoto", "saae", "cpfl",
        "energia", "aluguel", "saneamento", "condominio",
        "condomínio", "iptu", "gas encanado", "gás encanado",
        "iof", "pagamento de fatura",
    ],
    "Entretenimento": [
        "cinema", "teatro", "show", "bar ", "casa noturna",
        "boate", "jogo", "game", "parque", "museu",
    ],
    "Educação": [
        "escola", "faculdade", "curso", "livro", "livraria",
        "material didatico", "material didático", "harmoniza",
    ],
    "Vestuário": [
        "roupa", "calcado", "calçado", "vestuario", "vestuário",
        "tenis", "tênis", "camisa", "bermuda", "loja de roupa",
        "shopping", "renner", "cea", "riachuelo", "marisa",
    ],
}

# Transacoes internas do Nubank que devem ser ignoradas
IGNORAR_DESCRICOES: list[str] = []  # nada ignorado; RDB vira investimento, fatura vira Contas Fixas

# Descricoes que viram MovimentacaoInvestimento (aporte/resgate) em vez de Transacao
RDB_DESCRICOES = ["aplicação rdb", "aplicacao rdb", "resgate rdb"]


PIX_RECEBIDO = "transferência recebida pelo pix"
PIX_ENVIADO = "transferência enviada pelo pix"


def _extrair_nome_pix(descricao: str) -> tuple[str, str] | None:
    """Extrai (tipo, nome) de uma transferencia Pix ou TED/DOC.

    Retorna ("recebido", "NOME") ou ("enviado", "NOME"), ou None.
    """
    desc_lower = descricao.lower().strip()
    if desc_lower.startswith("transferência recebida pelo pix") or desc_lower.startswith("transferencia recebida pelo pix"):
        tipo = "recebido"
    elif desc_lower.startswith("transferência enviada pelo pix") or desc_lower.startswith("transferencia enviada pelo pix"):
        tipo = "enviado"
    elif desc_lower.startswith("transferência recebida -") or desc_lower.startswith("transferencia recebida -"):
        tipo = "recebido"
    else:
        return None

    partes = descricao.split(" - ")
    if len(partes) >= 2:
        nome = partes[1].strip()
        return (tipo, nome)
    return None


def _garantir_categoria_pix():
    """Garante que a categoria 'Pix' (entrada) existe no banco."""
    from models import db
    cat = Categoria.query.filter_by(nome="Pix").first()
    if not cat:
        cat = Categoria(nome="Pix", tipo="entrada", cor="#0d6efd")
        db.session.add(cat)
        db.session.flush()
    return cat.id

def _categorizar(descricao: str, valor: float) -> int | None:
    from models import db
    """Retorna o id da categoria que melhor se encaixa na descricao.

    Retorna None se nao encontrar categoria fallback.
    """
    desc_lower = descricao.lower().strip()

    if valor > 0:
        mapa = CATEGORIA_KEYWORDS_ENTRADA
    else:
        mapa = CATEGORIA_KEYWORDS_SAIDA

    for nome_categoria, keywords in mapa.items():
        for kw in keywords:
            if kw.lower() in desc_lower:
                cat = Categoria.query.filter_by(nome=nome_categoria).first()
                if cat:
                    return cat.id

    # Fallback: "Outros" para saida, "Salário" para entrada
    fallback = "Outros" if valor < 0 else "Salário"
    cat = Categoria.query.filter_by(nome=fallback).first()
    return cat.id if cat else None


def _parse_data(data_str: str) -> date:
    """Converte data DD/MM/YYYY para date."""
    return datetime.strptime(data_str.strip(), "%d/%m/%Y").date()


def _detectar_formato(reader: list[dict]) -> str:
    """Detecta o formato do CSV pelas colunas. Retorna 'conta' ou 'cartao'."""
    if not reader:
        return "conta"
    colunas = set(k.lower().strip() for k in reader[0].keys())
    if "date" in colunas and "title" in colunas and "amount" in colunas:
        return "cartao"
    return "conta"


def _parse_valor_br(valor_str: str) -> float:
    """Converte string de valor brasileiro (1.234,56 ou - 32,00) para float."""
    s = valor_str.strip().strip('"').strip("'")
    # Remove espaços extras entre sinal e número
    s = s.replace(" ", "")
    # Converte formato BR para float
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def _parse_data_iso(data_str: str) -> date:
    """Converte data YYYY-MM-DD para date."""
    return datetime.strptime(data_str.strip(), "%Y-%m-%d").date()


def _gerar_identificador(data_str: str, titulo: str, valor_str: str) -> str:
    """Gera um identificador unico para dedup no formato cartao (sem UUID)."""
    import hashlib
    raw = f"{data_str}|{titulo.strip()}|{valor_str.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _processar_formato_cartao(reader: list[dict], resultado: dict) -> None:
    """Processa CSV no formato cartao de credito (date,title,amount)."""
    from models import db
    for row in reversed(reader):
        try:
            titulo = row.get("title", "").strip()
            if not titulo:
                resultado["puladas"] += 1
                continue

            data_str = row.get("date", "").strip()
            valor_str = row.get("amount", "").strip()
            if not data_str or not valor_str:
                resultado["puladas"] += 1
                continue

            identificador = _gerar_identificador(data_str, titulo, valor_str)

            # Dedup
            existente = Transacao.query.filter_by(identificador=identificador).first()
            if existente:
                break

            valor_original = _parse_valor_br(valor_str)
            data = _parse_data_iso(data_str)
            descricao = titulo

            # "Pagamento recebido" = saida (pagou a fatura do cartao)
            if "pagamento recebido" in descricao.lower():
                tipo = "saida"
                forma_pagamento = None
                cat_fatura = Categoria.query.filter_by(nome="Fatura Crédito").first()
                if not cat_fatura:
                    cat_fatura = Categoria(nome="Fatura Crédito", tipo="saida", cor="#e83e8c")
                    db.session.add(cat_fatura)
                    db.session.flush()
                t = Transacao(
                    tipo="saida", descricao=descricao, valor=abs(valor_original),
                    data=data, categoria_id=cat_fatura.id,
                    forma_pagamento=None, identificador=identificador, origem_importacao="nubank_csv",
                )
                db.session.add(t)
                resultado["importadas"] += 1
                continue

            # Compra normal no cartao
            tipo = "saida"
            forma_pagamento = "credito"
            categoria_id = _categorizar(descricao, -abs(valor_original))
            if categoria_id is None:
                cat_fallback = Categoria.query.filter_by(tipo="saida").first()
                categoria_id = cat_fallback.id if cat_fallback else None
            if categoria_id is None:
                resultado["ignoradas"] += 1
                continue

            t = Transacao(
                tipo=tipo,
                descricao=descricao,
                valor=abs(valor_original),
                data=data,
                categoria_id=categoria_id,
                forma_pagamento=forma_pagamento,
                identificador=identificador,
                origem_importacao="nubank_csv",
            )
            db.session.add(t)
            resultado["importadas"] += 1

        except (ValueError, KeyError, TypeError):
            resultado["puladas"] += 1
            continue

    if resultado["importadas"] > 0:
        db.session.commit()


def processar_arquivo_csv(caminho: Path) -> dict:
    """Processa um arquivo CSV do Nubank (conta corrente ou cartao de credito)."""
    from models import db
    resultado = {"importadas": 0, "ignoradas": 0, "puladas": 0}

    with open(caminho, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if not reader:
        return resultado

    formato = _detectar_formato(reader)
    if formato == "cartao":
        _processar_formato_cartao(reader, resultado)
        return resultado

    # Formato conta corrente (Data,Valor,Identificador,Descrição)
    for row in reversed(reader):
        try:
            identificador = row.get("Identificador", "").strip()
            if not identificador:
                resultado["puladas"] += 1
                continue

            existente = Transacao.query.filter_by(identificador=identificador).first()
            if existente:
                break

            existente_inv = MovimentacaoInvestimento.query.filter_by(identificador=identificador).first()
            if existente_inv:
                break

            valor_original = float(row["Valor"].strip())
            data = _parse_data(row["Data"])
            descricao = row["Descrição"].strip()
            desc_lower = descricao.lower()

            if "estorno" in desc_lower:
                resultado["ignoradas"] += 1
                continue

            # RDB → MovimentacaoInvestimento (aporte ou resgate)
            if any(p in desc_lower for p in RDB_DESCRICOES):
                tipo_inv = "aporte" if "aplic" in desc_lower else "resgate"
                cat_inv = CategoriaInvestimento.query.filter_by(nome="RDB").first()
                if not cat_inv:
                    cat_inv = CategoriaInvestimento(nome="RDB", cor="#fd7e14")
                    db.session.add(cat_inv)
                    db.session.flush()
                m = MovimentacaoInvestimento(
                    tipo=tipo_inv, descricao=descricao, valor=abs(valor_original),
                    data=data, categoria_id=cat_inv.id,
                    identificador=identificador, origem_importacao="nubank_csv",
                )
                db.session.add(m)
                resultado["importadas"] += 1
                continue

            # Pix → simplifica descricao e ajusta categoria/forma_pagamento
            pix_info = _extrair_nome_pix(descricao)
            if pix_info:
                pix_tipo, nome = pix_info
                if pix_tipo == "recebido":
                    label = "Pix recebido" if "pix" in descricao.lower() else "Transferência recebida"
                    descricao = f"{label}: {nome}"
                    t = Transacao(
                        tipo="entrada", descricao=descricao, valor=abs(valor_original),
                        data=data, categoria_id=_garantir_categoria_pix(),
                        forma_pagamento=None, identificador=identificador, origem_importacao="nubank_csv",
                    )
                    db.session.add(t)
                    resultado["importadas"] += 1
                    continue
                else:
                    descricao = f"Pix enviado: {nome}"
                    categoria_id = _categorizar(descricao, valor_original)
                    if categoria_id is None:
                        resultado["ignoradas"] += 1
                        continue
                    t = Transacao(
                        tipo="saida", descricao=descricao, valor=abs(valor_original),
                        data=data, categoria_id=categoria_id,
                        forma_pagamento="debito", identificador=identificador, origem_importacao="nubank_csv",
                    )
                    db.session.add(t)
                    resultado["importadas"] += 1
                    continue

            # Transacao normal (nao-Pix)
            if valor_original > 0:
                tipo = "entrada"
                forma_pagamento = None
            else:
                tipo = "saida"
                if "crédito" in desc_lower or "credito" in desc_lower:
                    forma_pagamento = "credito"
                elif "débito" in desc_lower or "debito" in desc_lower:
                    forma_pagamento = "debito"
                else:
                    forma_pagamento = None

            categoria_id = _categorizar(descricao, valor_original)
            if categoria_id is None:
                resultado["ignoradas"] += 1
                continue

            t = Transacao(
                tipo=tipo, descricao=descricao, valor=abs(valor_original),
                data=data, categoria_id=categoria_id, forma_pagamento=forma_pagamento,
                identificador=identificador, origem_importacao="nubank_csv",
            )
            db.session.add(t)
            resultado["importadas"] += 1

        except (ValueError, KeyError, TypeError):
            resultado["puladas"] += 1
            continue

    if resultado["importadas"] > 0:
        db.session.commit()

    return resultado


def _pasta_importar() -> Path:
    """Retorna o caminho da pasta de importacao."""
    base = Path(__file__).resolve().parent
    return base / "instance" / "importar"


def _pasta_processados() -> Path:
    """Retorna o caminho da pasta de processados."""
    return _pasta_importar() / "processados"


def executar_importacao() -> dict:
    """Varre instance/importar/ e processa todos os CSVs.

    Retorna {"total_importadas": N, "arquivos_processados": [...]}
    """
    pasta = _pasta_importar()
    processados = _pasta_processados()

    pasta.mkdir(parents=True, exist_ok=True)
    processados.mkdir(parents=True, exist_ok=True)

    total_importadas = 0
    arquivos_processados = []

    for arquivo in sorted(pasta.glob("*.csv")):
        resultado = processar_arquivo_csv(arquivo)
        if resultado["importadas"] > 0 or resultado["ignoradas"] > 0:
            arquivos_processados.append({
                "nome": arquivo.name,
                **resultado,
            })
        total_importadas += resultado["importadas"]

        destino = processados / arquivo.name
        shutil.move(str(arquivo), str(destino))

    return {
        "total_importadas": total_importadas,
        "arquivos_processados": arquivos_processados,
    }
