/* Ensure file upload fields are visible on DownloadableDocument admin */
(function () {
  function revealFileInputs() {
    var inputs = document.querySelectorAll('input[type="file"]');
    inputs.forEach(function (el) {
      el.style.display = 'block';
      el.style.visibility = 'visible';
      el.style.opacity = '1';
      el.style.width = '100%';
      el.style.maxWidth = '520px';
      el.style.padding = '12px';
      el.style.border = '2px dashed #1a73e8';
      el.style.borderRadius = '10px';
      el.style.background = '#f0f7ff';
      el.style.cursor = 'pointer';
      var wrap = el.closest('.form-group, .fieldBox, .form-row, div');
      if (wrap) {
        wrap.style.display = 'block';
        wrap.style.visibility = 'visible';
      }
    });

    // Jazzmin/Bootstrap sometimes wraps file inputs in .custom-file
    document.querySelectorAll('.custom-file, .custom-file-input').forEach(function (el) {
      el.style.opacity = '1';
      el.style.display = 'block';
      el.style.visibility = 'visible';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', revealFileInputs);
  } else {
    revealFileInputs();
  }
  window.addEventListener('load', revealFileInputs);
})();
