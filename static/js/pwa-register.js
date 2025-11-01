// Registrar Service Worker solo para instalación
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/sw.js')
      .then(registration => {
        console.log('PWA registrada para instalación');
      })
      .catch(error => {
        console.log('Error al registrar PWA:', error);
      });
  });
}

// Mostrar botón de instalación
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  
  // Mostrar botón de instalación personalizado
  const installBtn = document.createElement('button');
  installBtn.id = 'install-btn';
  installBtn.innerHTML = '📥 Instalar CommerceBox';
  installBtn.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #4f46e5;
    color: white;
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
    z-index: 9999;
  `;
  
  installBtn.onclick = async () => {
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      installBtn.remove();
    }
    deferredPrompt = null;
  };
  
  document.body.appendChild(installBtn);
});