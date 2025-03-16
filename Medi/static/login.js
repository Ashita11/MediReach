document.querySelectorAll('.eye-icon').forEach(icon => {
    icon.addEventListener('click', () => {
      const passwordField = icon.previousElementSibling;
      if (passwordField.type === 'password') {
        passwordField.type = 'text';
        icon.classList.replace('bx-hide', 'bx-show');
      } else {
        passwordField.type = 'password';
        icon.classList.replace('bx-show', 'bx-hide');
      }
    });
  });
  