import createClient, { type Middleware } from "openapi-fetch";

import { getToken } from "@/lib/token";

import type { paths } from "./schema";

const withToken: Middleware = {
  onRequest({ request }) {
    const token = getToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
};

/** Client typé généré depuis l'OpenAPI du backend (`make api-client`). */
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  // Résolu à chaque appel (et non capturé à l'import) pour rester remplaçable dans les tests.
  fetch: (request) => globalThis.fetch(request),
});
api.use(withToken);
