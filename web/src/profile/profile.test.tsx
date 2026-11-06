import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { mockApi, renderWithProviders } from "@/test/mockApi";

import { FactForm } from "./FactForm";
import { ImportReview } from "./ImportReview";

afterEach(() => vi.unstubAllGlobals());

describe("FactForm", () => {
  it("normalise le contenu : champs vides à null, traductions, liens", async () => {
    const onSubmit = vi.fn();
    render(
      <FactForm
        kind="experience"
        initial={{ employer: "Acme", title: "Stagiaire", start: "2024", extra: "conservé" }}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText("Lieu"), { target: { value: "   " } });
    fireEvent.change(screen.getByLabelText("Intitulé du poste (EN)"), { target: { value: "Intern" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    const content = onSubmit.mock.calls[0]![0];
    expect(content).toMatchObject({
      employer: "Acme",
      title: "Stagiaire",
      start: "2024",
      end: null,
      location: null,
      current: false,
      extra: "conservé",
      translations: { en: { title: "Intern" } },
    });
  });

  it("affiche l'erreur renvoyée par l'enregistrement", async () => {
    render(
      <FactForm
        kind="language"
        initial={{ name: "Anglais" }}
        onSubmit={() => Promise.reject(new Error("Contenu invalide"))}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Contenu invalide")).toBeInTheDocument();
  });

  it("choisit les preuves d'une compétence", async () => {
    const onSubmit = vi.fn();
    render(
      <FactForm
        kind="skill"
        initial={{ name: "SQL" }}
        evidenceOptions={[{ id: "f1", label: "Data engineer — Acme" }]}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByLabelText("Data engineer — Acme"));
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(onSubmit.mock.calls[0]![0].evidence).toEqual(["f1"]));
  });
});

const IMPORT = {
  id: "imp1",
  filename: "cv.pdf",
  created_at: "2026-11-06T10:00:00Z",
  status: "draft",
  draft: {
    items: [
      {
        ref: "exp1",
        kind: "experience" as const,
        content: { employer: "Acme", title: "Data engineer" },
        source_excerpt: "Data engineer — Acme",
        keep: true,
      },
      {
        ref: "exp1.a1",
        kind: "achievement" as const,
        parent_ref: "exp1",
        content: { text: "Réduction de 20 % du temps" },
        source_excerpt: "• Réduction de 20 % du temps",
        keep: true,
      },
      {
        ref: "edu1",
        kind: "education" as const,
        content: { degree: "Master IA", institution: "Université" },
        source_excerpt: "Master IA — Université",
        keep: true,
      },
    ],
    rejected: [
      {
        kind: "skill" as const,
        content: { name: "Kubernetes" },
        source_excerpt: "Kubernetes avancé",
        reason: "passage introuvable tel quel dans le CV",
      },
    ],
    warnings: [],
  },
};

describe("ImportReview", () => {
  it("montre chaque élément à côté de son passage et les éléments écartés", () => {
    mockApi({});
    renderWithProviders(<ImportReview cvImport={IMPORT} />);

    expect(screen.getByText("• Réduction de 20 % du temps")).toBeInTheDocument();
    expect(screen.getByText(/1 élément\(s\) écarté\(s\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ajouter 3 élément(s) à mon profil" })).toBeEnabled();
  });

  it("décocher une expérience écarte aussi ses réalisations, puis valide la sélection", async () => {
    const calls = mockApi({
      "POST /api/profile/imports/imp1/validate": { body: { version: 1, facts: [] } },
    });
    renderWithProviders(<ImportReview cvImport={IMPORT} />);

    fireEvent.click(screen.getByRole("checkbox", { name: "Garder : Data engineer — Acme" }));
    expect(screen.getByRole("checkbox", { name: "Garder : Réduction de 20 % du temps" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Ajouter 1 élément(s) à mon profil" }));

    await waitFor(() => expect(calls.map((c) => c.key)).toContain("POST /api/profile/imports/imp1/validate"));
    const sent = calls.find((c) => c.key.endsWith("/validate"))!.body as { items: { ref: string; keep: boolean }[] };
    expect(sent.items.find((i) => i.ref === "exp1")!.keep).toBe(false);
  });

  it("corrige un élément avant validation", async () => {
    mockApi({});
    renderWithProviders(<ImportReview cvImport={IMPORT} />);

    const keep = screen.getByRole("checkbox", { name: "Garder : Master IA — Université" });
    const education = keep.closest("div.grid") as HTMLElement;
    fireEvent.click(within(education).getByRole("button", { name: "Corriger" }));
    fireEvent.change(screen.getByLabelText("Diplôme *"), { target: { value: "Master Intelligence artificielle" } });
    fireEvent.click(screen.getByRole("button", { name: "Appliquer" }));

    expect(await screen.findByText("Master Intelligence artificielle — Université")).toBeInTheDocument();
  });
});
