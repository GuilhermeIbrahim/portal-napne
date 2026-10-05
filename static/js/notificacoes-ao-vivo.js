(function () {
    'use strict';

    var area = document.getElementById('area-toasts');
    if (!area || !area.dataset.url || !window.NapneAoVivo) {
        return;
    }

    var MAXIMO_NA_TELA = 3;
    var DURACAO_SAIDA_MS = 400;

    var urlApi = area.dataset.url;
    var urlLista = area.dataset.urlLista;
    var intervalo = parseInt(area.dataset.intervalo, 10) || 20;
    var chave = 'napne:notificacoes:ultimo-id:' + area.dataset.usuario;

    var lista = document.getElementById('lista-notificacoes');
    var selo = document.getElementById('selo-notificacoes');
    var armazem = window.NapneAoVivo.armazenamento();

    var desdeDaConsulta = null;
    var fila = [];
    var naTela = 0;

    function ultimoVisto() {
        var valor = parseInt(armazem.ler(chave), 10);
        return isNaN(valor) ? null : valor;
    }

    function atualizarSelo(quantidade) {
        if (!selo) {
            return;
        }
        var valor = selo.querySelector('.selo-valor');
        if (quantidade > 0) {
            valor.textContent = quantidade > 99 ? '99+' : String(quantidade);
            selo.classList.remove('d-none');
        } else {
            selo.classList.add('d-none');
        }
    }

    function criarElemento(tag, classe) {
        var elemento = document.createElement(tag);
        elemento.className = classe;
        return elemento;
    }

    function montarToast(dados) {
        var toast = criarElemento('div', 'toast-napne');

        var link = criarElemento('a', 'toast-napne__link');
        link.href = dados.url;

        var icone = criarElemento('span', 'toast-napne__icone');
        icone.innerHTML = '<i class="bi bi-bell-fill" aria-hidden="true"></i>';

        var texto = criarElemento('span', 'toast-napne__texto');
        var titulo = criarElemento('strong', 'toast-napne__titulo');
        titulo.textContent = dados.titulo;            
        texto.appendChild(titulo);
        if (dados.trecho) {
            var trecho = criarElemento('span', 'toast-napne__trecho');
            trecho.textContent = dados.trecho;
            texto.appendChild(trecho);
        }

        link.appendChild(icone);
        link.appendChild(texto);

        var fechar = criarElemento('button', 'toast-napne__fechar');
        fechar.type = 'button';
        fechar.setAttribute('aria-label', 'Fechar notificação');
        fechar.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
        fechar.addEventListener('click', function () {
            dispensar(toast);
        });

        var barra = criarElemento('div', 'toast-napne__barra');
        barra.setAttribute('aria-hidden', 'true');
        barra.addEventListener('animationend', function (evento) {
            if (evento.animationName === 'toast-napne-barra') {
                dispensar(toast);
            }
        });

        toast.appendChild(link);
        toast.appendChild(fechar);
        toast.appendChild(barra);
        return toast;
    }

    function exibirProximos() {
        while (naTela < MAXIMO_NA_TELA && fila.length) {
            area.appendChild(montarToast(fila.shift()));
            naTela += 1;
        }
    }

    function dispensar(toast) {
        if (toast.dataset.saindo) {
            return;
        }
        toast.dataset.saindo = '1';
        toast.classList.add('toast-napne--saindo');

        var removido = false;
        function remover() {
            if (removido) {
                return;
            }
            removido = true;
            toast.remove();
            naTela -= 1;
            exibirProximos();
        }
        toast.addEventListener('transitionend', remover);
        window.setTimeout(remover, DURACAO_SAIDA_MS);
    }

    function enfileirar(dados) {
        fila.push(dados);
        exibirProximos();
    }

    function inserirNaLista(html) {
        if (!lista || !html) {
            return;
        }
        var existentes = {};
        lista.querySelectorAll('[data-notificacao-id]').forEach(function (item) {
            existentes[item.dataset.notificacaoId] = true;
        });

        var novos = window.NapneAoVivo.converterHtml(html).filter(function (item) {
            return !existentes[item.dataset.notificacaoId];
        });

        var vazio = document.getElementById('aviso-sem-notificacoes');
        if (vazio && novos.length) {
            vazio.classList.add('d-none');
        }
        window.NapneAoVivo.inserirNoTopo(lista, novos, { preservarLeitura: true });
    }

    function montarUrl() {
        desdeDaConsulta = ultimoVisto();
        var parametros = [];
        if (desdeDaConsulta !== null) {
            parametros.push('desde=' + desdeDaConsulta);
        }
        if (lista) {
            parametros.push('lista=1');
        }
        return urlApi + (parametros.length ? '?' + parametros.join('&') : '');
    }

    function receber(dados) {
        atualizarSelo(dados.nao_lidas);

        if (desdeDaConsulta !== null) {
            dados.novas.forEach(enfileirar);

            var restantes = dados.total_novas - dados.novas.length;
            if (restantes > 0) {
                enfileirar({
                    titulo: restantes === 1 ? 'Mais 1 notificação nova' : 'Mais ' + restantes + ' notificações novas',
                    trecho: 'Toque para ver todas.',
                    url: urlLista
                });
            }
            inserirNaLista(dados.html);
        }

        var visto = Math.max(dados.ultimo_id || 0, desdeDaConsulta || 0, ultimoVisto() || 0);
        armazem.gravar(chave, visto);
    }

    window.NapneAoVivo.iniciarConsulta({
        intervalo: intervalo,
        url: montarUrl,
        aoReceber: receber
    });
})();
