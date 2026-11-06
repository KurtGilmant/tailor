import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { mockApi, renderWithProviders } from "@/test/mockApi";

import { Settings } from "./Settings";

afterEach(() => vi.unstubAllGlobals());

const EMPTY_PREFS = { contract_types: [], locations: [], work_modes: [], work_languages: [], excluded_companies: [] };

describe("Settings", () => {
  it("enregistre les préférences saisies", async () => {
    const calls = mockApi({
      "GET /api/preferences": EMPTY_PREFS,
      "PUT /api/preferences": (body: unknown) => body,
      "GET /api/answers": [],
    });
    renderWithProviders(<Settings />);

    fireEvent.click(await screen.findByLabelText("Alternance"));
    fireEvent.click(screen.getByLabelText("Télétravail complet"));
    fireEvent.change(screen.getByLabelText("Lieux (séparés par des virgules)"), {
      target: { value: "Bordeaux, Toulouse " },
    });
    fireEvent.change(screen.getByLabelText("Disponible à partir du"), { target: { value: "2027-09-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer les préférences" }));

    await waitFor(() => expect(calls.some((c) => c.key === "PUT /api/preferences")).toBe(true));
    const body = calls.find((c) => c.key === "PUT /api/preferences")!.body;
    expect(body).toMatchObject({
      contract_types: ["alternance"],
      work_modes: ["teletravail_complet"],
      locations: ["Bordeaux", "Toulouse"],
      available_from: "2027-09-01",
      salary: null,
    });
  });

  it("n'autorise la suppression totale qu'après avoir tapé SUPPRIMER", async () => {
    const calls = mockApi({
      "GET /api/preferences": EMPTY_PREFS,
      "GET /api/answers": [],
      "POST /api/data/delete": { status: 204 },
    });
    renderWithProviders(<Settings />);

    const button = screen.getByRole("button", { name: "Supprimer définitivement" });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Confirmation de suppression"), { target: { value: "supprimer" } });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Confirmation de suppression"), { target: { value: "SUPPRIMER" } });
    fireEvent.click(button);

    expect(await screen.findByText("Toutes les données ont été effacées.")).toBeInTheDocument();
    expect(calls.find((c) => c.key === "POST /api/data/delete")!.body).toEqual({ confirmation: "SUPPRIMER" });
  });

  it("le formulaire de préférences reflète les données après une suppression", async () => {
    let prefs: object = { ...EMPTY_PREFS, contract_types: ["alternance"], locations: ["Bordeaux"] };
    mockApi({
      "GET /api/preferences": () => prefs,
      "GET /api/answers": [],
      "POST /api/data/delete": () => {
        prefs = EMPTY_PREFS;
        return { status: 204 };
      },
    });
    renderWithProviders(<Settings />);

    expect(await screen.findByLabelText("Lieux (séparés par des virgules)")).toHaveValue("Bordeaux");
    fireEvent.change(screen.getByLabelText("Confirmation de suppression"), { target: { value: "SUPPRIMER" } });
    fireEvent.click(screen.getByRole("button", { name: "Supprimer définitivement" }));

    await waitFor(() => expect(screen.getByLabelText("Lieux (séparés par des virgules)")).toHaveValue(""));
    expect(screen.getByRole("checkbox", { name: "Alternance" })).not.toBeChecked();
  });
});
