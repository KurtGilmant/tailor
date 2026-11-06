import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/helpers";
import type { components } from "@/api/schema";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { getToken } from "@/lib/token";

type Preferences = components["schemas"]["Preferences"];
type Answer = components["schemas"]["AnswerOut"];

const CONTRACTS: [NonNullable<Preferences["contract_types"]>[number], string][] = [
  ["cdi", "CDI"],
  ["cdd", "CDD"],
  ["alternance", "Alternance"],
  ["stage", "Stage"],
  ["freelance", "Freelance"],
  ["interim", "Intérim"],
];
const WORK_MODES: [NonNullable<Preferences["work_modes"]>[number], string][] = [
  ["sur_site", "Sur site"],
  ["hybride", "Hybride"],
  ["teletravail_complet", "Télétravail complet"],
];

const splitList = (raw: string) =>
  raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

export function Settings() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Réglages</h1>
      <PreferencesCard />
      <AnswersCard />
      <DataCard />
    </div>
  );
}

function PreferencesCard() {
  const preferences = useQuery({
    queryKey: ["preferences"],
    queryFn: () => unwrap(api.GET("/api/preferences")),
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle>Préférences de recherche</CardTitle>
        <CardDescription>
          Utilisées pour filtrer les offres et pour répondre aux questions factuelles des
          formulaires, sans jamais passer par l'IA.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {preferences.data ? (
          // Clé = contenu serveur : le formulaire repart des données fraîches quand elles
          // changent (après une suppression totale, il ne doit pas garder l'ancien état).
          <PreferencesForm key={JSON.stringify(preferences.data)} initial={preferences.data} />
        ) : (
          <p>Chargement…</p>
        )}
      </CardContent>
    </Card>
  );
}

function PreferencesForm({ initial }: { initial: Preferences }) {
  const queryClient = useQueryClient();
  const [contracts, setContracts] = useState(initial.contract_types ?? []);
  const [modes, setModes] = useState(initial.work_modes ?? []);
  const [locations, setLocations] = useState((initial.locations ?? []).join(", "));
  const [languages, setLanguages] = useState((initial.work_languages ?? []).join(", "));
  const [excluded, setExcluded] = useState((initial.excluded_companies ?? []).join(", "));
  const [availableFrom, setAvailableFrom] = useState(initial.available_from ?? "");
  const [salaryMin, setSalaryMin] = useState(initial.salary?.min?.toString() ?? "");
  const [salaryMax, setSalaryMax] = useState(initial.salary?.max?.toString() ?? "");
  const [period, setPeriod] = useState(initial.salary?.period ?? "annuel");
  const [authorization, setAuthorization] = useState(initial.work_authorization ?? "");
  const [notice, setNotice] = useState(initial.notice_period ?? "");

  const save = useMutation({
    mutationFn: (body: Preferences) => unwrap(api.PUT("/api/preferences", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["preferences"] }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const hasSalary = salaryMin !== "" || salaryMax !== "";
    save.mutate({
      contract_types: contracts,
      work_modes: modes,
      locations: splitList(locations),
      work_languages: splitList(languages),
      excluded_companies: splitList(excluded),
      available_from: availableFrom || null,
      salary: hasSalary
        ? {
            min: salaryMin ? Number(salaryMin) : null,
            max: salaryMax ? Number(salaryMax) : null,
            currency: "EUR",
            period,
          }
        : null,
      work_authorization: authorization.trim() || null,
      notice_period: notice.trim() || null,
    });
  }

  function toggle<T>(list: T[], value: T, checked: boolean) {
    return checked ? [...list, value] : list.filter((item) => item !== value);
  }

  return (
    <form onSubmit={submit} className="space-y-4" aria-label="Préférences de recherche">
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Types de contrat</legend>
        <div className="flex flex-wrap gap-4">
          {CONTRACTS.map(([value, label]) => (
            <div key={value} className="flex items-center gap-2">
              <Checkbox
                id={`contract-${value}`}
                checked={contracts.includes(value)}
                onCheckedChange={(c) => setContracts((l) => toggle(l, value, c === true))}
              />
              <Label htmlFor={`contract-${value}`} className="font-normal">
                {label}
              </Label>
            </div>
          ))}
        </div>
      </fieldset>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Modes de travail acceptés</legend>
        <div className="flex flex-wrap gap-4">
          {WORK_MODES.map(([value, label]) => (
            <div key={value} className="flex items-center gap-2">
              <Checkbox
                id={`mode-${value}`}
                checked={modes.includes(value)}
                onCheckedChange={(c) => setModes((l) => toggle(l, value, c === true))}
              />
              <Label htmlFor={`mode-${value}`} className="font-normal">
                {label}
              </Label>
            </div>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="locations" label="Lieux (séparés par des virgules)" value={locations} onChange={setLocations} />
        <Field id="available" label="Disponible à partir du" type="date" value={availableFrom} onChange={setAvailableFrom} />
        <Field id="salary-min" label="Prétentions minimales (€)" type="number" value={salaryMin} onChange={setSalaryMin} />
        <Field id="salary-max" label="Prétentions maximales (€)" type="number" value={salaryMax} onChange={setSalaryMax} />
        <div className="space-y-1">
          <Label htmlFor="period">Période</Label>
          <select
            id="period"
            value={period}
            onChange={(e) => setPeriod(e.target.value as typeof period)}
            className="h-9 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
          >
            <option value="annuel">Annuel brut</option>
            <option value="mensuel">Mensuel brut</option>
            <option value="journalier">Journalier (TJM)</option>
          </select>
        </div>
        <Field id="languages" label="Langues de travail" value={languages} onChange={setLanguages} />
        <Field id="authorization" label="Autorisation de travail" value={authorization} onChange={setAuthorization} />
        <Field id="notice" label="Préavis" value={notice} onChange={setNotice} />
        <Field id="excluded" label="Entreprises exclues" value={excluded} onChange={setExcluded} />
      </div>
      {save.error && <p className="text-sm text-red-700">{save.error.message}</p>}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={save.isPending}>
          Enregistrer les préférences
        </Button>
        {save.isSuccess && <span className="text-sm text-emerald-700">Enregistré.</span>}
      </div>
    </form>
  );
}

function Field(props: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={props.id}>{props.label}</Label>
      <Input
        id={props.id}
        type={props.type}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </div>
  );
}

function AnswersCard() {
  const queryClient = useQueryClient();
  const answers = useQuery({ queryKey: ["answers"], queryFn: () => unwrap(api.GET("/api/answers")) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["answers"] });
  const create = useMutation({
    mutationFn: (body: { question: string; answer: string }) =>
      unwrap(api.POST("/api/answers", { body })),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/api/answers/{entry_id}", { params: { path: { entry_id: id } } })),
    onSuccess: refresh,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Banque de réponses</CardTitle>
        <CardDescription>
          Tes réponses aux questions récurrentes des formulaires, réutilisées telles quelles.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {answers.data?.length === 0 && <p className="text-sm text-slate-500">Aucune réponse enregistrée.</p>}
        {answers.data?.map((entry) => (
          <AnswerRow key={entry.id} entry={entry} onDelete={() => remove.mutate(entry.id)} onSaved={refresh} />
        ))}
        <AnswerForm
          submitLabel="Ajouter la réponse"
          onSubmit={(question, answer) => create.mutateAsync({ question, answer })}
        />
      </CardContent>
    </Card>
  );
}

function AnswerRow({ entry, onDelete, onSaved }: { entry: Answer; onDelete: () => void; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  if (editing)
    return (
      <AnswerForm
        initial={entry}
        submitLabel="Enregistrer"
        onCancel={() => setEditing(false)}
        onSubmit={async (question, answer) => {
          await unwrap(
            api.PUT("/api/answers/{entry_id}", {
              params: { path: { entry_id: entry.id } },
              body: { question, answer },
            }),
          );
          setEditing(false);
          onSaved();
        }}
      />
    );
  return (
    <div className="flex items-start justify-between gap-3 rounded-md border border-slate-200 p-3">
      <div className="space-y-1 text-sm">
        <p className="font-medium">{entry.question}</p>
        <p className="whitespace-pre-wrap text-slate-700">{entry.answer}</p>
      </div>
      <div className="flex gap-1">
        <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
          Modifier
        </Button>
        <Button variant="ghost" size="sm" onClick={onDelete}>
          Supprimer
        </Button>
      </div>
    </div>
  );
}

function AnswerForm(props: {
  initial?: Answer;
  submitLabel: string;
  onSubmit: (question: string, answer: string) => Promise<unknown>;
  onCancel?: () => void;
}) {
  const [question, setQuestion] = useState(props.initial?.question ?? "");
  const [answer, setAnswer] = useState(props.initial?.answer ?? "");
  const [error, setError] = useState<string | null>(null);
  const prefix = props.initial ? `answer-${props.initial.id}` : "answer-new";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await props.onSubmit(question, answer);
      if (!props.initial) {
        setQuestion("");
        setAnswer("");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-md border border-dashed border-slate-300 p-3">
      <div className="space-y-1">
        <Label htmlFor={`${prefix}-q`}>Question</Label>
        <Input id={`${prefix}-q`} value={question} onChange={(e) => setQuestion(e.target.value)} required />
      </div>
      <div className="space-y-1">
        <Label htmlFor={`${prefix}-a`}>Réponse</Label>
        <Textarea id={`${prefix}-a`} value={answer} onChange={(e) => setAnswer(e.target.value)} required />
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" size="sm">
          {props.submitLabel}
        </Button>
        {props.onCancel && (
          <Button type="button" size="sm" variant="outline" onClick={props.onCancel}>
            Annuler
          </Button>
        )}
      </div>
    </form>
  );
}

function DataCard() {
  const queryClient = useQueryClient();
  const [confirmation, setConfirmation] = useState("");
  const wipe = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/data/delete", { body: { confirmation: "SUPPRIMER" } })),
    onSuccess: () => {
      setConfirmation("");
      return queryClient.invalidateQueries();
    },
  });

  async function exportData() {
    const response = await fetch("/api/data/export", {
      headers: { Authorization: `Bearer ${getToken() ?? ""}` },
    });
    const url = URL.createObjectURL(await response.blob());
    const link = Object.assign(document.createElement("a"), { href: url, download: "tailor-export.json" });
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Données</CardTitle>
        <CardDescription>
          Tout est stocké sur ta machine. L'export contient l'intégralité de tes données au format
          JSON documenté (docs/export.md).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button variant="outline" onClick={exportData}>
          Exporter toutes mes données
        </Button>
        <div className="space-y-2 rounded-md border border-red-200 bg-red-50 p-3">
          <p className="text-sm font-medium text-red-900">Tout supprimer</p>
          <p className="text-sm text-red-800">
            Efface définitivement le profil, les préférences, les réponses, le journal et les fichiers
            générés. Tape <strong>SUPPRIMER</strong> pour confirmer.
          </p>
          <div className="flex flex-wrap gap-2">
            <Input
              aria-label="Confirmation de suppression"
              className="max-w-48 bg-white"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
            />
            <Button
              variant="destructive"
              disabled={confirmation !== "SUPPRIMER" || wipe.isPending}
              onClick={() => wipe.mutate()}
            >
              Supprimer définitivement
            </Button>
          </div>
          {wipe.isSuccess && <p className="text-sm text-red-900">Toutes les données ont été effacées.</p>}
          {wipe.error && <p className="text-sm text-red-900">{wipe.error.message}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
