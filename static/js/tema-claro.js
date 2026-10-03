(function () {
    'use strict';

    var raiz = document.documentElement;

    raiz.setAttribute('data-lte-color-mode', 'off');
    raiz.setAttribute('data-bs-theme', 'light');
    raiz.style.colorScheme = 'light';

    try {
        localStorage.removeItem('lte-theme');
    } catch (erro) {

    }
})();