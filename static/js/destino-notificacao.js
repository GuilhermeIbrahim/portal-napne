(function () {
    'use strict';

    var campoDestino = document.getElementById('id_destino_tipo');
    var divDestinatario = document.getElementById('div_destinatario');

    if (!campoDestino || !divDestinatario) {
        return;
    }

    function atualizarVisibilidadeDestinatario() {
        divDestinatario.classList.toggle('d-none', campoDestino.value !== 'usuario');
    }

    atualizarVisibilidadeDestinatario();
    campoDestino.addEventListener('change', atualizarVisibilidadeDestinatario);
})();
