(function () {
    'use strict';

    var lista = document.getElementById('lista-noticias');
    if (!lista || !lista.dataset.urlNovas || !window.NapneAoVivo) {
        return;
    }

    var aviso = document.getElementById('aviso-novas-noticias');
    var anuncio = document.getElementById('anuncio-noticias');
    var ultimoId = parseInt(lista.dataset.ultimoId, 10) || 0;
    var primeiraPagina = lista.dataset.pagina === '1';
    var intervalo = parseInt(lista.dataset.intervalo, 10) || 30;

    var pendentes = [];          
    var novasOutraPagina = 0;

    function plural(quantidade) {
        return quantidade + (quantidade === 1 ? ' nova notícia' : ' novas notícias');
    }

    function anunciar(quantidade) {
        if (!anuncio) {
            return;
        }
        anuncio.textContent = '';
        window.setTimeout(function () {
            anuncio.textContent = quantidade === 1
                ? '1 nova notícia publicada.'
                : quantidade + ' novas notícias publicadas.';
        }, 50);
    }

    function esconderAviso() {
        if (aviso) {
            aviso.classList.add('d-none');
            aviso.textContent = '';
        }
    }

    function mostrarAviso(controle, texto) {
        if (!aviso) {
            return;
        }
        controle.className = 'btn btn-warning shadow';
        controle.textContent = texto;
        aviso.textContent = '';
        aviso.appendChild(controle);
        aviso.classList.remove('d-none');
    }

    function avisoParaTopo() {
        var botao = document.createElement('button');
        botao.type = 'button';
        botao.addEventListener('click', function () {
            inserirPendentes();
            lista.scrollIntoView({ block: 'start' });
        });
        mostrarAviso(botao, plural(pendentes.length) + ' ↑');
    }

    function avisoParaPrimeiraPagina() {
        var link = document.createElement('a');
        link.href = lista.dataset.urlInicio || '/';
        mostrarAviso(link, plural(novasOutraPagina) + ' — ver na primeira página');
    }

    function idsNaTela() {
        var ids = {};
        lista.querySelectorAll('[data-noticia-id]').forEach(function (cartao) {
            ids[cartao.dataset.noticiaId] = true;
        });
        return ids;
    }

    function usuarioLendoAbaixo() {
        return lista.getBoundingClientRect().top < 0;
    }

    function inserirPendentes() {
        if (!pendentes.length) {
            return;
        }

        var semNoticias = document.getElementById('aviso-sem-noticias');
        if (semNoticias) {
            semNoticias.remove();
        }

        var resultado = window.NapneAoVivo.inserirNoTopo(lista, pendentes, { preservarLeitura: false });
        pendentes = [];
        esconderAviso();
        anunciar(resultado.inseridos);
    }

    function receber(dados) {
        ultimoId = Math.max(ultimoId, dados.ultimo_id || 0);

        if (!dados.total) {
            return;
        }

        if (!primeiraPagina) {
            novasOutraPagina += dados.total;
            avisoParaPrimeiraPagina();
            return;
        }

        var emTela = idsNaTela();
        var emEspera = {};
        pendentes.forEach(function (cartao) {
            emEspera[cartao.dataset.noticiaId] = true;
        });

        var novos = window.NapneAoVivo.converterHtml(dados.html).filter(function (cartao) {
            return !emTela[cartao.dataset.noticiaId] && !emEspera[cartao.dataset.noticiaId];
        });
        pendentes = novos.concat(pendentes);

        if (!pendentes.length) {
            return;
        }

        if (usuarioLendoAbaixo()) {
            avisoParaTopo();
        } else {
            inserirPendentes();
        }
    }

    window.addEventListener('scroll', function () {
        if (pendentes.length && !usuarioLendoAbaixo()) {
            inserirPendentes();
        }
    }, { passive: true });

    window.NapneAoVivo.iniciarConsulta({
        intervalo: intervalo,
        url: function () {
            return lista.dataset.urlNovas + '?desde=' + ultimoId;
        },
        aoReceber: receber
    });
})();
