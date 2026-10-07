// Pré-visualização da foto escolhida nos formulários
document.querySelectorAll('input[type="file"][data-preview]').forEach(function (input) {
  var img = document.getElementById(input.dataset.preview);
  input.addEventListener('change', function () {
    if (input.files && input.files[0]) { img.src = URL.createObjectURL(input.files[0]); }
  });
  // botão "Limpar" volta a pré-visualização ao estado original
  if (input.form) {
    input.form.addEventListener('reset', function () { img.src = img.dataset.original; });
  }
});

// Confirmação antes de excluir (formulários com data-confirm)
document.querySelectorAll('form[data-confirm]').forEach(function (form) {
  form.addEventListener('submit', function (e) {
    if (!confirm(form.dataset.confirm)) { e.preventDefault(); }
  });
});
