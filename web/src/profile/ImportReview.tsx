import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/helpers";
import type { components } from "@/api/schema";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

import { FactForm } from "./FactForm";
import { EVIDENCE_KINDS, KIND_LABELS, KIND_ORDER, summarize, type Content } from "./facts";

type ImportOut = components["schemas"]["ImportOut"];
type DraftItem = components["schemas"]["DraftItem"];

export function ImportReview({ cvImport }: { cvImport: ImportOut }) {
  const queryClient = useQueryClient();
  const { items: draftItems = [], rejected = [], warnings = [] } = cvImport.draft;
  const [items, setItems] = useState<DraftItem[]>(draftItems);
  const [editing, setEditing] = useState<string | null>(null);
  const path = { params: { path: { import_id: cvImport.id } } };

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["profile"] });
  const validate = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/profile/imports/{import_id}/validate", { ...path, body: { items } })),
    // La réponse est le profil à jour : on l'installe directement pour éviter d'afficher
    // un instant l'ancien profil (vide) entre la fin de la revue et le rechargement.
    onSuccess: (profile) => {
      queryClient.setQueryData(["profile", "facts"], profile);
      queryClient.setQueryData(["profile", "pending-import"], null);
    },
  });
  const discard = useMutation({
    mutationFn: () => unwrap(api.DELETE("/api/profile/imports/{import_id}", path)),
    onSuccess: refresh,
  });

  const update = (ref: string, patch: Partial<DraftItem>) =>
    setItems((list) => list.map((item) => (item.ref === ref ? { ...item, ...patch } : item)));
  const byRef = new Map(items.map((item) => [item.ref, item]));
  const isKept = (item: DraftItem) =>
    item.keep !== false && (!item.parent_ref || byRef.get(item.parent_ref)?.keep !== false);
  const keptCount = items.filter(isKept).length;
  const evidenceOptions = items
    .filter((item) => EVIDENCE_KINDS.includes(item.kind) && isKept(item))
    .map((item) => ({ id: item.ref, label: summarize(item.kind, item.content) }));

  function renderItem(item: DraftItem, nested = false) {
    const parentDropped = item.parent_ref != null && byRef.get(item.parent_ref)?.keep === false;
    const isEditing = editing === item.ref;
    return (
      <div key={item.ref} className={nested ? "ml-6 border-l border-slate-200 pl-4" : ""}>
        <div
          className={`grid gap-3 rounded-md border bg-white p-3 md:grid-cols-[1fr_minmax(0,0.8fr)] ${
            isKept(item) ? "border-slate-200" : "border-dashed border-slate-300 opacity-60"
          }`}
        >
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <Checkbox
                aria-label={`Garder : ${summarize(item.kind, item.content)}`}
                checked={item.keep !== false}
                disabled={parentDropped}
                onCheckedChange={(checked) => update(item.ref, { keep: checked === true })}
              />
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium">{summarize(item.kind, item.content)}</p>
                {item.kind === "skill" && (
                  <p className="text-xs text-slate-600">
                    {item.evidence_refs?.length
                      ? `Prouvée par : ${item.evidence_refs
                          .map((ref) => byRef.get(ref))
                          .filter((e): e is DraftItem => !!e)
                          .map((e) => summarize(e.kind, e.content))
                          .join(" ; ")}`
                      : "Déclarative : aucune expérience ne la mentionne explicitement."}
                  </p>
                )}
              </div>
              {!isEditing && (
                <Button variant="ghost" size="sm" onClick={() => setEditing(item.ref)}>
                  Corriger
                </Button>
              )}
            </div>
            {isEditing && (
              <FactForm
                kind={item.kind}
                initial={{ ...item.content, evidence: item.evidence_refs }}
                evidenceOptions={item.kind === "skill" ? evidenceOptions : undefined}
                submitLabel="Appliquer"
                onCancel={() => setEditing(null)}
                onSubmit={(content: Content) => {
                  const { evidence, ...rest } = content;
                  update(item.ref, {
                    content: rest,
                    evidence_refs: item.kind === "skill" ? (evidence as string[]) : item.evidence_refs,
                  });
                  setEditing(null);
                }}
              />
            )}
          </div>
          <blockquote className="rounded bg-slate-50 p-2 text-xs whitespace-pre-wrap text-slate-600">
            <span className="mb-1 block font-medium text-slate-500">Passage du CV</span>
            {item.source_excerpt}
          </blockquote>
        </div>
        {items.filter((child) => child.parent_ref === item.ref).map((child) => renderItem(child, true))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Revue de l'import</h1>
        <Badge variant="secondary">{cvImport.filename}</Badge>
      </div>
      <Alert>
        <AlertTitle>Rien n'est ajouté à ton profil avant ta validation.</AlertTitle>
        <AlertDescription>
          Vérifie chaque élément à côté du passage de ton CV dont il provient. Décoche ce qui est
          faux ou inutile, corrige ce qui est mal extrait.
        </AlertDescription>
      </Alert>

      {warnings.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      {KIND_ORDER.map((kind) => {
        const roots = items.filter((item) => item.kind === kind);
        if (roots.length === 0) return null;
        return (
          <section key={kind} className="space-y-2">
            <h2 className="text-lg font-semibold">{KIND_LABELS[kind].many}</h2>
            {roots.map((item) => renderItem(item))}
          </section>
        );
      })}

      {rejected.length > 0 && (
        <details className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
          <summary className="cursor-pointer font-medium">
            {rejected.length} élément(s) écarté(s) automatiquement
          </summary>
          <p className="mt-2 text-slate-700">
            Leur passage source est introuvable dans ton CV : le modèle a pu les inventer ou les
            reformuler. Si l'un d'eux est vrai, ajoute-le à la main dans ton profil.
          </p>
          <ul className="mt-2 space-y-2">
            {rejected.map((item, index) => (
              <li key={index}>
                <span className="font-medium">{KIND_LABELS[item.kind].one}</span> :{" "}
                {summarize(item.kind, item.content)} — <em>{item.reason}</em>
              </li>
            ))}
          </ul>
        </details>
      )}

      {(validate.error || discard.error) && (
        <p className="text-sm text-red-700">{(validate.error ?? discard.error)?.message}</p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button disabled={validate.isPending || keptCount === 0} onClick={() => validate.mutate()}>
          Ajouter {keptCount} élément(s) à mon profil
        </Button>
        <Button variant="outline" disabled={discard.isPending} onClick={() => discard.mutate()}>
          Abandonner cet import
        </Button>
      </div>
    </div>
  );
}
