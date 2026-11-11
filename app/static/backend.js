// Solo comportamientos de interfaz. La seguridad y los datos se controlan en el servidor.
document.addEventListener('DOMContentLoaded', () => {
  const menu = document.getElementById('menu-toggle');
  const nav = document.getElementById('main-nav');
  if(menu && nav) menu.addEventListener('click', () => {
    const active = nav.classList.toggle('is-open');
    menu.setAttribute('aria-expanded', String(active));
  });
  const description = document.getElementById('description');
  const counter = document.getElementById('description-counter');
  if(description && counter) description.addEventListener('input', () => counter.textContent = description.value.length + ' / 500 caracteres');
});
