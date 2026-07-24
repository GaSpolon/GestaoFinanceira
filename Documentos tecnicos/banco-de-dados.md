# Documentacao Tecnica — Banco de Dados

## Visao Geral

O sistema utiliza **SQLite** como banco de dados relacional, gerenciado via **SQLAlchemy** (ORM). O arquivo do banco e criado automaticamente na primeira execucao e persistido em disco, garantindo que os dados sobrevivam a reinicializacao do servidor.

## Arquivo do Banco

```
instance/financas.db
```

- Criado automaticamente por `db.create_all()` em `app.py:criar_app()`
- Nao requer instalacao ou configuracao de servidor de banco
- O arquivo e portavel: copiar `instance/financas.db` para outra maquina transfere todos os dados
- Para resetar: delete o arquivo e reinicie o servidor

## Esquema Relacional

```mermaid
erDiagram
    Categoria {
        int id PK
        string nome UNIQUE
        string tipo
        string cor
        datetime criada_em
    }
    Transacao {
        int id PK
        string tipo
        string descricao
        float valor
        date data
        int categoria_id FK
        datetime criada_em
    }
    CategoriaInvestimento {
        int id PK
        string nome UNIQUE
        string cor
        datetime criada_em
    }
    MovimentacaoInvestimento {
        int id PK
        string tipo
        string descricao
        float valor
        date data
        int categoria_id FK
        datetime criada_em
    }

    Categoria ||--o{ Transacao : "categoria_id"
    CategoriaInvestimento ||--o{ MovimentacaoInvestimento : "categoria_id"
```

## Tabelas

### `categorias`

Armazena as categorias para transacoes financeiras (entradas e saidas).

| Coluna | Tipo | Restricoes | Descricao |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | Identificador unico |
| nome | VARCHAR(80) | NOT NULL, UNIQUE | Nome da categoria (ex: "Alimentacao") |
| tipo | VARCHAR(10) | NOT NULL, DEFAULT "saida" | "entrada" ou "saida" |
| cor | VARCHAR(7) | NOT NULL, DEFAULT "#6c757d" | Cor hexadecimal para graficos |
| criada_em | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Data de criacao |

**Dados iniciais (seed):** 12 categorias, sendo 3 de entrada (Salario, Freelance, Investimentos) e 9 de saida (Alimentacao, Moradia, Transporte, etc).

### `transacoes`

Armazena cada movimentacao financeira de entrada ou saida.

| Coluna | Tipo | Restricoes | Descricao |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | Identificador unico |
| tipo | VARCHAR(10) | NOT NULL | "entrada" ou "saida" |
| descricao | VARCHAR(200) | NOT NULL | Descricao do gasto/recebimento |
| valor | FLOAT | NOT NULL | Valor em reais (sempre positivo) |
| data | DATE | NOT NULL, DEFAULT CURRENT_DATE | Data da transacao |
| categoria_id | INTEGER | NOT NULL, FK -> categorias.id | Categoria associada |
| criada_em | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Data de criacao do registro |

**Relacionamento:** Muitas transacoes pertencem a uma categoria (`categoria_id` -> `categorias.id`).

### `categorias_investimento`

Armazena as categorias para investimentos.

| Coluna | Tipo | Restricoes | Descricao |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | Identificador unico |
| nome | VARCHAR(80) | NOT NULL, UNIQUE | Nome da categoria (ex: "Renda Fixa") |
| cor | VARCHAR(7) | NOT NULL, DEFAULT "#6c757d" | Cor hexadecimal para graficos |
| criada_em | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Data de criacao |

**Dados iniciais (seed):** 8 categorias (Renda Fixa, Acoes, Fundos Imobiliarios, Tesouro Direto, CDB/LC, Criptomoedas, Previdencia Privada, Outros).

### `movimentacoes_investimento`

Armazena aportes e resgates de investimentos.

| Coluna | Tipo | Restricoes | Descricao |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | Identificador unico |
| tipo | VARCHAR(10) | NOT NULL | "aporte" ou "resgate" |
| descricao | VARCHAR(200) | NOT NULL | Descricao da movimentacao |
| valor | FLOAT | NOT NULL | Valor em reais (sempre positivo) |
| data | DATE | NOT NULL, DEFAULT CURRENT_DATE | Data da movimentacao |
| categoria_id | INTEGER | NOT NULL, FK -> categorias_investimento.id | Categoria associada |
| criada_em | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Data de criacao do registro |

**Relacionamento:** Muitas movimentacoes pertencem a uma categoria de investimento (`categoria_id` -> `categorias_investimento.id`).

## Mapeamento ORM (SQLAlchemy)

Definido em `models.py`. Detalhes da implementacao:

```python
# Relacoes bidirecionais com back_populates
categoria = db.relationship("CategoriaInvestimento", back_populates="movimentacoes")
movimentacoes = db.relationship("MovimentacaoInvestimento", back_populates="categoria", lazy="dynamic")
```

- `lazy="dynamic"` nas relacoes de lista evita carregar todos os registros na memoria — essencial para `categoria.transacoes.count()` na pagina de categorias, que executa uma query COUNT em vez de carregar objetos.
- `back_populates` mantem a consistencia bidirecional entre os modelos.

## Consultas no Codigo

### Agregacoes (para cards de resumo)

```python
# Soma total de aportes (usa COALESCE para nao retornar None com tabela vazia)
total_aportes = db.session.query(
    db.func.coalesce(db.func.sum(MovimentacaoInvestimento.valor), 0)
).filter(MovimentacaoInvestimento.tipo == "aporte").scalar()
```

### Combinacao de tabelas (historico)

O historico nao utiliza JOIN entre as duas tabelas de movimentacao. Em vez disso:

1. Realiza duas consultas separadas (uma em `Transacao`, outra em `MovimentacaoInvestimento`)
2. Converte cada resultado para um dicionario com keys comuns (`id`, `origem`, `data`, `tipo_display`, `descricao`, etc.)
3. Combina as duas listas e ordena por `(data, id)` descendente

```python
registros.sort(key=lambda r: (r["data"], r["id"]), reverse=True)
```

Isso evita acoplamento entre as tabelas e permite que cada origem tenha seu proprio esquema.

## Persistencia

O SQLite e um banco de dados baseado em arquivo. Quando o servidor Flask e encerrado, o arquivo `instance/financas.db` permanece no disco. Ao reiniciar o servidor:

1. `db.create_all()` executa novamente — como as tabelas ja existem, nao ha alteracao
2. `_semear_categorias()` e `_semear_categorias_investimento()` verificam se ja existem registros (`query.first() is not None`) e pulam a insercao
3. Todos os dados inseridos anteriormente estao intactos

### Verificacao de Persistencia

Para confirmar que os dados persistem:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('instance/financas.db')
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print('Tabelas:', [r[0] for r in cur.fetchall()])
cur.execute('SELECT COUNT(*) FROM categorias')
print('Categorias:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM categorias_investimento')
print('Categorias Investimento:', cur.fetchone()[0])
conn.close()
"
```

## Indices

O SQLAlchemy cria automaticamente indices para chaves primarias. Nao ha indices adicionais definidos, pois o volume de dados esperado e pequeno (uso pessoal). Se o volume crescer, recomenda-se adicionar indices em:

- `transacoes.data` — para filtros por periodo
- `movimentacoes_investimento.data` — para filtros por periodo
- `transacoes.categoria_id` — para joins com categorias
- `movimentacoes_investimento.categoria_id` — para joins com categorias de investimento

```sql
CREATE INDEX idx_transacoes_data ON transacoes(data);
CREATE INDEX idx_movimentacoes_investimento_data ON movimentacoes_investimento(data);
```
