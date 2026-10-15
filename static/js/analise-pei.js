(function () {
    'use strict';

    var formulario = document.getElementById('form-analise-pei');
    if (!formulario) {
        return;
    }

    var parecer = formulario.querySelector('textarea[name="parecer"]');
    var rotulo = formulario.querySelector('label[for="' + (parecer && parecer.id) + '"]');
    var opcoes = formulario.querySelectorAll('input[name="decisao"]');

    if (!parecer || !opcoes.length) {
        return;
    }

    var decisoesQueExigem = (parecer.dataset.obrigatorioPara || '').split(',');
    var MENSAGEM_PARECER = 'O parecer é obrigatório ao devolver ou solicitar ajustes.';

    function validarParecer() {
        var faltando = parecer.required && !parecer.value.trim();
        parecer.setCustomValidity(faltando ? MENSAGEM_PARECER : '');
    }

    function atualizar() {
        var escolhida = formulario.querySelector('input[name="decisao"]:checked');
        var obrigatorio = !!escolhida && decisoesQueExigem.indexOf(escolhida.value) !== -1;

        parecer.required = obrigatorio;
        parecer.setAttribute('aria-required', obrigatorio ? 'true' : 'false');
        validarParecer();

        if (rotulo) {
            rotulo.dataset.textoOriginal = rotulo.dataset.textoOriginal || rotulo.textContent.replace(/\s*\*\s*$/, '').trim();
            rotulo.textContent = rotulo.dataset.textoOriginal + (obrigatorio ? ' *' : ' (opcional)');
        }
    }

    opcoes.forEach(function (opcao) {
        opcao.addEventListener('change', atualizar);
    });
    parecer.addEventListener('input', validarParecer);
    atualizar();
})();
