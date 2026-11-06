import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { components } from "@/api/schema";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  STATUS_LABELS,
  TASK_LABELS,
  formatDateTime,
  formatDay,
  formatInt,
  formatUsd,
} from "@/lib/format";

type ProviderStatus = components["schemas"]["ProviderStatus"];

async function unwrap<T>(call: Promise<{ data?: T; response: Response }>): Promise<T> {
  const { data, response } = await call;
  if (data === undefined) throw new Error(`HTTP ${response.status}`);
  return data;
}

export function Usage() {
  const status = useQuery({
    queryKey: ["llm", "status"],
    queryFn: () => unwrap(api.GET("/api/llm/status")),
  });
  const usage = useQuery({
    queryKey: ["llm", "usage"],
    queryFn: () => unwrap(api.GET("/api/llm/usage", { params: { query: { days: 30 } } })),
  });

  if (status.isError || usage.isError) {
    return <p className="text-red-700">Impossible de charger la consommation.</p>;
  }
  if (!status.data || !usage.data) return <p>Chargement…</p>;

  const { mode, monthly_budget_usd: budget, routes, providers } = status.data;
  const spent = usage.data.month_spend_usd;
  const cloudProviders = providers.filter((p) => p.is_cloud);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Consommation des modèles</h1>
        {mode === "local_strict" && <Badge variant="secondary">Mode local strict</Badge>}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ce mois-ci</CardTitle>
          <CardDescription>Coût estimé des appels aux fournisseurs cloud.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-3xl font-semibold">{formatUsd(spent)}</p>
          {budget != null ? (
            <>
              <Progress value={Math.min(100, (spent / budget) * 100)} aria-label="Budget consommé" />
              <p className="text-sm text-slate-600">Plafond mensuel : {formatUsd(budget)}</p>
            </>
          ) : (
            <p className="text-sm text-slate-600">
              Aucun plafond configuré (<code>monthly_budget_usd</code> dans tailor.toml).
            </p>
          )}
        </CardContent>
      </Card>

      {cloudProviders.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Envoi de données aux fournisseurs cloud</CardTitle>
            <CardDescription>
              Les tâches routées vers un fournisseur cloud lui envoient des extraits de ton profil
              et des offres. Rien ne part sans ton autorisation explicite, fournisseur par
              fournisseur.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {cloudProviders.map((provider) => (
              <ConsentRow key={provider.name} provider={provider} />
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Routage par tâche</CardTitle>
          <CardDescription>Modifiable dans la section [llm.routes] de tailor.toml.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tâche</TableHead>
                <TableHead>Fournisseur</TableHead>
                <TableHead>Modèle</TableHead>
                <TableHead>Effort</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {routes.map((route) => (
                <TableRow key={route.task}>
                  <TableCell>{TASK_LABELS[route.task] ?? route.task}</TableCell>
                  <TableCell>{route.provider}</TableCell>
                  <TableCell className="font-mono text-xs">{route.model}</TableCell>
                  <TableCell>{route.effort ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Coût par jour et par tâche</CardTitle>
          <CardDescription>30 derniers jours.</CardDescription>
        </CardHeader>
        <CardContent>
          {usage.data.daily.length === 0 ? (
            <p className="text-sm text-slate-600">Aucun appel sur la période.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Jour</TableHead>
                  <TableHead>Tâche</TableHead>
                  <TableHead className="text-right">Appels</TableHead>
                  <TableHead className="text-right">Jetons (entrée / sortie)</TableHead>
                  <TableHead className="text-right">Coût</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {usage.data.daily.map((d) => (
                  <TableRow key={`${d.day}-${d.task}`}>
                    <TableCell>{formatDay(d.day)}</TableCell>
                    <TableCell>{TASK_LABELS[d.task] ?? d.task}</TableCell>
                    <TableCell className="text-right">{formatInt(d.calls)}</TableCell>
                    <TableCell className="text-right">
                      {formatInt(d.input_tokens)} / {formatInt(d.output_tokens)}
                    </TableCell>
                    <TableCell className="text-right">{formatUsd(d.cost_usd)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appels récents</CardTitle>
        </CardHeader>
        <CardContent>
          {usage.data.recent.length === 0 ? (
            <p className="text-sm text-slate-600">Aucun appel pour l'instant.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Tâche</TableHead>
                  <TableHead>Modèle</TableHead>
                  <TableHead>Prompt</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Durée</TableHead>
                  <TableHead className="text-right">Coût</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {usage.data.recent.map((call) => (
                  <TableRow key={call.id}>
                    <TableCell>{formatDateTime(call.created_at)}</TableCell>
                    <TableCell>{TASK_LABELS[call.task] ?? call.task}</TableCell>
                    <TableCell className="font-mono text-xs">{call.model}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {call.prompt_id}@{call.prompt_version}
                    </TableCell>
                    <TableCell title={call.error ?? undefined}>
                      <Badge variant={call.status === "ok" || call.status === "cached" ? "secondary" : "destructive"}>
                        {STATUS_LABELS[call.status] ?? call.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">{formatInt(call.duration_ms)} ms</TableCell>
                    <TableCell className="text-right">{formatUsd(call.cost_usd)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ConsentRow({ provider }: { provider: ProviderStatus }) {
  const queryClient = useQueryClient();
  const params = { params: { path: { provider: provider.name } } };
  const mutation = useMutation({
    mutationFn: async (grant: boolean) => {
      const { response } = grant
        ? await api.POST("/api/llm/consents/{provider}", params)
        : await api.DELETE("/api/llm/consents/{provider}", params);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["llm", "status"] }),
  });
  const granted = provider.consent_granted_at != null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3">
      <div className="space-y-1">
        <p className="font-medium">{provider.name}</p>
        <p className="text-sm text-slate-600">
          {granted
            ? `Autorisé le ${formatDateTime(provider.consent_granted_at!)}.`
            : "Non autorisé : les tâches routées ici échoueront."}
          {!provider.api_key_configured && " Aucune clé détectée (variable d'environnement ou trousseau)."}
        </p>
      </div>
      <Button
        variant={granted ? "outline" : "default"}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate(!granted)}
      >
        {granted ? "Retirer l'autorisation" : `Autoriser l'envoi à ${provider.name}`}
      </Button>
    </div>
  );
}
