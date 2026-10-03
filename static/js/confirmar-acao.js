(function () {
    'use strict';

    document.addEventListener('submit', function (evento) {
        var formulario = evento.target;

        if (!(formulario instanceof HTMLFormElement)) {
            return;
        }

        var mensagem = formulario.dataset.confirmar;

        if (mensagem && !window.confirm(mensagem)) {
            evento.preventDefault();
        }
    });
})();
