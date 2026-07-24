# Gestao Financeira

Sistema local de gestao financeira pessoal com entrada de receitas/despesas, 
controle de investimentos (caixinha), categorizacao e dashboards dinamicos.

---

## Requisitos

- Python 3.10 ou superior
- Pip (gerenciador de pacotes do Python)

## Instalacao

Abra o terminal na pasta do projeto e instale as dependencias:

```bash
pip install -r requirements.txt
```

## Execucao

```bash
python app.py
```

Acesse no navegador: **http://127.0.0.1:5000**

Para interromper o servidor, pressione `Ctrl+C` no terminal.

---

## Funcionalidades

### 1. Dashboard (`/`)

Pagina inicial com visao geral das financas e dos investimentos.

**Cards de resumo:**
- Total de receitas (verde), despesas (vermelho), saldo do periodo

**Graficos (transacoes):**
- **Despesas por categoria** (pizza) -- proporcao dos gastos agrupados por categoria
- **Receitas vs Despesas** (barras) -- comparativo mes a mes no periodo selecionado
- **Saldo acumulado** (linha) -- evolucao do saldo ao longo do periodo

**Graficos (investimentos):**
- **Saldo por categoria** (pizza) -- distribuicao dos investimentos
- **Aportes vs Resgates** (barras) -- comparativo mes a mes
- **Saldo acumulado** (linha) -- evolucao do patrimonio investido

**Filtro de periodo:**
- Mensal, Trimestral, Semestral, Anual

### 2. Transacoes (`/transacoes`)

Pagina dedicada exclusivamente ao cadastro de novas transacoes financeiras.

**Formulario de entrada:**
- **Tipo:** Entrada (receita) ou Saida (despesa)
- **Descricao:** identificacao do gasto/recebimento
- **Valor:** em reais (R$)
- **Data:** padrao como data atual
- **Categoria:** filtrada automaticamente conforme o tipo selecionado

Abaixo do formulario ha um link direto para o Historico.

### 3. Investimentos (`/investimentos`)

Pagina dedicada a caixinha de investimentos.

**Cards de resumo:** Total de aportes, resgates e saldo acumulado (calculados do banco).

**Formulario de entrada:**
- **Tipo:** Aporte (deposito) ou Resgate (retirada)
- **Descricao:** identificacao da movimentacao
- **Valor:** em reais (R$)
- **Data:** padrao como data atual
- **Categoria:** selecao entre as categorias de investimento

### 4. Categorias (`/categorias`)

Gerenciamento unificado de categorias em duas colunas:

**Categorias de Transacoes** (coluna esquerda):
- 12 categorias padrao (Salario, Freelance, Alimentacao, Moradia, etc.)
- Tipo: Entrada ou Saida
- Cor personalizavel visivel nos graficos

**Categorias de Investimentos** (coluna direita):
- 8 categorias padrao (Renda Fixa, Acoes, FIIs, Tesouro, CDB/LC, etc.)
- Cor personalizavel

Categorias com registros vinculados exibem a contagem e nao podem ser excluidas.

### 5. Historico (`/historico`)

Pagina unificada que combina transacoes e investimentos em uma unica listagem.

**Filtros:**
- **Origem:** Todas / Transacoes / Investimentos
- **Tipo:** Entrada / Saida / Aporte / Resgate
- **De / Ate:** intervalo de datas

**Tabela:** Data, Origem (badge T ou I), Tipo, Descricao, Categoria, Valor, Excluir

### 6. Tema Claro/Escuro

Botao no canto direito da barra de navegacao (icone de lua/sol) para alternar.

- A preferencia fica salva no navegador (localStorage)
- Respeita a preferencia do sistema operacional na primeira visita
- Sem flash branco ao navegar (script bloqueante no head)

---

## Banco de Dados

O sistema utiliza SQLite, armazenado em:

```
instance/financas.db
```

Nao e necessario configurar nenhum servidor de banco de dados. O arquivo e criado automaticamente na primeira execucao.

Os dados persistem entre execucoes do servidor. Para resetar o banco (voltar ao estado inicial), delete este arquivo e reinicie o servidor.

---

## Tecnologias

| Componente | Tecnologia |
|------------|-----------|
| Backend | Python + Flask |
| ORM | SQLAlchemy |
| Banco | SQLite |
| Frontend | Bootstrap 5.3 |
| Graficos | Chart.js 4.4 |
| Tema escuro | Bootstrap data-bs-theme + CSS customizado |

---

## Documentacao Tecnica

Disponivel na pasta `Documentos tecnicos/`:

- `backend.md` -- Rotas, modelos, utilitarios
- `frontend.md` -- Templates, estilos, graficos, tema
- `banco-de-dados.md` -- Esquema relacional, tabelas, ORM, persistencia
