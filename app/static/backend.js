// Solo comportamientos de interfaz. La seguridad y los datos se controlan en el servidor.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-history-back]').forEach((button) => {
    button.addEventListener('click', () => {
      if (window.history.length > 1) window.history.back();
      else window.location.assign('/');
    });
  });
  const menu = document.getElementById('menu-toggle');
  const nav = document.getElementById('main-nav');
  if(menu && nav) menu.addEventListener('click', () => {
    const active = nav.classList.toggle('is-open');
    menu.setAttribute('aria-expanded', String(active));
  });
  const description = document.getElementById('description');
  const counter = document.getElementById('description-counter');
  if(description && counter) {
    const updateCounter = () => { counter.textContent = description.value.length + ' / 500 caracteres'; };
    description.addEventListener('input', updateCounter);
    updateCounter();
  }

  // Los formularios muestran sus errores dentro de la misma página antes de enviar.
  document.querySelectorAll('form.real-form').forEach((form) => {
    form.noValidate = true;
    const summary = document.createElement('div');
    summary.className = 'form-error form-error-summary';
    summary.setAttribute('role', 'alert');
    summary.setAttribute('aria-live', 'assertive');
    summary.setAttribute('tabindex', '-1');
    summary.hidden = true;
    form.prepend(summary);

    const clearErrors = () => {
      form.querySelectorAll('.client-field-error').forEach((node) => node.remove());
      form.querySelectorAll('[aria-invalid="true"]').forEach((node) => node.removeAttribute('aria-invalid'));
      summary.hidden = true;
      summary.textContent = '';
    };

    const fieldName = (control) => {
      const field = control.closest('.field');
      const label = field?.querySelector('label') || control.labels?.[0];
      return label?.textContent?.replace(/\s+/g, ' ').trim() ||
        control.closest('fieldset')?.querySelector('legend')?.textContent?.trim() || 'este campo';
    };

    const validityMessage = (control) => {
      const name = fieldName(control);
      if (control.validity.valueMissing) return `Debes completar «${name}».`;
      if (control.validity.typeMismatch) return `Ingresa un correo válido en «${name}».`;
      if (control.validity.tooShort) return `«${name}» necesita al menos ${control.minLength} caracteres.`;
      if (control.validity.tooLong) return `«${name}» permite un máximo de ${control.maxLength} caracteres.`;
      if (control.validity.patternMismatch || control.validity.badInput) return `Revisa el valor de «${name}».`;
      return `Revisa «${name}» antes de continuar.`;
    };

    form.addEventListener('input', clearErrors);
    form.addEventListener('change', clearErrors);
    form.addEventListener('submit', (event) => {
      clearErrors();
      const problems = [];
      const checkedRadios = new Set();
      const addProblem = (control, message) => {
        if (problems.some((item) => item.control === control)) return;
        problems.push({control, message});
        control.setAttribute('aria-invalid', 'true');
        const field = control.closest('.field') || control.closest('fieldset') || control.parentElement;
        const feedback = document.createElement('small');
        feedback.className = 'client-field-error';
        feedback.textContent = message;
        field?.append(feedback);
      };

      form.querySelectorAll('input, select, textarea').forEach((control) => {
        if (control.disabled || control.type === 'hidden' || control.type === 'submit') return;
        if (control.type === 'radio') {
          if (checkedRadios.has(control.name)) return;
          checkedRadios.add(control.name);
        }
        if (!control.checkValidity()) addProblem(control, validityMessage(control));
        // minlength no siempre se aplica a valores rellenados por código o restaurados.
        if (control.minLength > 0 && control.value.trim() && control.value.trim().length < control.minLength) {
          addProblem(control, `«${fieldName(control)}» necesita al menos ${control.minLength} caracteres.`);
        }
        if (control.dataset.passwordPolicy === 'complex' && control.value.length >= 12) {
          const password = control.value;
          if (!/\p{Lu}/u.test(password) || !/\p{Ll}/u.test(password) ||
              !/\p{Nd}/u.test(password) || !/[^\p{L}\p{N}\s]/u.test(password)) {
            addProblem(control, 'La contraseña debe incluir una mayúscula, una minúscula, un número y un símbolo (por ejemplo, ! o #).');
          }
        }
      });

      if (form.action.endsWith('/solicitud')) {
        const name = form.querySelector('#contact_name');
        const email = form.querySelector('#contact_email');
        const consent = form.querySelector('#contact_consent');
        if (name && email && consent && (name.value.trim() || email.value.trim())) {
          if (!email.value.trim()) addProblem(email, 'Para dejar un contacto, debes ingresar un correo válido.');
          if (!consent.checked) addProblem(consent, 'Te faltó aceptar el consentimiento para guardar tus datos de contacto.');
        }
        const attachment = form.querySelector('#attachment');
        const file = attachment?.files?.[0];
        if (file && file.size > 2 * 1024 * 1024) {
          addProblem(attachment, 'El archivo supera el máximo permitido de 2 MB.');
        }
        if (file && !/\.(pdf|png|jpe?g)$/i.test(file.name)) {
          addProblem(attachment, 'Adjunta únicamente archivos PDF, PNG o JPG.');
        }
      }

      if (problems.length) {
        event.preventDefault();
        summary.textContent = problems.length === 1 ? problems[0].message :
          `Encontramos ${problems.length} campos por corregir. Revisa los mensajes que aparecen debajo de ellos.`;
        summary.hidden = false;
        problems[0].control.focus();
        summary.scrollIntoView({behavior: 'smooth', block: 'center'});
      }
    });
  });

  // Al usar Atrás/Adelante, nunca volver a mostrar un panel guardado en memoria
  // sin consultar al servidor si la sesión sigue siendo válida.
  if (document.body.dataset.protectedArea === 'true') {
    const hidePrivateContent = () => document.body.classList.add('private-page-hidden');
    const showPrivateContent = () => document.body.classList.remove('private-page-hidden');

    window.addEventListener('pagehide', hidePrivateContent);
    window.addEventListener('pageshow', async () => {
      hidePrivateContent();
      try {
        const response = await fetch('/funcionarios/sesion-actual', {
          method: 'GET', credentials: 'same-origin', cache: 'no-store'
        });
        if (response.status !== 204) {
          window.location.replace('/funcionarios/login?sesion=finalizada');
          return;
        }
        showPrivateContent();
      } catch (_error) {
        // Si no se puede comprobar la sesión, se falla de forma segura.
        window.location.replace('/funcionarios/login?sesion=finalizada');
      }
    });
  }
});
