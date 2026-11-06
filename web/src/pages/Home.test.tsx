import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Home } from "./Home";

function renderHome() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Home />
    </QueryClientProvider>,
  );
}

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn(async (_request: Request) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("Home", () => {
  it("affiche l'état du backend en envoyant le jeton", async () => {
    sessionStorage.setItem("tailor.token", "secret");
    const fetchMock = mockFetch(200, { status: "ok", version: "0.1.0", database: "ok" });

    renderHome();

    expect(await screen.findByText(/Backend connecté — version 0.1.0/)).toBeInTheDocument();
    const request = fetchMock.mock.calls[0]![0];
    expect(new URL(request.url).pathname).toBe("/api/health");
    expect(request.headers.get("Authorization")).toBe("Bearer secret");
  });

  it("explique quoi faire quand le jeton est refusé", async () => {
    mockFetch(401, { detail: "Jeton manquant ou invalide." });

    renderHome();

    expect(await screen.findByText(/Jeton absent ou expiré/)).toBeInTheDocument();
  });
});
