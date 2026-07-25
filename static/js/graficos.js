/**
 * Graficos dinamicos do Dashboard Financeiro
 * Gerencia 5 Chart.js instancias: pizza (despesas), barras (receita vs despesa),
 * pizza credito (cartao por categoria), linha credito (evolucao fatura), linha (saldo)
 */

let graficoPizza = null;
let graficoBarras = null;
let graficoCreditoPizza = null;
let graficoCreditoLinha = null;
let graficoLinha = null;

function formatarMoeda(valor) {
    return 'R$ ' + valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function gerarOpcoesPeriodo() {
    const periodo = document.getElementById('filtroPeriodo').value;
    const select = document.getElementById('filtroValor');
    select.innerHTML = '';

    const hoje = new Date();
    const anoAtual = hoje.getFullYear();
    const mesAtual = hoje.getMonth() + 1;

    if (periodo === 'mensal') {
        for (let ano = anoAtual; ano >= anoAtual - 2; ano--) {
            for (let mes = 12; mes >= 1; mes--) {
                if (ano === anoAtual && mes > mesAtual) continue;
                const val = `${ano}-${String(mes).padStart(2, '0')}`;
                const label = `${String(mes).padStart(2, '0')}/${ano}`;
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = label;
                if (ano === anoAtual && mes === mesAtual) opt.selected = true;
                select.appendChild(opt);
            }
        }
    } else if (periodo === 'trimestral') {
        for (let ano = anoAtual; ano >= anoAtual - 2; ano--) {
            for (let q = 4; q >= 1; q--) {
                if (ano === anoAtual && (q - 1) * 3 + 1 > mesAtual) continue;
                const val = `${ano}-Q${q}`;
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = `${ano} - ${q}° Trimestre`;
                if (ano === anoAtual && Math.ceil(mesAtual / 3) === q) opt.selected = true;
                select.appendChild(opt);
            }
        }
    } else if (periodo === 'semestral') {
        for (let ano = anoAtual; ano >= anoAtual - 2; ano--) {
            for (let s = 2; s >= 1; s--) {
                if (ano === anoAtual && s === 2 && mesAtual <= 6) continue;
                if (ano === anoAtual && s === 1 && mesAtual > 6) continue;
                const val = `${ano}-S${s}`;
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = `${ano} - ${s}° Semestre`;
                if (ano === anoAtual && ((s === 1 && mesAtual <= 6) || (s === 2 && mesAtual > 6))) opt.selected = true;
                select.appendChild(opt);
            }
        }
    } else { // anual
        for (let ano = anoAtual; ano >= anoAtual - 5; ano--) {
            const val = String(ano);
            const opt = document.createElement('option');
            opt.value = val;
            opt.textContent = String(ano);
            if (ano === anoAtual) opt.selected = true;
            select.appendChild(opt);
        }
    }
}

async function carregarDados() {
    const periodo = document.getElementById('filtroPeriodo').value;
    const valor = document.getElementById('filtroValor').value;
    const btn = document.getElementById('btnAtualizar');
    btn.disabled = true;
    btn.textContent = 'Carregando...';

    try {
        const resp = await fetch(`/api/dados?periodo=${periodo}&valor=${valor}`);
        const dados = await resp.json();

        // Cartoes
        document.getElementById('totalEntradas').textContent = formatarMoeda(dados.total_entradas);
        document.getElementById('totalSaidas').textContent = formatarMoeda(dados.total_saidas);
        document.getElementById('totalCredito').textContent = formatarMoeda(dados.total_credito);

        const saldoEl = document.getElementById('saldoPeriodo');
        saldoEl.textContent = formatarMoeda(dados.saldo);
        saldoEl.className = 'mb-0 ' + (dados.saldo >= 0 ? 'text-success' : 'text-danger');

        // Grafico de pizza — despesas por categoria
        if (graficoPizza) graficoPizza.destroy();
        const ctxPizza = document.getElementById('graficoPizza').getContext('2d');
        graficoPizza = new Chart(ctxPizza, {
            type: 'pie',
            data: {
                labels: dados.pie_labels,
                datasets: [{
                    data: dados.pie_data,
                    backgroundColor: dados.pie_colors,
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'right', labels: { padding: 12, font: { size: 12 } } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                return ` ${ctx.label}: ${formatarMoeda(ctx.parsed)} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Grafico de barras — receitas vs despesas
        if (graficoBarras) graficoBarras.destroy();
        const ctxBarras = document.getElementById('graficoBarras').getContext('2d');
        graficoBarras = new Chart(ctxBarras, {
            type: 'bar',
            data: {
                labels: dados.evolucao_labels,
                datasets: [
                    {
                        label: 'Receitas',
                        data: dados.receitas_mensais,
                        backgroundColor: 'rgba(40, 167, 69, 0.7)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1,
                    },
                    {
                        label: 'Despesas',
                        data: dados.despesas_mensais,
                        backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1,
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) { return 'R$ ' + val.toFixed(0); }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ` ${ctx.dataset.label}: ${formatarMoeda(ctx.parsed.y)}`;
                            }
                        }
                    }
                }
            }
        });

        // Grafico de pizza — cartao de credito por categoria
        if (graficoCreditoPizza) graficoCreditoPizza.destroy();
        const ctxCreditoPizza = document.getElementById('graficoCreditoPizza').getContext('2d');
        graficoCreditoPizza = new Chart(ctxCreditoPizza, {
            type: 'pie',
            data: {
                labels: dados.credito_pie_labels,
                datasets: [{
                    data: dados.credito_pie_data,
                    backgroundColor: dados.credito_pie_colors,
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'right', labels: { padding: 12, font: { size: 12 } } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                return ` ${ctx.label}: ${formatarMoeda(ctx.parsed)} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Grafico de linha — evolucao do cartao de credito
        if (graficoCreditoLinha) graficoCreditoLinha.destroy();
        const ctxCreditoLinha = document.getElementById('graficoCreditoLinha').getContext('2d');
        graficoCreditoLinha = new Chart(ctxCreditoLinha, {
            type: 'line',
            data: {
                labels: dados.evolucao_labels,
                datasets: [{
                    label: 'Fatura do Cartao',
                    data: dados.credito_mensal,
                    borderColor: 'rgba(255, 193, 7, 1)',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) { return 'R$ ' + val.toFixed(0); }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ` Fatura: ${formatarMoeda(ctx.parsed.y)}`;
                            }
                        }
                    }
                }
            }
        });

        // Grafico de linha — saldo acumulado
        if (graficoLinha) graficoLinha.destroy();
        const ctxLinha = document.getElementById('graficoLinha').getContext('2d');
        graficoLinha = new Chart(ctxLinha, {
            type: 'line',
            data: {
                labels: dados.evolucao_labels,
                datasets: [{
                    label: 'Saldo Acumulado',
                    data: dados.saldo_acumulado,
                    borderColor: 'rgba(23, 162, 184, 1)',
                    backgroundColor: 'rgba(23, 162, 184, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        ticks: {
                            callback: function (val) { return 'R$ ' + val.toFixed(0); }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ` Saldo: ${formatarMoeda(ctx.parsed.y)}`;
                            }
                        }
                    }
                }
            }
        });
    } catch (err) {
        console.error('Erro ao carregar dados:', err);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Atualizar';
    }
}

async function importarCSV(arquivo) {
    if (!arquivo) return;
    const status = document.getElementById('statusImportacao');
    const input = document.getElementById('inputArquivoImportar');
    status.textContent = 'Importando ' + arquivo.name + '...';
    status.className = 'text-muted small';

    try {
        const formData = new FormData();
        formData.append('arquivo', arquivo);
        const resp = await fetch('/api/importar', { method: 'POST', body: formData });
        const dados = await resp.json();

        if (dados.ok) {
            const total = dados.importadas || 0;
            status.textContent = total > 0
                ? `${total} transação(ões) importada(s). Atualizando gráficos...`
                : 'Nenhuma transação nova encontrada.';
            status.className = 'text-success small';
            if (total > 0) {
                await carregarDados();
                status.textContent = `${total} transação(ões) importada(s) com sucesso.`;
            }
        } else {
            status.textContent = 'Erro: ' + (dados.erro || 'desconhecido');
            status.className = 'text-danger small';
        }
    } catch (err) {
        status.textContent = 'Erro ao importar. Verifique o console.';
        status.className = 'text-danger small';
        console.error(err);
    } finally {
        input.value = '';
    }
}

// Inicializacao
document.addEventListener('DOMContentLoaded', function () {
    gerarOpcoesPeriodo();
    carregarDados();

    document.getElementById('filtroPeriodo').addEventListener('change', gerarOpcoesPeriodo);
    document.getElementById('btnAtualizar').addEventListener('click', carregarDados);
    // Recarregar automatico ao trocar o valor do periodo
    document.getElementById('filtroValor').addEventListener('change', carregarDados);
});
