import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/helpers";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";

import { FactForm } from "./FactForm";
import {
  EVIDENCE_KINDS,
  KIND_LABELS,
  KIND_ORDER,
  summarize,
  type Content,
  type FactKind,
  type FactOut,
} from "./facts";

type Editing = { mode: "edit"; id: string } | { mode: "add"; kind: FactKind; parentId?: string };

export function ProfileEditor({ facts, version }: { facts: FactOut[]; version: number }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Editing | null>(null);
  const [historyOf, setHistoryOf] = useState<string | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["profile"] });

  const create = (kind: FactKind, content: Content, parentId?: string) =>
    unwrap(
      api.POST("/api/profile/facts", { body: { kind, content, parent_id: parentId ?? null } }),
    ).then(() => (setEditing(null), refresh()));
  const save = (id: string, content: Content) =>
    unwrap(
      api.PUT("/api/profile/facts/{fact_id}", { params: { path: { fact_id: id } }, body: { content } }),
    ).then(() => (setEditing(null), refresh()));
  const retire = useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE("/api/profile/facts/{fact_id}", { params: { path: { fact_id: id } } })),
    onSuccess: refresh,
  });

  const byId = new Map(facts.map((fact) => [fact.id, fact]));
  const evidenceOptions = facts
    .filter((fact) => EVIDENCE_KINDS.includes(fact.kind))
    .map((fact) => ({ id: fact.id, label: summarize(fact.kind, fact.content) }));
  const hasIdentity = facts.some((fact) => fact.kind === "identity");

  function renderFact(fact: FactOut, nested = false) {
    const isEditing = editing?.mode === "edit" && editing.id === fact.id;
    const children = facts.filter((child) => child.parent_id === fact.id);
    const canHaveAchievements = fact.kind === "experience" || fact.kind === "project";
    const addingChild =
      editing?.mode === "add" && editing.kind === "achievement" && editing.parentId === fact.id;
    return (
      <div key={fact.id} className={nested ? "ml-6 border-l border-slate-200 pl-4" : ""}>
        <div className="rounded-md border border-slate-200 bg-white p-3">
          {isEditing ? (
            <FactForm
              kind={fact.kind}
              initial={fact.content}
              evidenceOptions={fact.kind === "skill" ? evidenceOptions : undefined}
              onCancel={() => setEditing(null)}
              onSubmit={(content) => save(fact.id, content)}
            />
          ) : (
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="space-y-1">
                <p className="text-sm font-medium">{summarize(fact.kind, fact.content)}</p>
                {fact.kind === "skill" && (
                  <p className="text-xs text-slate-600">
                    {fact.skill_status === "supported" ? (
                      <Badge variant="secondary">Étayée</Badge>
                    ) : (
                      <Badge variant="outline">Déclarative</Badge>
                    )}{" "}
                    {((fact.content.evidence as string[]) ?? [])
                      .map((id) => byId.get(id))
                      .filter((e): e is FactOut => !!e)
                      .map((e) => summarize(e.kind, e.content))
                      .join(" ; ")}
                  </p>
                )}
                {fact.source_excerpt && (
                  <p className="text-xs text-slate-500" title={fact.source_excerpt}>
                    Extrait du CV · révision {fact.rev}
                  </p>
                )}
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => setEditing({ mode: "edit", id: fact.id })}>
                  Modifier
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setHistoryOf(historyOf === fact.id ? null : fact.id)}
                >
                  Historique
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const message = canHaveAchievements
                      ? "Retirer cet élément et ses réalisations du profil ?"
                      : "Retirer cet élément du profil ?";
                    if (window.confirm(message)) retire.mutate(fact.id);
                  }}
                >
                  Retirer
                </Button>
              </div>
            </div>
          )}
          {historyOf === fact.id && <History factId={fact.id} kind={fact.kind} />}
        </div>
        {children.map((child) => renderFact(child, true))}
        {canHaveAchievements && (
          <div className="ml-6 mt-1 pl-4">
            {addingChild ? (
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <FactForm
                  kind="achievement"
                  submitLabel="Ajouter"
                  onCancel={() => setEditing(null)}
                  onSubmit={(content) => create("achievement", content, fact.id)}
                />
              </div>
            ) : (
              <Button
                variant="link"
                size="sm"
                onClick={() => setEditing({ mode: "add", kind: "achievement", parentId: fact.id })}
              >
                + Ajouter une réalisation
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-600">
        Version {version} du profil · {facts.length} faits. Le profil peut contenir bien plus que
        ton CV : c'est le réservoir dans lequel les CV adaptés puisent.
      </p>
      {retire.error && <p className="text-sm text-red-700">{retire.error.message}</p>}
      {KIND_ORDER.map((kind) => {
        const roots = facts.filter((fact) => fact.kind === kind);
        const adding = editing?.mode === "add" && editing.kind === kind;
        const canAdd = kind !== "identity" || !hasIdentity;
        return (
          <section key={kind} className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">{KIND_LABELS[kind].many}</h2>
              {canAdd && !adding && (
                <Button variant="outline" size="sm" onClick={() => setEditing({ mode: "add", kind })}>
                  Ajouter
                </Button>
              )}
            </div>
            {adding && (
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <FactForm
                  kind={kind}
                  submitLabel="Ajouter"
                  evidenceOptions={kind === "skill" ? evidenceOptions : undefined}
                  onCancel={() => setEditing(null)}
                  onSubmit={(content) => create(kind, content)}
                />
              </div>
            )}
            {roots.length === 0 && !adding && <p className="text-sm text-slate-500">Rien pour l'instant.</p>}
            {roots.map((fact) => renderFact(fact))}
          </section>
        );
      })}
    </div>
  );
}

function changedFields(previous: Content | undefined, current: Content): string[] {
  if (!previous) return [];
  const keys = new Set([...Object.keys(previous), ...Object.keys(current)]);
  return [...keys].filter((key) => JSON.stringify(previous[key]) !== JSON.stringify(current[key]));
}

function History({ factId, kind }: { factId: string; kind: FactKind }) {
  const revisions = useQuery({
    queryKey: ["profile", "revisions", factId],
    queryFn: () =>
      unwrap(api.GET("/api/profile/facts/{fact_id}/revisions", { params: { path: { fact_id: factId } } })),
  });
  if (!revisions.data) return <p className="mt-2 text-xs text-slate-500">Chargement…</p>;
  return (
    <ol className="mt-3 space-y-1 border-t border-slate-100 pt-2 text-xs text-slate-600">
      {revisions.data.map((revision, index) => {
        const changed = changedFields(revisions.data[index - 1]?.content, revision.content);
        return (
          <li key={revision.rev}>
            <span className="font-medium">Révision {revision.rev}</span> ·{" "}
            {formatDateTime(revision.created_at)} · version {revision.profile_version} —{" "}
            {summarize(kind, revision.content)}
            {index === 0
              ? revision.source_excerpt
                ? " (extrait du CV)"
                : " (saisie manuelle)"
              : ` (modifié : ${changed.join(", ") || "rien"})`}
          </li>
        );
      })}
    </ol>
  );
}
