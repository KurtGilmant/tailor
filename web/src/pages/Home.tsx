import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

export function Home() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, response } = await api.GET("/api/health");
      if (!data) throw new Error(String(response.status));
      return data;
    },
    retry: false,
  });

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Bienvenue dans Tailor</h1>
      <p className="text-slate-600">
        Préparation de candidatures en un clic, à partir d'un profil où chaque ligne est vraie.
      </p>
      <div role="status" className="rounded-md border border-slate-200 bg-white p-4 text-sm">
        {health.isPending && "Connexion au backend…"}
        {health.isSuccess && (
          <span className="text-emerald-700">
            Backend connecté — version {health.data.version}, base {health.data.database}.
          </span>
        )}
        {health.isError &&
          (health.error.message === "401" ? (
            <span className="text-amber-700">
              Jeton absent ou expiré : ouvre l'application avec l'URL affichée par la commande{" "}
              <code>tailor</code>.
            </span>
          ) : (
            <span className="text-red-700">Backend injoignable ({health.error.message}).</span>
          ))}
      </div>
    </section>
  );
}
