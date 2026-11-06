const STORAGE_KEY = "tailor.token";

/**
 * Récupère le jeton de lancement passé par `tailor` dans l'URL (`?token=…`),
 * le conserve pour la session de l'onglet, puis le retire de la barre d'adresse
 * pour qu'il ne traîne ni dans l'historique ni dans une capture d'écran.
 */
export function captureToken(): string | null {
  const url = new URL(window.location.href);
  const fromUrl = url.searchParams.get("token");
  if (fromUrl) {
    sessionStorage.setItem(STORAGE_KEY, fromUrl);
    url.searchParams.delete("token");
    window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
  }
  return getToken();
}

export function getToken(): string | null {
  return sessionStorage.getItem(STORAGE_KEY);
}
