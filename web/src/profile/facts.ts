import type { components } from "@/api/schema";

export type FactKind = components["schemas"]["FactKind"];
export type FactOut = components["schemas"]["FactOut"];
export type Content = Record<string, unknown>;

export type FieldType = "text" | "textarea" | "date" | "checkbox" | "links";
export type FieldDef = {
  name: string;
  label: string;
  type?: FieldType;
  required?: boolean;
  placeholder?: string;
};

export const KIND_ORDER: FactKind[] = [
  "identity",
  "experience",
  "project",
  "education",
  "certification",
  "skill",
  "language",
];

export const KIND_LABELS: Record<FactKind, { one: string; many: string }> = {
  identity: { one: "Identité", many: "Identité" },
  experience: { one: "Expérience", many: "Expériences" },
  achievement: { one: "Réalisation", many: "Réalisations" },
  project: { one: "Projet", many: "Projets" },
  education: { one: "Formation", many: "Formations" },
  skill: { one: "Compétence", many: "Compétences" },
  language: { one: "Langue", many: "Langues" },
  certification: { one: "Certification", many: "Certifications" },
};

const DATE = { type: "date" as const, placeholder: "AAAA ou AAAA-MM" };

export const FIELDS: Record<FactKind, FieldDef[]> = {
  identity: [
    { name: "full_name", label: "Nom complet", required: true },
    { name: "headline", label: "Titre" },
    { name: "email", label: "E-mail" },
    { name: "phone", label: "Téléphone" },
    { name: "location", label: "Localisation" },
    { name: "links", label: "Liens (un par ligne : libellé | URL)", type: "links" },
  ],
  experience: [
    { name: "title", label: "Intitulé du poste", required: true },
    { name: "employer", label: "Employeur", required: true },
    { name: "start", label: "Début", ...DATE },
    { name: "end", label: "Fin", ...DATE },
    { name: "current", label: "Poste actuel", type: "checkbox" },
    { name: "location", label: "Lieu" },
    { name: "summary", label: "Résumé du poste", type: "textarea" },
  ],
  achievement: [{ name: "text", label: "Réalisation", type: "textarea", required: true }],
  project: [
    { name: "name", label: "Nom", required: true },
    { name: "description", label: "Description", type: "textarea" },
    { name: "url", label: "Lien" },
    { name: "start", label: "Début", ...DATE },
    { name: "end", label: "Fin", ...DATE },
  ],
  education: [
    { name: "degree", label: "Diplôme", required: true },
    { name: "institution", label: "Établissement", required: true },
    { name: "field", label: "Spécialité" },
    { name: "start", label: "Début", ...DATE },
    { name: "end", label: "Fin", ...DATE },
  ],
  skill: [
    { name: "name", label: "Compétence", required: true },
    { name: "category", label: "Catégorie" },
  ],
  language: [
    { name: "name", label: "Langue", required: true },
    { name: "level", label: "Niveau" },
  ],
  certification: [
    { name: "name", label: "Certification", required: true },
    { name: "issuer", label: "Organisme" },
    { name: "date", label: "Date", ...DATE },
  ],
};

/** Champs protégés traduisibles (miroir de TRANSLATABLE_FIELDS côté backend). */
export const TRANSLATABLE: Partial<Record<FactKind, string[]>> = {
  experience: ["employer", "title"],
  education: ["institution", "degree", "field"],
  certification: ["name"],
};
export const TRANSLATION_LANGS = ["en", "fr"] as const;

/** Faits pouvant prouver une compétence (miroir de EVIDENCE_KINDS). */
export const EVIDENCE_KINDS: FactKind[] = [
  "experience",
  "achievement",
  "project",
  "education",
  "certification",
];

const text = (value: unknown) => (typeof value === "string" ? value : "");

function period(content: Content): string {
  const start = text(content.start);
  const end = content.current ? "aujourd'hui" : text(content.end);
  if (!start && !end) return "";
  return ` (${[start, end].filter(Boolean).join(" – ")})`;
}

/** Résumé d'une ligne d'un fait, pour les listes et les choix de preuves. */
export function summarize(kind: FactKind, content: Content): string {
  switch (kind) {
    case "identity":
      return [text(content.full_name), text(content.headline)].filter(Boolean).join(" — ");
    case "experience":
      return `${text(content.title)} — ${text(content.employer)}${period(content)}`;
    case "achievement":
      return text(content.text);
    case "project":
      return `${text(content.name)}${period(content)}`;
    case "education":
      return `${text(content.degree)} — ${text(content.institution)}${period(content)}`;
    case "skill":
      return text(content.name);
    case "language":
      return [text(content.name), text(content.level)].filter(Boolean).join(" — ");
    case "certification":
      return [text(content.name), text(content.issuer)].filter(Boolean).join(" — ");
  }
}
