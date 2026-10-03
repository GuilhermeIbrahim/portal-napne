(function () {
    'use strict';

    function esconderSeQuebrada(img) {
        if (img.complete && img.naturalWidth === 0) {
            img.classList.add('d-none');
        }
    }

    document.querySelectorAll('img.logo-napne').forEach(function (img) {
        esconderSeQuebrada(img);
        img.addEventListener('error', function () {
            img.classList.add('d-none');
        });
    });
})();