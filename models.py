from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    tipo = db.Column(db.String(10), nullable=False, default="saida")  # "entrada" | "saida"
    cor = db.Column(db.String(7), nullable=False, default="#6c757d")
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    transacoes = db.relationship("Transacao", back_populates="categoria", lazy="dynamic")

    def __repr__(self):
        return f"<Categoria {self.nome}>"


class Transacao(db.Model):
    __tablename__ = "transacoes"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False)  # "entrada" | "saida"
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False, default=date.today)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    forma_pagamento = db.Column(db.String(10), nullable=True)  # "debito" | "credito" | None (entradas)
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    categoria = db.relationship("Categoria", back_populates="transacoes")

    def __repr__(self):
        return f"<Transacao {self.tipo} R${self.valor:.2f}>"


class CategoriaInvestimento(db.Model):
    __tablename__ = "categorias_investimento"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    cor = db.Column(db.String(7), nullable=False, default="#6c757d")
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    movimentacoes = db.relationship("MovimentacaoInvestimento", back_populates="categoria", lazy="dynamic")

    def __repr__(self):
        return f"<CategoriaInvestimento {self.nome}>"


class MovimentacaoInvestimento(db.Model):
    __tablename__ = "movimentacoes_investimento"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False)  # "aporte" | "resgate"
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False, default=date.today)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_investimento.id"), nullable=False)
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    categoria = db.relationship("CategoriaInvestimento", back_populates="movimentacoes")

    def __repr__(self):
        return f"<MovimentacaoInvestimento {self.tipo} R${self.valor:.2f}>"
