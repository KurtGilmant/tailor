import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { Link } from "react-router";

import { api } from "@/api/client";
import { ApiError, postFile, unwrap } from "@/api/helpers";
import type { components } from "@/api/schema";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ImportReview } from "@/profile/ImportReview";
import { ProfileEditor } from "@/profile/ProfileEditor";

type ImportOut = components["schemas"]["ImportOut"];

export function Profile() {
  const profile = useQuery({
    queryKey: ["profile", "facts"],
    queryFn: () => unwrap(api.GET("/api/profile")),
  });
  const pending = useQuery({
    queryKey: ["profile", "pending-import"],
    queryFn: () => unwrap(api.GET("/api/profile/imports/pending")),
  });

  if (profile.isError || pending.isError) {
    return <p className="text-red-700">Impossible de charger le profil.</p>;
  }
  if (!profile.data || pending.data === undefined) return <p>Chargement…</p>;
  if (pending.data) return <ImportReview key={pending.data.id} cvImport={pending.data} />;

  const empty = profile.data.facts.length === 0;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Mon profil</h1>
        {!empty && <ImportButton label="Importer un autre CV" variant="outline" />}
      </div>
      {empty && (
        <Card>
          <CardHeader>
            <CardTitle>Commence par importer ton CV</CardTitle>
            <CardDescription>
              PDF (avec du texte sélectionnable) ou DOCX. Chaque élément extrait te sera présenté à
              côté du passage de ton CV dont il vient, et rien n'est enregistré avant ta validation.
              Tu peux aussi tout saisir à la main ci-dessous.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ImportButton label="Importer mon CV" />
          </CardContent>
        </Card>
      )}
      <ProfileEditor facts={profile.data.facts} version={profile.data.version} />
    </div>
  );
}

function ImportButton({ label, variant }: { label: string; variant?: "outline" }) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const upload = useMutation({
    mutationFn: (file: File) => postFile<ImportOut>("/api/profile/imports", file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });
  const blocked = upload.error instanceof ApiError && upload.error.code === "llm_blocked";

  return (
    <div className="space-y-3">
      <input
        ref={input}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        aria-label="Fichier du CV"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) upload.mutate(file);
          event.target.value = "";
        }}
      />
      <Button variant={variant} disabled={upload.isPending} onClick={() => input.current?.click()}>
        {upload.isPending ? "Analyse du CV en cours…" : label}
      </Button>
      {upload.error && (
        <Alert variant="destructive">
          <AlertTitle>Import impossible</AlertTitle>
          <AlertDescription>
            {upload.error.message}
            {blocked && (
              <>
                {" "}
                <Link to="/consommation" className="underline">
                  Ouvrir la page Consommation
                </Link>
              </>
            )}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
