/**
 * Grafico de tendencia de gastos por categoria
 */

let graficoTendencia = null;

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

async function carregarTendencias() {
    const categoriaId = document.getElementById('filtroCategoria').value;
    const periodo = document.getElementById('filtroPeriodo').value;
    const valor = document.getElementById('filtroValor').value;
    const btn = document.getElementById('btnAtualizar');
    btn.disabled = true;
    btn.textContent = 'Carregando...';

    try {
        let url = `/api/tendencias?periodo=${periodo}&valor=${valor}`;
        if (categoriaId) {
            url += `&categoria_id=${categoriaId}`;
        }
        const resp = await fetch(url);
        const dados = await resp.json();

        // Card de total
        document.getElementById('totalPeriodo').textContent = formatarMoeda(dados.total_periodo);

        // Grafico de linha
        if (graficoTendencia) graficoTendencia.destroy();
        const ctx = document.getElementById('graficoTendencia').getContext('2d');
        graficoTendencia = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dados.evolucao_labels,
                datasets: [{
                    label: 'Gastos',
                    data: dados.gastos_mensais,
                    borderColor: 'rgba(220, 53, 69, 1)',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
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
                                return ` Gastos: ${formatarMoeda(ctx.parsed.y)}`;
                            }
                        }
                    }
                }
            }
        });
    } catch (err) {
        console.error('Erro ao carregar tendencias:', err);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Atualizar';
    }
}

// Inicializacao
document.addEventListener('DOMContentLoaded', function () {
    gerarOpcoesPeriodo();
    carregarTendencias();

    document.getElementById('filtroPeriodo').addEventListener('change', gerarOpcoesPeriodo);
    document.getElementById('btnAtualizar').addEventListener('click', carregarTendencias);
    document.getElementById('filtroValor').addEventListener('change', carregarTendencias);
    document.getElementById('filtroCategoria').addEventListener('change', carregarTendencias);
});
