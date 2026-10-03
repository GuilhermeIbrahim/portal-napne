(function () {
    'use strict';

    var REGRAS = {
        'tamanho': function (valor) { return valor.length >= 8; },
        'nao-numerica': function (valor) { return valor.length > 0 && !/^\d+$/.test(valor); }
    };

    function adicionarBotaoMostrar(campo) {
        var grupo = document.createElement('div');
        grupo.className = 'input-group';
        campo.parentNode.insertBefore(grupo, campo);
        grupo.appendChild(campo);

        var botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'btn btn-outline-secondary';
        botao.setAttribute('aria-label', 'Mostrar senha');
        botao.innerHTML = '<i class="bi bi-eye" aria-hidden="true"></i>';
        grupo.appendChild(botao);

        botao.addEventListener('click', function () {
            var mostrando = campo.type === 'text';
            campo.type = mostrando ? 'password' : 'text';
            botao.setAttribute('aria-label', mostrando ? 'Mostrar senha' : 'Ocultar senha');
            botao.firstElementChild.className = mostrando ? 'bi bi-eye' : 'bi bi-eye-slash';
        });
    }

    function ligarRegras(campo, quadro) {
        var itens = quadro.querySelectorAll('li[data-regra]');

        function atualizar() {
            var valor = campo.value;
            itens.forEach(function (item) {
                var regra = REGRAS[item.dataset.regra];
                if (!regra) {
                    return;
                }
                var ok = regra(valor);
                var icone = item.querySelector('i');
                item.classList.toggle('regra-ok', ok);
                icone.className = ok ? 'bi bi-check-circle-fill' : 'bi bi-circle';
            });
        }

        campo.addEventListener('input', atualizar);
        atualizar();
    }

    document.querySelectorAll('input[type="password"][data-mostrar-senha]').forEach(function (campo) {
        adicionarBotaoMostrar(campo);

        var seletor = campo.dataset.regrasSenha;
        var quadro = seletor ? document.querySelector(seletor) : null;
        if (quadro) {
            ligarRegras(campo, quadro);
        }
    });
})();
