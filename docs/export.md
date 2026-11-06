# Format d'export de Tailor

L'export contient **toutes** tes données dans un seul fichier JSON. On le télécharge depuis
**Réglages → Données → Exporter**, ou par l'API (`GET /api/data/export`, avec le jeton de
lancement). La configuration `tailor.toml` et les clés d'API n'y figurent jamais.

## Enveloppe

| Champ | Type | Description |
|---|---|---|
| `format` | `"tailor-export"` | identifiant du format |
| `format_version` | entier | `1` ; incrémenté à chaque changement incompatible |
| `app_version` | texte | version de Tailor qui a produit l'export |
| `exported_at` | date ISO 8601 (UTC) | date de l'export |
| `profile` | objet | profil maître (voir ci-dessous) |
| `preferences` | objet | préférences de recherche |
| `answers` | liste | banque de réponses |
| `cv_imports` | liste | imports de CV, avec le texte extrait et le brouillon proposé |
| `llm` | objet | `consents` (consentements par fournisseur) et `calls` (journal des appels) |

Les jalons suivants ajouteront `offers`, `kits` et `applications` (sans changer
`format_version`, puisque ces ajouts sont compatibles).

## `profile`

```json
{
  "versions": [{ "id": 1, "created_at": "…", "reason": "Import du CV « cv.pdf »" }],
  "facts": [
    {
      "id": "01JC…",
      "kind": "achievement",
      "parent_id": "01JB…",
      "position": 0,
      "current_rev": 2,
      "created_at": "…",
      "retired_at": null,
      "revisions": [
        {
          "rev": 1,
          "content": { "text": "Réduction de 20 % du temps de traitement" },
          "source_excerpt": "• Réduction de 20 % du temps de traitement",
          "profile_version": 1,
          "created_at": "…"
        }
      ]
    }
  ]
}
```

- **Tous** les faits y figurent, y compris ceux retirés (`retired_at` renseigné), avec
  **toutes** leurs révisions : c'est l'historique complet, pas seulement l'état courant.
- `kind` vaut `identity`, `experience`, `achievement`, `project`, `education`, `skill`,
  `language` ou `certification`. La forme de `content` dépend du type : voir
  `backend/src/tailor/profile/schemas.py`.
- `source_excerpt` est le passage du CV dont le fait a été extrait (`null` pour un fait
  saisi à la main).
- Une compétence (`skill`) liste dans `content.evidence` les identifiants des faits qui la
  démontrent.

## `preferences`

```json
{
  "contract_types": ["alternance"],
  "locations": ["Bordeaux"],
  "work_modes": ["sur_site", "teletravail_complet"],
  "salary": { "min": 20000, "max": 24000, "currency": "EUR", "period": "annuel" },
  "available_from": "2027-09-01",
  "work_languages": ["français", "anglais"],
  "work_authorization": null,
  "notice_period": null,
  "excluded_companies": []
}
```

## `answers`

Chaque entrée : `id`, `question`, `question_key` (question normalisée, utilisée pour la
réutilisation à l'identique), `answer`, `created_at`, `updated_at`.

## Suppression totale

**Réglages → Données → Tout supprimer** (ou `POST /api/data/delete` avec
`{"confirmation": "SUPPRIMER"}`) vide toutes les tables, compacte la base (`VACUUM`) pour
qu'aucune ancienne donnée ne reste dans le fichier, vide le journal SQLite et efface les
fichiers générés. La configuration `tailor.toml` est conservée. Exporte d'abord si tu veux
garder une copie.
