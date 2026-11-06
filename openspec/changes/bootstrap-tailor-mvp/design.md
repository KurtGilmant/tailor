# Design

## Context

Projet neuf, sans code existant. Motivation et périmètre : voir `proposal.md`. Exigences : voir `specs/`.

Contraintes qui façonnent l'architecture :
- **Une seule personne, une seule machine** (macOS Apple Silicon). Pas de comptes ni de serveur distant, mais une extension navigateur doit pouvoir parler à l'application.
- **La véracité est l'exigence n°1.** La garantie ne peut pas reposer uniquement sur un prompt (« n'invente rien ») : il faut des garanties structurelles et des contrôles indépendants du modèle.
- **Les fournisseurs LLM sont interchangeables** (cloud et local), et la qualité doit être mesurée plutôt que supposée.
- **Le texte des offres est hostile par défaut**, puisqu'il est écrit par des tiers.

## Goals / Non-Goals

**Goals :**
- Garantir la véracité par construction : ce que le LLM ne produit pas, il ne peut pas le falsifier.
- Rendre chaque étape IA observable (journal, versions de prompts, rapports de vérification) et mesurable (évaluation).
- Avoir une architecture simple à lancer : une commande, un processus, une base SQLite.
- Pouvoir tester l'extension de bout en bout sur des formulaires de démonstration, sans postuler pour de vrai.

**Non-Goals :**
- Pas de file de messages, pas de base distribuée, pas de conteneurs : c'est inutile en mono-utilisateur.
- Pas d'application de bureau empaquetée (Tauri, Electron) pour le MVP : l'application tourne en local et s'ouvre dans le navigateur.
- Pas de publication de l'extension sur le Chrome Web Store : elle est chargée « non empaquetée ».
- Pas d'OCR des CV scannés.

## Decisions

### D1. Monorepo et processus unique

```
tailor/
├── backend/        FastAPI + logique métier (paquet `tailor`)
├── web/            React + Vite + TS (servi en statique par le backend une fois buildé)
├── extension/      Chrome MV3 (WXT + TS)
├── prompts/        prompts versionnés (fichiers texte + front-matter version)
├── templates/      gabarits Typst du CV et de la lettre
├── evals/          jeu d'évaluation synthétique + runner
└── openspec/
```

Un seul processus Python sert l'API et l'interface web buildée sur `127.0.0.1:8765`. En développement, Vite tourne à part avec un proxy vers l'API.

*Alternatives :* Next.js full-stack (écarté : l'écosystème IA et l'évaluation sont en Python) ; application de bureau Tauri (reportée, rien ne l'impose pour le MVP).

### D2. Persistance : SQLite et faits révisionnés

- SQLite via SQLModel, migrations Alembic. Les données vont dans le dossier applicatif de l'OS (`platformdirs` : `~/Library/Application Support/Tailor/`), **hors du dépôt**, avec des permissions `700`.
- **Faits append-only** : une table `fact` (id ULID stable, type, révision courante, retiré oui/non) et une table `fact_revision` (fact_id, rev, contenu JSON, date). Tout contenu généré cite des couples `(fact_id, rev)`, ce qui fige le texte exact qui a servi de preuve. C'est ce qui rend possibles l'instantané immuable et l'affichage d'un fait retiré (spec `candidate-profile`).
- `profile_version` est un compteur incrémenté à chaque validation de modification.
- Autres tables : `preference`, `answer_bank`, `offer`, `offer_source`, `offer_analysis`, `match_score`, `kit`, `kit_document`, `verification_report`, `application`, `application_event`, `snapshot`, `llm_call`, `llm_cache`, `background_job`.
- Les fichiers PDF générés sont stockés sur disque dans le dossier applicatif, référencés par leur hash SHA-256. Les instantanés pointent vers ces hash et ne les modifient jamais.

*Alternatives :* PostgreSQL (surdimensionné en local) ; fichiers JSON (pas de requêtes, pas de transactions).

### D3. Schéma du profil

Le schéma s'inspire de JSON Resume (standard connu, mappable vers les ATS), étendu avec :
- un identifiant et une révision par fait ;
- des **réalisations atomiques** sous chaque expérience (une puce = un fait) plutôt qu'un bloc de texte ;
- des compétences reliées par `evidence: [fact_id]` ;
- pour les champs protégés, `translations: {en: "...", fr: "..."}` saisies par l'utilisateur.

Import : extraction texte (pdfplumber pour le PDF, python-docx pour le DOCX), puis un appel LLM d'extraction structurée qui renvoie, pour chaque fait, le passage source. Un passage source introuvable textuellement dans le CV fait rejeter le fait.

### D4. Passerelle LLM maison et légère

Interface interne unique `complete(task, prompt_id, inputs, schema) -> validated_model`, avec deux adaptateurs :
- **Anthropic** (SDK officiel) ;
- **compatible OpenAI** (SDK `openai` pointé vers une `base_url`), qui couvre Ollama, LM Studio, vLLM et OpenAI.

Sorties structurées : schéma JSON strict dérivé du modèle Pydantic (objets fermés, toutes propriétés requises), passé via `output_config.format` côté Anthropic et `response_format: json_schema` côté compatible OpenAI, puis revalidé par Pydantic. En cas d'échec, la réponse fautive et l'erreur sont renvoyées dans un **nouveau** message utilisateur (2 tentatives au total par défaut) : on ne rejoue pas l'historique, ce qui évite toute réécriture de blocs de réflexion.

Spécificités Anthropic (API actuelle, vérifiée à l'implémentation) : pas de `temperature` (rejetée par les modèles récents), la profondeur se règle par `output_config.effort` ; le `stop_reason` « refusal » est traité explicitement, et `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) rejoue côté serveur une demande refusée sur les modèles qui le supportent. Le coût est calculé au tarif du modèle effectivement servi.

Routage par défaut (modifiable dans `tailor.toml`) : **`claude-opus-5-5` pour toutes les tâches**, avec un effort adapté. Basculer l'extraction ou la notation vers `claude-haiku-5-5` (40 fois moins cher) est une décision de coût laissée à l'utilisateur, à éclairer par les évaluations (groupe 8).

| Tâche | Défaut | Effort | Rôle |
|---|---|---|---|
| `extract` | `claude-opus-5-5` | `low` | CV vers faits, offre vers exigences |
| `score` | `claude-opus-5-5` | `medium` | couverture des exigences |
| `write` | `claude-opus-5-5` | `high` | puces, accroche, lettre, réponses |
| `verify` | `claude-opus-5-5` | `high` | juge d'ancrage (prompt et contexte indépendants du rédacteur) |

Les **embeddings** sont toujours locaux (`sentence-transformers`, modèle multilingue FR/EN, `intfloat/multilingual-e5-base` en premier candidat) : c'est gratuit, privé, et Anthropic ne propose pas d'API d'embeddings. Les vecteurs sont stockés dans SQLite et la recherche se fait par force brute avec numpy, ce qui suffit pour quelques milliers d'offres.

Cache : clé = hash(fournisseur, modèle, version du prompt, entrées sérialisées). Journal : une ligne `llm_call` par appel. Coûts : barème par modèle dans la configuration.

Garde-fous de sortie (spec `llm-gateway`) : consentement par fournisseur stocké en base, mode local strict vérifié **dans l'adaptateur** (l'adaptateur cloud refuse de s'exécuter), plafond mensuel vérifié avant chaque appel cloud.

*Alternatives :* LiteLLM (dépendance lourde, qui masque justement ce qu'on veut apprendre) ; `instructor` (bonne bibliothèque, mais la boucle de validation tient en une centaine de lignes et reste sous contrôle). On pourra y revenir si la maintenance des adaptateurs devient pénible.

### D5. Pipeline d'adaptation du CV (le cœur)

```
offre ──► [1] analyse de l'offre (extract, cache) ──► exigences + passages
                                        │
profil ─► [2] classement des faits ◄────┘   embeddings fait↔exigence + rerank LLM (score)
                 │
                 ▼
          [3] sélection sous budget (une page) : glouton pertinence/longueur
                 │
                 ▼
          [4] réécriture contrainte (write) : reçoit UNIQUEMENT les faits retenus (id + texte)
              + les exigences extraites (jamais l'offre brute) ; sortie = éléments {texte, source_fact_ids}
                 │
                 ▼
          [5] vérification (D6) ──échec──► [5b] réparation avec raison (×2) ──► repli texte original
                 │ ok
                 ▼
          [6] assemblage : champs protégés injectés depuis le profil, PAS depuis le LLM
                 │
                 ▼
          [7] rendu Typst → PDF → contrôle pages + lisibilité ATS ──trop long──► retour en [3]
```

Décisions clés :
- **Garantie structurelle des champs protégés.** Le schéma de sortie du LLM n'a *aucun champ* pour l'employeur, l'intitulé ou les dates : le moteur de rendu les joint depuis le profil par `fact_id`. Le modèle ne peut donc pas les modifier, même s'il le voulait.
- **Le rédacteur ne voit jamais l'offre brute** pour le CV, seulement les exigences extraites (des champs courts et typés). Cela coupe le principal vecteur d'injection.
- **Ajustement à la page par réduction**, jamais par troncature : on retire le fait le moins pertinent et on refait le rendu (le rendu Typst prend quelques dizaines de millisecondes).

### D6. Vérification d'ancrage à deux couches

1. **Couche déterministe (veto)** :
   - nombres, pourcentages, durées et dates extraits par regex et normalisés (`20 %` = `20%` = `0,2`) ; chacun doit apparaître dans les faits cités ;
   - technologies : un lexique versionné dans le dépôt, complété par les compétences du profil ; tout terme du lexique présent dans la sortie doit figurer dans les faits cités ou dans les compétences du profil ;
   - organisations : détection par la reconnaissance d'entités nommées de spaCy (`fr_core_news_md` / `en_core_web_md`) ; toute organisation doit figurer dans les faits cités (ou, dans la lettre, correspondre au nom de l'entreprise de l'offre) ;
   - citations : chaque `fact_id` doit exister et être actif.
2. **Juge LLM** : décomposition en affirmations atomiques, puis jugement de type inférence (*NLI*) avec pour seules prémisses le texte des faits cités. **Le juge ne voit jamais l'offre**, il ne peut donc pas être contaminé par une injection. Pour la lettre, les affirmations sur l'entreprise sont contrôlées par une recherche textuelle du passage cité dans l'offre enregistrée, sans LLM.

Le verdict final est `contredit` > `non étayé` > `étayé`, et la couche déterministe l'emporte toujours. Les faux positifs déterministes (une entité mal reconnue, par exemple) sont acceptés : l'utilisateur peut les assumer explicitement. Mieux vaut une alerte de trop qu'une invention envoyée.

*Alternatives :* juge LLM seul (corrélé aux erreurs du rédacteur, non déterministe) ; cross-encoder NLI local de type mDeBERTa-XNLI (piste intéressante comme pré-filtre gratuit, à comparer dans `evals/` ; voir les questions ouvertes).

### D7. Défense contre l'injection de prompt

Il y a trois points d'entrée de texte non fiable : les offres, les pages capturées et les CV importés (moins critique). Mesures :
- l'offre est placée dans un bloc de données délimité, avec une consigne système explicite, uniquement dans l'étape d'extraction, dont la sortie est un schéma de champs courts ;
- les étapes suivantes consomment ces champs, pas le texte brut (sauf la lettre, qui le reçoit pour citer des passages, avec citations vérifiées textuellement) ;
- le vérificateur ne voit jamais l'offre (D6) ;
- une heuristique signale les offres contenant des motifs d'injection (« ignore », « previous instructions », texte caché en CSS lors d'une capture) : signalement informatif dans l'interface, sans blocage ;
- la mesure est faite par les cas adversariaux de `evals/`.

### D8. Matching en deux étages

1. Filtres déterministes sur les préférences (contrat, lieu, télétravail, exclusions, langue). Un champ « inconnu » ne filtre pas.
2. **Score préliminaire** : similarité cosinus entre l'embedding du profil (accroche et compétences) et celui de l'offre. C'est gratuit et immédiat.
3. **Score détaillé** pour le top N (20 par défaut) : couverture de chaque exigence par le LLM (`score`), avec les `fact_id` couvrants. Score = 60 % couverture des indispensables + 20 % des appréciées + 10 % adéquation séniorité/années + 10 % similarité. La formule est versionnée et ajustable.

*Alternatives :* score LLM global (opaque et instable d'un appel à l'autre) ; embeddings seuls (aucune explication possible, ce que la spec interdit).

### D9. Connecteurs de sourcing

Interface `SourceConnector.fetch(query) -> list[RawOffer]`, avec un connecteur par source et une normalisation commune.

| Source | Accès | Particularité |
|---|---|---|
| France Travail – Offres d'emploi v2 | OAuth2 *client credentials*, inscription gratuite | inclut l'alternance ; pagination par plages |
| Adzuna | `app_id` + `app_key` gratuits | descriptions **tronquées**, d'où le marquage « description partielle » |
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | public |
| Lever | `api.lever.co/v0/postings/{company}?mode=json` | public |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{org}` | public |
| Workable, Recruitee, SmartRecruiters | endpoints publics de *job board* | public |
| Welcome to the Jungle, LinkedIn, Indeed | aucun accès automatique | capture via l'extension uniquement |

- Détection de l'ATS depuis l'URL de la page carrière par motifs d'URL (`jobs.lever.co/{x}`, `boards.greenhouse.io/{x}`, `jobs.ashbyhq.com/{x}`…).
- Client HTTP `httpx` avec un limiteur par source et un backoff exponentiel sur 429/5xx. Chaque connecteur est isolé (try/except par source, statut stocké).
- Planification par APScheduler dans le processus, toutes les 6 h par défaut, seulement pendant que l'application tourne.
- Déduplication : clé normalisée (entreprise + intitulé + ville, sans accents ni casse), confirmée par une similarité cosine des descriptions au-dessus de 0,92.
- Assainissement du HTML avec `nh3` à l'ingestion ; l'offre brute est conservée à part pour l'audit.

### D10. Documents : Typst

Rendu par le paquet Python `typst`, qui embarque le compilateur (aucune installation système, contrairement à LaTeX ou WeasyPrint, qui dépend de pango). Les gabarits `.typ` reçoivent les données en JSON. L'ensemble est sobre, sur une colonne, avec des polices embarquées et un contenu sémantique (aucun texte en image).

Contrôle de lisibilité ATS : `pypdf` compte les pages, `pdfplumber` réextrait le texte, puis on vérifie la présence et l'ordre du nom, de l'e-mail, des titres de section et de chaque intitulé d'expérience.

*Alternatives :* WeasyPrint (HTML/CSS familier, mais dépendances système et rendu plus lent) ; export DOCX (certains ATS le préfèrent ; voir les questions ouvertes).

### D11. Extension Chrome MV3

- Framework **WXT** (Vite, TypeScript, rechargement à chaud, Firefox possible plus tard).
- **Permissions minimales** : `activeTab`, `scripting`, `storage`, plus des *permissions d'hôte optionnelles* pour les domaines d'ATS connus, demandées à l'exécution. C'est nécessaire parce que Greenhouse et Ashby sont souvent intégrés **en iframe** sur le site de l'entreprise, et `activeTab` ne couvre pas les iframes d'autres origines.
- **Tout le réseau passe par le service worker** (jamais par le content script), vers `http://127.0.0.1:8765` avec le jeton d'appairage. Cela évite les restrictions CORS et *Private Network Access* qui s'appliquent à l'origine de la page.
- Remplissage :
  - **adaptateurs dédiés** par ATS (sélecteurs et sémantique des champs connus, y compris les listes déroulantes personnalisées) ;
  - **adaptateur générique** : collecte des champs (libellé, `name`, placeholder, type, options), association déterministe par dictionnaire de synonymes FR/EN, puis association par LLM sur les **libellés seuls** avec un score de confiance ; sous le seuil, le champ reste vide.
- Champs React contrôlés : on affecte la valeur via le *setter* natif de `HTMLInputElement.prototype`, puis on émet `input` et `change` avec propagation. Fichiers : le PDF est récupéré par le service worker, transmis au content script, transformé en `File`, puis injecté via `DataTransfer` dans `input[type=file]`, avec l'événement `change`.
- **Interdiction de soumettre, garantie par l'outillage** : une règle eslint (`no-restricted-syntax`) interdit `.submit(`, `.requestSubmit(` et les clics programmatiques sur `[type=submit]` dans le code de l'extension. Un test Playwright vérifie qu'aucune soumission ni navigation n'a lieu après le pré-remplissage.
- Détection de l'envoi : écoute de l'événement `submit` (phase de capture) sur les formulaires pré-remplis, puis une notification dans la popup demande confirmation.
- Formulaires de démonstration (des copies statiques simplifiées de formulaires Greenhouse, Lever et génériques) dans `extension/e2e/fixtures/` pour les tests.

### D12. Sécurité locale

- Écoute **uniquement sur `127.0.0.1`**.
- **Jeton façon Jupyter** : au lancement, l'application génère un jeton aléatoire et ouvre `http://127.0.0.1:8765/?token=…`. L'interface web le conserve en `sessionStorage` et toutes les routes `/api` exigent `Authorization: Bearer`. L'extension reçoit son propre jeton à l'appairage (code à 6 chiffres, valable 5 minutes, à usage unique).
- **Contrôle de l'en-tête `Host`** (seulement `127.0.0.1:8765` ou `localhost:8765`) contre le *DNS rebinding*, et CORS limité à l'origin `chrome-extension://<id>` appairé.
- Clés d'API stockées dans le trousseau macOS via `keyring` (repli sur des variables d'environnement), jamais envoyées au front ni journalisées.

### D13. Tâches longues

La préparation d'un dossier prend de 30 à 90 secondes. Elle s'exécute en tâche asyncio dans le processus, avec son état persisté dans `background_job` (étape courante, erreur) et une progression poussée au front par SSE. Au redémarrage, une tâche « en cours » orpheline passe « en échec, relançable ». Aucune file externe (Celery, Redis) n'est nécessaire en mono-utilisateur.

### D14. Front et contrat d'API

React, Vite, TypeScript, React Router, TanStack Query, Tailwind et shadcn/ui. Le client typé est **généré depuis l'OpenAPI** de FastAPI (`openapi-typescript` + `openapi-fetch`) : le front casse à la compilation si le contrat change.

Écrans : Profil, Offres (flux), Détail d'offre (score, exigences, lacunes), Dossier (revue côte à côte, rapport de vérification), Candidatures (tableau), Sources, Réglages (préférences, LLM, consommation).

### D15. Outillage

`uv` (Python 3.13 épinglé, déjà présent sur la machine), `ruff`, `pyright`, `pytest` (enregistrement des appels HTTP des connecteurs via `respx`, `httpx2.MockTransport` pour les SDK LLM, et faux fournisseur LLM déterministe) ; `npm`, `eslint`, `vitest`, `playwright`. Un `Makefile` regroupe `dev`, `test`, `lint`, `typecheck`, `eval`, `build` (`make` est toujours présent, contrairement à `just`).

## Risks / Trade-offs

- [Le juge LLM laisse passer un gonflement subtil, du type « participé » devenu « piloté »] → Le prompt du juge cible explicitement les verbes de responsabilité, le rappel du vérificateur est mesuré sur des annotations manuelles (spec `quality-evaluation`) et la revue humaine reste obligatoire avant « prêt ».
- [Des contraintes trop strictes produisent des CV fades et peu adaptés] → La couverture des exigences et la longueur sont mesurées dans les évaluations, et la seule voie pour enrichir est d'enrichir le profil (le réservoir), jamais le CV.
- [Faux positifs de la couche déterministe, NER en tête] → Possibilité d'« assumer » une alerte (horodatée), et un suivi du taux de faux positifs dans les évaluations.
- [Formulaires d'ATS qui changent, iframes, widgets maison] → Adaptateurs isolés et testés sur fixtures, repli générique qui préfère laisser vide, et récapitulatif des champs obligatoires vides.
- [Endpoints publics d'ATS modifiés ou restreints] → Connecteurs isolés, panne visible sans effet sur le reste, et import manuel ou capture toujours disponibles.
- [Modèles locaux nettement plus faibles en rédaction] → Routage par tâche (par exemple extraction en local, rédaction dans le cloud) et comparaison chiffrée dans les évaluations au lieu d'un a priori.
- [Coûts cloud qui dérivent pendant le développement] → Cache des appels, faux fournisseur dans les tests, plafond mensuel, et score détaillé limité au top N.
- [Perception recruteur et usage de masse] → Aucun envoi automatique, alerte anti-doublon, revue obligatoire : l'outil fait gagner du temps sur la qualité, pas sur le volume.
- [Exposition locale : une page web malveillante qui vise `localhost`] → Jeton obligatoire, contrôle du `Host`, CORS strict, écoute en bouclage uniquement.

## Migration Plan

Il n'y a rien à migrer. Les livraisons sont incrémentales et chaque jalon est utilisable seul :

1. **M0 Fondations** : dépôt, backend, front, sécurité locale, passerelle LLM.
2. **M1 Profil** : import, revue, faits révisionnés, préférences.
3. **M2 Offres** : connecteurs, import manuel, analyse, matching, flux.
4. **M3 Cœur IA** : vérification d'ancrage, puis CV adapté, puis évaluation (construite tout de suite pour piloter les prompts).
5. **M4 Dossier et suivi** : lettre, réponses, rendu, instantanés, candidatures.
6. **M5 Extension** : appairage, capture, pré-remplissage, détection de l'envoi.

Retour arrière : la base est migrée par Alembic (`downgrade` disponible) et l'export JSON complet sert de sauvegarde avant chaque migration.

## Open Questions

- Conditions d'utilisation et quotas exacts de chaque endpoint public d'ATS et de France Travail : à relire au moment d'écrire chaque connecteur. Cela ne change pas l'architecture, car chaque connecteur est isolé.
- Faut-il proposer un export DOCX en plus du PDF ? À décider après les premiers retours d'ATS ; cela ne touche que le moteur de rendu.
- Un cross-encoder NLI local peut-il servir de pré-filtre gratuit avant le juge LLM ? À trancher par les évaluations de M3.
- Le design visuel du gabarit Typst : itératif, sans effet sur les specs.
- La prise en charge de Firefox : WXT le permet, à faire après M5 si besoin.
