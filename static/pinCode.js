function checkPinAuth() {
  // 1. Проверяем, действительна ли авторизация
  const authExpiry = localStorage.getItem('authorized');
  const now = Date.now();

  // Если авторизация есть и не истекла - пропускаем
  if (authExpiry && now < parseInt(authExpiry)) return;

  // 2. Подготавливаем URL для возврата после ввода пин-кода
  if (localStorage.getItem("globalPin") == null) {
    return
  }
  const currentPath = window.location.pathname + window.location.search;
  const redirectUrl = currentPath.startsWith('/pinCode') ? '/' : currentPath;

  // 3. Перенаправляем на страницу пин-кода с текущим URL
  if (!window.location.href.includes('/pinCode')) {
    window.location.href = `/pinCode?redirect=${encodeURIComponent(redirectUrl)}`;
  }
}

// Запускаем проверку при загрузке страницы
checkPinAuth();