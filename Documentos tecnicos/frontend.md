# Documentacao Tecnica — Frontend

## Visao Geral

O frontend e composto por templates **Jinja2** renderizados no servidor, com **Bootstrap 5.3** para layout responsivo e **Chart.js 4.4** para graficos interativos. JavaScript vanilla para comportamentos dinamicos (tema escuro, filtro de categorias, atualizacao de graficos).

## Estrutura de Arquivos

```
templates/
  base.html             # Layout base com navbar, flash messages, tema
  dashboard.html        # Dashboard com graficos e filtro de periodo
  transacoes.html       # Formulario de nova transacao
  investimentos.html    # Formulario de investimento + cards de resumo
  categorias.html       # Gerenciamento de categorias (transacoes + investimentos)
  historico.html        # Listagem unificada com filtros

static/
  css/
    estilo.css          # Estilos customizados + modo escuro
  js/
    graficos.js         # Logica dos graficos do dashboard
```

## Template: base.html

### Estrutura
```html
<html data-bs-theme="light">  <!-- Tema gerenciado via Bootstrap 5.3 -->
  <head>
    <script>...</script>       <!-- Script bloqueante para tema (evita flash) -->
    <title>...</title>
    <link bootstrap.css>
    <link estilo.css>
  </head>
  <body>
    <nav>...</nav>             <!-- Navbar com 5 abas + botao tema -->
    <div class="container">
      {% with flashes %}...{% endwith %}  <!-- Flash messages -->
      {% block conteudo %}...{% endblock %}
    </div>
    <script bootstrap.bundle.min.js>
    <script>                   <!-- Click handler do botao tema -->
    {% block scripts %}...{% endblock %}
  </body>
</html>
```

### Tema Claro/Escuro

Implementacao sem flash branco:

1. **Script bloqueante no `<head>`** (antes do CSS): le `localStorage.getItem('tema')` e define `data-bs-theme` no `<html>` sincronamente, antes do primeiro paint. Respeita `prefers-color-scheme` na primeira visita.
2. **Click handler no final do `<body>`**: alterna o atributo e persiste em `localStorage`.
3. **CSS**: regras `[data-bs-theme="dark"]` sobrescrevem cores de cards, tabelas, inputs, alertas e modais com transicao suave de 0.25s.

### Navbar

5 abas principais + botao de tema:
- **Dashboard** (`/`)
- **Transacoes** (`/transacoes`) — form de entrada/saida
- **Investimentos** (`/investimentos`) — form de aporte/resgate
- **Categorias** (`/categorias`) — gerenciamento de ambos os tipos
- **Historico** (`/historico`) — listagem unificada com filtros

O link ativo e destacado via `{% if request.endpoint == '...' %}active{% endif %}`.

## Templates Especificos

### Dashboard (`dashboard.html`)

- Filtro de periodo com dois `select`s: tipo de periodo (mensal/trimestral/semestral/anual) e valor especifico
- Botao "Atualizar" que chama `/api/dados` e `/api/investimentos`
- 3 cards de resumo (receitas, despesas, saldo)
- 3 graficos Chart.js: pizza (despesas por categoria), barras (receitas vs despesas), linha (saldo acumulado)

### Transacoes (`transacoes.html`)

- Formulario centralizado (largura maxima de `col-lg-8`)
- Campos: tipo (entrada/saida), descricao, valor, data, categoria
- Filtro JS no `select#tipo`: esconde categorias do tipo oposto (`display: none`)
- Link para o historico ao final

### Investimentos (`investimentos.html`)

- 3 cards de resumo com valores renderizados pelo servidor (total aportes, resgates, saldo)
- Formulario similar ao de transacoes: tipo (aporte/resgate), descricao, valor, data, categoria
- Link para o historico ao final

### Categorias (`categorias.html`)

- Layout de duas colunas (`col-lg-6`):
  - **Esquerda**: categorias de transacoes (com badge `T` azul)
  - **Direita**: categorias de investimentos (com badge `I` amarelo)
- Cada secao tem seu proprio formulario de criacao e lista de categorias
- Categorias com registros vinculados mostram contagem e bloqueiam exclusao
- Forms usam `action` explicito: `criar_categoria` e `criar_categoria_investimento`

### Historico (`historico.html`)

- Filtros via GET: origem (transacao/investimento), tipo (entrada/saida/aporte/resgate), intervalo de datas
- Tabela unificada com colunas: data, origem (badge T/I), tipo, descricao, categoria, valor, acoes
- Ordenacao por data descendente
- `valor_display` e negativo para saidas/resgates (pintado em vermelho)
- Indicacao visual quando nenhum registro e encontrado

## Estilos Customizados (`static/css/estilo.css`)

- `body` com fundo `#f5f6fa` no claro e `#1a1d23` no escuro
- Cards com `box-shadow`, `border-radius: 8px`, sem borda
- Tabelas com cores zebradas adaptadas para modo escuro via `[data-bs-theme="dark"] .table { --bs-table-bg: ... }`
- Inputs, selects e modais com cores escuras
- Alertas (success/danger/warning/info) com cores adaptadas
- Transicao suave (`transition: 0.25s ease`) em todos os componentes sensiveis ao tema
- Responsivo: `@media (max-width: 768px)` reduz fontes e padding

## Graficos (`static/js/graficos.js`)

Chart.js e carregado via CDN no `dashboard.html` (`head_extra`).

### Funcoes

| Funcao | Descricao |
|---|---|
| `formatarMoeda(valor)` | Formata como `R$ 1.234,56` (locale pt-BR) |
| `gerarOpcoesPeriodo()` | Popula o `select#filtroValor` conforme o periodo selecionado |
| `carregarDados()` | Fetch em `/api/dados`, atualiza cards e 3 graficos |
| `carregarGraficos()` (investimentos) | Fetch em `/api/investimentos`, similar |

### Eventos

- `DOMContentLoaded`: gera opcoes e carrega dados
- `change` no `#filtroPeriodo`: regenera opcoes
- `change` no `#filtroValor`: recarrega graficos automaticamente
- `click` no `#btnAtualizar`: recarrega graficos

## Tecnologias

| Componente | Versao | Uso |
|---|---|---|
| Bootstrap | 5.3.3 | Layout responsivo, componentes, tema escuro nativo |
| Chart.js | 4.4.7 | Graficos pizza, barras e linha |
| Jinja2 | (Flask) | Template engine com heranca, blocos, filtros |
| JavaScript | Vanilla ES6 | Manipulacao DOM, Fetch API, eventos |
