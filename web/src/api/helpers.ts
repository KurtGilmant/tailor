import { getToken } from "@/lib/token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
  }
}

type ApiResult<T> = { data?: T; error?: unknown; response: Response };

/** Renvoie les données d'un appel openapi-fetch, ou lève une ApiError lisible. */
export async function unwrap<T>(call: Promise<ApiResult<T>>): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok) throw toApiError(response.status, error);
  return data as T;
}

function toApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === "object" && "detail" in body) {
    const { detail, code } = body as { detail: unknown; code?: string };
    if (typeof detail === "string") return new ApiError(status, detail, code);
    if (Array.isArray(detail)) {
      // Erreurs de validation FastAPI : [{loc, msg}, …]
      const messages = detail.map((d: { loc?: unknown[]; msg?: string }) =>
        [d.loc?.slice(1).join("."), d.msg].filter(Boolean).join(" : "),
      );
      return new ApiError(status, messages.join(" ; "), code);
    }
  }
  return new ApiError(status, `Erreur HTTP ${status}`);
}

/** Envoi multipart (non couvert par le client typé) avec le jeton de lancement. */
export async function postFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(path, {
    method: "POST",
    body: form,
    headers: { Authorization: `Bearer ${getToken() ?? ""}` },
  });
  const body = await response.json().catch(() => undefined);
  if (!response.ok) throw toApiError(response.status, body);
  return body as T;
}
