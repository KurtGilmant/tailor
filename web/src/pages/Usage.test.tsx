import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Usage } from "./Usage";

const anthropic = {
  name: "anthropic",
  type: "anthropic",
  is_cloud: true,
  api_key_configured: true,
  consent_granted_at: null as string | null,
};

const status = () => ({
  mode: "standard",
  monthly_budget_usd: 10,
  month_spend_usd: 2.5,
  providers: [anthropic, { ...anthropic, name: "ollama", is_cloud: false }],
  routes: [{ task: "write", provider: "anthropic", model: "claude-opus-5-5", effort: "high" }],
});

const usage = {
  month_spend_usd: 2.5,
  monthly_budget_usd: 10,
  daily: [
    { day: "2026-11-06", task: "write", calls: 3, input_tokens: 1200, output_tokens: 400, cost_usd: 2.5 },
  ],
  recent: [
    {
      id: 1,
      created_at: "2026-11-06T10:00:00Z",
      task: "write",
      provider: "anthropic",
      model: "claude-opus-5-5",
      prompt_id: "cv-bullets",
      prompt_version: "1-abcd1234",
      input_tokens: 400,
      output_tokens: 120,
      cost_usd: 0.0064,
      duration_ms: 1530,
      status: "invalid",
      error: "- age : Input should be a valid integer",
    },
  ],
};

function json(body: unknown, statusCode = 200) {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}

function mockBackend() {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      calls.push(`${request.method} ${path}`);
      if (path === "/api/llm/status") return json(status());
      if (path === "/api/llm/usage") return json(usage);
      if (path === "/api/llm/consents/anthropic" && request.method === "POST") {
        anthropic.consent_granted_at = "2026-11-06T11:00:00Z";
        return json({ ...anthropic }, 201);
      }
      return json({ detail: "inconnu" }, 404);
    }),
  );
  return calls;
}

function renderUsage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Usage />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  anthropic.consent_granted_at = null;
});

describe("Usage", () => {
  it("affiche coût du mois, plafond, routage et appels récents", async () => {
    mockBackend();
    renderUsage();

    expect(await screen.findByText("Consommation des modèles")).toBeInTheDocument();
    expect(screen.getByText(/Plafond mensuel/)).toHaveTextContent("10,00");
    expect(screen.getByText("Hors schéma")).toBeInTheDocument();
    expect(screen.getByText("cv-bullets@1-abcd1234")).toBeInTheDocument();
    // Seuls les fournisseurs cloud demandent un consentement.
    expect(screen.queryByText("Autoriser l'envoi à ollama")).not.toBeInTheDocument();
  });

  it("enregistre le consentement puis rafraîchit l'état", async () => {
    const calls = mockBackend();
    renderUsage();

    fireEvent.click(await screen.findByRole("button", { name: "Autoriser l'envoi à anthropic" }));

    expect(await screen.findByRole("button", { name: "Retirer l'autorisation" })).toBeInTheDocument();
    await waitFor(() => expect(calls).toContain("POST /api/llm/consents/anthropic"));
    expect(calls.filter((c) => c === "GET /api/llm/status")).toHaveLength(2);
  });
});
