# Documentacao Tecnica — Backend

## Visao Geral

O backend e construido com **Python 3** utilizando o micro-framework **Flask** para servir paginas HTML, processar formularios e expor APIs JSON para os graficos. O ORM utilizado e o **SQLAlchemy** (atraves da extensao `Flask-SQLAlchemy`), e o banco de dados e **SQLite**.

## Estrutura de Arquivos

```
app.py              # Inicializacao, rotas, utilitarios
models.py           # Definicao das entidades do banco
requirements.txt    # Dependencias Python
instance/
  financas.db       # Banco SQLite (criado automaticamente)
```

## Arquivo: app.py

### Inicializacao (`criar_app`)

A fabrica `criar_app()` configura:
- `SECRET_KEY` — chave aleatoria para sessoes flash
- `SQLALCHEMY_DATABASE_URI` — aponta para `instance/financas.db`
- `db.create_all()` — cria as tabelas se nao existirem
- `_semear_categorias()` — insere 12 categorias padrao de transacao na primeira execucao
- `_semear_categorias_investimento()` — insere 8 categorias padrao de investimento na primeira execucao

### Utilitarios de Periodo

Funcoes auxiliares usadas pelas APIs de graficos:

| Funcao | Descricao |
|---|---|
| `_parse_periodo(periodo, valor)` | Converte string de periodo (ex: `"2026-07"` ou `"2026-Q2"`) em tupla `(data_inicio, data_fim)` |
| `_periodo_padrao(periodo, hoje)` | Gera o valor do periodo atual (ex: `"2026-07"` para mensal) |
| `_gerar_meses_no_periodo(inicio, fim)` | Lista de `(ano, mes)` entre duas datas |

Periodos suportados:
- `mensal` — formato `YYYY-MM`
- `trimestral` — formato `YYYY-QN` (N = 1..4)
- `semestral` — formato `YYYY-SN` (N = 1, 2)
- `anual` — formato `YYYY`

### Rotas

#### Dashboard

| Metodo | Rota | Funcao |
|---|---|---|
| GET | `/` | Renderiza `dashboard.html` com lista de periodos |
| GET | `/api/dados?periodo=&valor=` | JSON com totais, gastos por categoria (pizza), receitas vs despesas (barras), saldo acumulado (linha) |
| GET | `/api/investimentos?periodo=&valor=` | JSON com totais de investimento, saldo por categoria, aportes vs resgates, saldo acumulado |

#### Transacoes

| Metodo | Rota | Funcao |
|---|---|---|
| GET | `/transacoes` | Renderiza formulario de nova transacao |
| POST | `/transacoes` | Valida e salva nova transacao no banco |

#### Investimentos

| Metodo | Rota | Funcao |
|---|---|---|
| GET | `/investimentos` | Renderiza formulario + cards de resumo |
| POST | `/investimentos` | Valida e salva novo aporte/resgate |

#### Historico

| Metodo | Rota | Funcao |
|---|---|---|
| GET | `/historico?origem=&tipo=&data_inicio=&data_fim=` | Busca registros de ambas as tabelas (Transacao + MovimentacaoInvestimento), combina em lista unificada ordenada por data |
| POST | `/historico/<origem>/<id>/excluir` | Exclui registro de transacao ou investimento conforme o parametro `origem` |

#### Categorias

| Metodo | Rota | Funcao |
|---|---|---|
| GET | `/categorias` | Renderiza pagina com ambas as listas de categorias |
| POST | `/categorias/criar` | Cria nova categoria de transacao |
| POST | `/categorias/<id>/excluir` | Exclui categoria (bloqueado se tiver transacoes) |
| POST | `/categorias/investimento/criar` | Cria nova categoria de investimento |
| POST | `/categorias/investimento/<id>/excluir` | Exclui categoria de investimento (bloqueado se tiver movimentacoes) |

### Flash Messages

Todas as operacoes POST utilizam `flash()` do Flask com categorias `"success"` ou `"danger"` para feedback visual ao usuario, renderizados pelo template `base.html`.

## Arquivo: models.py

### Entidades

```python
Categoria                     # Categorias para transacoes (entrada/saida)
  id              Integer     # Chave primaria
  nome            String(80)  # Nome unico
  tipo            String(10)  # "entrada" | "saida"
  cor             String(7)   # Hex color (#RRGGBB)
  criada_em       DateTime    # Timestamp UTC

Transacao                     # Movimentacoes financeiras
  id              Integer     # Chave primaria
  tipo            String(10)  # "entrada" | "saida"
  descricao       String(200) # Descricao do gasto/recebimento
  valor           Float       # Valor em reais
  data            Date        # Data da transacao
  categoria_id    Integer     # FK -> Categoria.id
  criada_em       DateTime    # Timestamp UTC

CategoriaInvestimento         # Categorias para investimentos
  id              Integer     # Chave primaria
  nome            String(80)  # Nome unico
  cor             String(7)   # Hex color
  criada_em       DateTime    # Timestamp UTC

MovimentacaoInvestimento      # Aportes e resgates
  id              Integer     # Chave primaria
  tipo            String(10)  # "aporte" | "resgate"
  descricao       String(200) # Descricao
  valor           Float       # Valor em reais
  data            Date        # Data da movimentacao
  categoria_id    Integer     # FK -> CategoriaInvestimento.id
  criada_em       DateTime    # Timestamp UTC
```

Todos os modelos utilizam `back_populates` para relacoes bidirecionais e `lazy="dynamic"` para consultas otimizadas de contagem.

## Tecnologias

| Componente | Versao | Uso |
|---|---|---|
| Python | 3.10+ | Runtime |
| Flask | 3.1.1 | Servidor web, rotas, templates |
| Flask-SQLAlchemy | 3.1.1 | ORM e integracao com banco |
| SQLAlchemy | 2.0+ | Mapeamento objeto-relacional |
