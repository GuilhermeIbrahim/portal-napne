(function () {
    'use strict';

    var INTERVALO_MAXIMO_MS = 5 * 60 * 1000;
    var ESPERA_MINIMA_AO_VOLTAR_MS = 5 * 1000;

    function iniciarConsulta(opcoes) {
        var temporizador = null;
        var falhasSeguidas = 0;
        var parado = false;
        var emAndamento = false;
        var ultimaConsulta = 0;

        function proximoAtraso() {
            var base = opcoes.intervalo * 1000 * Math.pow(2, Math.min(falhasSeguidas, 4));
            var variacao = 0.9 + Math.random() * 0.2; // ±10%: evita que todos os navegadores consultem juntos
            return Math.min(base * variacao, INTERVALO_MAXIMO_MS);
        }

        function agendar(atraso) {
            clearTimeout(temporizador);
            if (parado || document.hidden) {
                return;
            }
            temporizador = setTimeout(consultar, atraso === undefined ? proximoAtraso() : atraso);
        }

        function consultar() {
            if (parado || emAndamento || document.hidden) {
                return;
            }

            emAndamento = true;
            ultimaConsulta = Date.now();

            fetch(opcoes.url(), {
                headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
                cache: 'no-store'
            })
                .then(function (resposta) {
                    if (resposta.status === 401 || resposta.status === 403) {
                        parado = true;
                        return null;
                    }
                    if (!resposta.ok) {
                        throw new Error('HTTP ' + resposta.status);
                    }
                    return resposta.json();
                })
                .then(function (dados) {
                    if (dados) {
                        falhasSeguidas = 0;
                        opcoes.aoReceber(dados);
                    }
                })
                .catch(function () {
                    falhasSeguidas += 1;
                })
                .then(function () {
                    emAndamento = false;
                    agendar();
                });
        }

        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                clearTimeout(temporizador);
                return;
            }
            var jaPassou = Date.now() - ultimaConsulta;
            agendar(Math.max(0, ESPERA_MINIMA_AO_VOLTAR_MS - jaPassou));
        });

        consultar();
    }

    function converterHtml(html) {
        var modelo = document.createElement('template');
        modelo.innerHTML = (html || '').trim();
        return Array.prototype.slice.call(modelo.content.children);
    }

    function escolherAncora(container) {
        var filhos = container.children;
        for (var i = 0; i < filhos.length; i += 1) {
            if (filhos[i].getBoundingClientRect().bottom > 0) {
                return filhos[i];
            }
        }
        return null;
    }

    function inserirNoTopo(container, elementos, opcoes) {
        if (!elementos.length) {
            return { inseridos: 0 };
        }

        var raiz = document.documentElement;
        var preservarLeitura = !!(opcoes && opcoes.preservarLeitura);
        var listaAcimaDaTela = container.getBoundingClientRect().top < 0;
        var ancora = preservarLeitura && listaAcimaDaTela ? escolherAncora(container) : null;
        var topoAntes = ancora ? ancora.getBoundingClientRect().top : 0;
        var referencia = container.firstChild;

        raiz.classList.add('sem-ancora-rolagem');

        elementos.forEach(function (elemento) {
            container.insertBefore(elemento, referencia);
        });

        if (ancora) {
            var deslocamento = ancora.getBoundingClientRect().top - topoAntes;
            if (deslocamento !== 0) {
                window.scrollBy(0, deslocamento);
            }
        }

        window.requestAnimationFrame(function () {
            raiz.classList.remove('sem-ancora-rolagem');
        });

        return { inseridos: elementos.length };
    }

    function armazenamento() {
        var memoria = {};

        return {
            ler: function (chave) {
                try {
                    var valor = window.localStorage.getItem(chave);
                    if (valor !== null) {
                        return valor;
                    }
                } catch (erro) { /* armazenamento indisponível: usa a memória */ }
                return Object.prototype.hasOwnProperty.call(memoria, chave) ? memoria[chave] : null;
            },
            gravar: function (chave, valor) {
                memoria[chave] = String(valor);
                try {
                    window.localStorage.setItem(chave, String(valor));
                } catch (erro) { /* sem problema: fica só na memória desta página */ }
            }
        };
    }

    window.NapneAoVivo = {
        iniciarConsulta: iniciarConsulta,
        converterHtml: converterHtml,
        inserirNoTopo: inserirNoTopo,
        armazenamento: armazenamento
    };
})();
