import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import {
  FIELDS,
  KIND_LABELS,
  TRANSLATABLE,
  TRANSLATION_LANGS,
  type Content,
  type FactKind,
} from "./facts";

export type EvidenceOption = { id: string; label: string };

type Props = {
  kind: FactKind;
  initial?: Content;
  /** Faits pouvant servir de preuve (compétences uniquement). */
  evidenceOptions?: EvidenceOption[];
  submitLabel?: string;
  onSubmit: (content: Content) => Promise<unknown> | void;
  onCancel?: () => void;
};

type Values = Record<string, string | boolean>;
type Translations = Record<string, Record<string, string>>;

function toValues(kind: FactKind, content: Content): Values {
  const values: Values = {};
  for (const field of FIELDS[kind]) {
    const raw = content[field.name];
    if (field.type === "checkbox") values[field.name] = Boolean(raw);
    else if (field.type === "links")
      values[field.name] = ((raw as { label: string; url: string }[]) ?? [])
        .map((link) => `${link.label} | ${link.url}`)
        .join("\n");
    else values[field.name] = typeof raw === "string" ? raw : "";
  }
  return values;
}

function parseLinks(raw: string) {
  return raw
    .split("\n")
    .map((line) => line.split("|").map((part) => part.trim()))
    .filter(([label, url]) => label && url)
    .map(([label, url]) => ({ label, url }));
}

export function FactForm({
  kind,
  initial = {},
  evidenceOptions,
  submitLabel = "Enregistrer",
  onSubmit,
  onCancel,
}: Props) {
  const [values, setValues] = useState<Values>(() => toValues(kind, initial));
  const [translations, setTranslations] = useState<Translations>(
    () => (initial.translations as Translations) ?? {},
  );
  const [evidence, setEvidence] = useState<string[]>(() => (initial.evidence as string[]) ?? []);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const translatable = TRANSLATABLE[kind] ?? [];

  function buildContent(): Content {
    // On part du contenu initial pour ne perdre aucun champ non affiché.
    const content: Content = { ...initial };
    for (const field of FIELDS[kind]) {
      const value = values[field.name];
      if (field.type === "checkbox") content[field.name] = Boolean(value);
      else if (field.type === "links") content[field.name] = parseLinks(String(value));
      else {
        const trimmed = String(value).trim();
        content[field.name] = trimmed === "" && !field.required ? null : trimmed;
      }
    }
    if (translatable.length) {
      const cleaned: Translations = {};
      for (const [lang, fields] of Object.entries(translations)) {
        const kept = Object.fromEntries(Object.entries(fields).filter(([, v]) => v.trim()));
        if (Object.keys(kept).length) cleaned[lang] = kept;
      }
      content.translations = cleaned;
    }
    if (kind === "skill") content.evidence = evidence;
    return content;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await onSubmit(buildContent());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3" aria-label={KIND_LABELS[kind].one}>
      <div className="grid gap-3 sm:grid-cols-2">
        {FIELDS[kind].map((field) => {
          const id = `${kind}-${field.name}`;
          const wide = field.type === "textarea" || field.type === "links";
          if (field.type === "checkbox")
            return (
              <div key={field.name} className="flex items-center gap-2 self-end pb-2">
                <Checkbox
                  id={id}
                  checked={Boolean(values[field.name])}
                  onCheckedChange={(checked) =>
                    setValues((v) => ({ ...v, [field.name]: checked === true }))
                  }
                />
                <Label htmlFor={id}>{field.label}</Label>
              </div>
            );
          const Component = wide ? Textarea : Input;
          return (
            <div key={field.name} className={wide ? "space-y-1 sm:col-span-2" : "space-y-1"}>
              <Label htmlFor={id}>
                {field.label}
                {field.required && " *"}
              </Label>
              <Component
                id={id}
                value={String(values[field.name] ?? "")}
                placeholder={field.placeholder}
                required={field.required}
                onChange={(e: { target: { value: string } }) =>
                  setValues((v) => ({ ...v, [field.name]: e.target.value }))
                }
              />
            </div>
          );
        })}
      </div>

      {translatable.length > 0 && (
        <details className="rounded-md border border-slate-200 p-3 text-sm">
          <summary className="cursor-pointer font-medium">Traductions des champs protégés</summary>
          <p className="mt-2 text-slate-600">
            Ces champs ne sont jamais reformulés par l'IA : dans un CV dans une autre langue, seule
            la traduction saisie ici sera utilisée.
          </p>
          {TRANSLATION_LANGS.map((lang) => (
            <div key={lang} className="mt-3 grid gap-3 sm:grid-cols-2">
              {translatable.map((name) => {
                const id = `${kind}-tr-${lang}-${name}`;
                const label = FIELDS[kind].find((f) => f.name === name)?.label ?? name;
                return (
                  <div key={name} className="space-y-1">
                    <Label htmlFor={id}>
                      {label} ({lang.toUpperCase()})
                    </Label>
                    <Input
                      id={id}
                      value={translations[lang]?.[name] ?? ""}
                      onChange={(e) =>
                        setTranslations((t) => ({
                          ...t,
                          [lang]: { ...t[lang], [name]: e.target.value },
                        }))
                      }
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </details>
      )}

      {kind === "skill" && evidenceOptions && (
        <fieldset className="space-y-2 rounded-md border border-slate-200 p-3 text-sm">
          <legend className="px-1 font-medium">Preuves (ce qui démontre cette compétence)</legend>
          {evidenceOptions.length === 0 && (
            <p className="text-slate-600">Ajoute d'abord une expérience ou un projet.</p>
          )}
          {evidenceOptions.map((option) => (
            <div key={option.id} className="flex items-start gap-2">
              <Checkbox
                id={`evidence-${option.id}`}
                checked={evidence.includes(option.id)}
                onCheckedChange={(checked) =>
                  setEvidence((list) =>
                    checked === true ? [...list, option.id] : list.filter((id) => id !== option.id),
                  )
                }
              />
              <Label htmlFor={`evidence-${option.id}`} className="font-normal">
                {option.label}
              </Label>
            </div>
          ))}
        </fieldset>
      )}

      {error && <p className="text-sm text-red-700">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" disabled={pending}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Annuler
          </Button>
        )}
      </div>
    </form>
  );
}
