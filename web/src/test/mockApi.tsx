import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";

type Reply = { status?: number; body?: unknown };
/** Une fonction du corps de requête, ou directement la réponse ({status, body} ou corps). */
type Handler = ((body: unknown) => unknown) | unknown;
export type Call = { key: string; body: unknown };

/** Remplace fetch par un faux backend : clés « MÉTHODE /chemin ». */
export function mockApi(routes: Record<string, Handler>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = input instanceof Request ? input : new Request(new URL(input, location.origin), init);
      const key = `${request.method} ${new URL(request.url).pathname}`;
      const raw = request.headers.get("content-type")?.includes("json") ? await request.text() : "";
      const body = raw ? JSON.parse(raw) : undefined;
      calls.push({ key, body });
      const handler = routes[key];
      if (handler === undefined) return json({ detail: `route non simulée : ${key}` }, 404);
      const result = typeof handler === "function" ? handler(body) : handler;
      const reply: Reply =
        result && typeof result === "object" && ("status" in result || "body" in result)
          ? (result as Reply)
          : { body: result };
      return json(reply.body, reply.status ?? 200);
    }),
  );
  return calls;
}

function json(body: unknown, status: number) {
  if (status === 204) return new Response(null, { status });
  return new Response(JSON.stringify(body ?? null), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function renderWithProviders(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}
