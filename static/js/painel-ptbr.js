(function () {
    'use strict';

    var LINKS_DE_PULO = {
        'Skip to main content': 'Pular para o conteúdo principal',
        'Skip to navigation': 'Pular para a navegação'
    };

    function traduzir() {
        document.querySelectorAll('.required-indicator').forEach(function (indicador) {
            var rotulo = indicador.closest('label');
            var campo = rotulo && rotulo.control;

            if (campo && (campo.type === 'radio' || campo.type === 'checkbox')) {
                indicador.remove();
            } else {
                indicador.textContent = ' (obrigatório)';
            }
        });

        document.querySelectorAll('.skip-links a').forEach(function (link) {
            var traducao = LINKS_DE_PULO[link.textContent.trim()];
            if (traducao) {
                link.textContent = traducao;
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', traduzir);
    } else {
        traduzir();
    }
})();
