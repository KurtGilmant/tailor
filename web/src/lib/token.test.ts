import { describe, expect, it } from "vitest";

import { captureToken, getToken } from "./token";

describe("captureToken", () => {
  it("garde le jeton de l'URL et le retire de la barre d'adresse", () => {
    window.history.replaceState(null, "", "/offres?token=abc123&tri=score#haut");

    expect(captureToken()).toBe("abc123");
    expect(getToken()).toBe("abc123");
    expect(window.location.pathname + window.location.search + window.location.hash).toBe(
      "/offres?tri=score#haut",
    );
  });

  it("réutilise le jeton de la session quand l'URL n'en a pas", () => {
    window.history.replaceState(null, "", "/?token=first");
    captureToken();
    window.history.replaceState(null, "", "/profil");

    expect(captureToken()).toBe("first");
  });

  it("renvoie null sans jeton", () => {
    window.history.replaceState(null, "", "/");
    expect(captureToken()).toBeNull();
  });
});
