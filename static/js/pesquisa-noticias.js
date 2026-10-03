(function () {
    'use strict';

    var campoPesquisa = document.getElementById('campo-pesquisa');
    var caixaSugestoes = document.getElementById('sugestoes-pesquisa');

    if (!campoPesquisa || !caixaSugestoes) {
        return;
    }

    var urlPesquisa = campoPesquisa.dataset.urlPesquisa;
    var temporizador = null;

    function esconderSugestoes() {
        caixaSugestoes.classList.add('d-none');
        caixaSugestoes.innerHTML = '';
    }

    function mostrarSugestoes(resultados) {
        caixaSugestoes.innerHTML = '';

        if (resultados.length === 0) {
            var vazio = document.createElement('div');
            vazio.className = 'list-group-item text-muted';
            vazio.textContent = 'Nenhuma notícia encontrada.';
            caixaSugestoes.appendChild(vazio);
        } else {
            resultados.forEach(function (noticia) {
                var link = document.createElement('a');
                link.href = noticia.url;
                link.className = 'list-group-item list-group-item-action';
                link.textContent = noticia.titulo;
                caixaSugestoes.appendChild(link);
            });
        }

        caixaSugestoes.classList.remove('d-none');
    }

    function buscarNoticias(termo) {
        fetch(urlPesquisa + '?q=' + encodeURIComponent(termo))
            .then(function (resposta) {
                return resposta.json();
            })
            .then(function (dados) {
                mostrarSugestoes(dados.resultados);
            })
            .catch(function (erro) {
                console.error('Erro ao pesquisar notícias:', erro);
            });
    }

    campoPesquisa.addEventListener('input', function () {
        var termo = campoPesquisa.value.trim();

        clearTimeout(temporizador);

        if (termo.length === 0) {
            esconderSugestoes();
            return;
        }

        temporizador = setTimeout(function () {
            buscarNoticias(termo);
        }, 300);
    });

    document.addEventListener('click', function (evento) {
        var cliqueFora = !campoPesquisa.contains(evento.target) &&
                         !caixaSugestoes.contains(evento.target);
        if (cliqueFora) {
            caixaSugestoes.classList.add('d-none');
        }
    });

    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape') {
            caixaSugestoes.classList.add('d-none');
        }
    });
})();
