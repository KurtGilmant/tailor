# Tailor

Préparer une candidature **de qualité** en un clic : Tailor adapte ton CV à chaque offre,
rédige la lettre et pré-remplit le formulaire. Il ne contient pourtant **aucune ligne inventée** :
chaque phrase générée cite les faits de ton profil dont elle provient, et un vérificateur
bloque tout ce qui n'est pas étayé.

Projet personnel, local, mono-utilisateur, sans aucune visée commerciale.

## Principes

- **Véracité d'abord.** Le CV adapté sélectionne, ordonne et reformule les faits de ton profil
  maître. Il n'ajoute jamais une compétence, ne modifie jamais un chiffre, ne gonfle jamais
  une responsabilité.
- **L'humain envoie.** Tailor prépare et pré-remplit, mais ne soumet jamais une candidature.
- **Local-first.** Tes données restent sur ta machine. Un fournisseur cloud ne reçoit rien sans
  ton consentement explicite, et le mode « local strict » coupe tout envoi.
- **Sources légitimes.** API officielles et publiques uniquement. LinkedIn ou Indeed : capture
  manuelle depuis l'extension, jamais de scraping.

La spécification complète (10 capacités, design, plan de tâches) est dans
[`openspec/changes/bootstrap-tailor-mvp/`](openspec/changes/bootstrap-tailor-mvp/), et se
consulte aussi avec `openspec view`.

## État

| Jalon | Contenu | État |
|---|---|---|
| M0 | Fondations, sécurité locale, passerelle LLM | ✅ |
| M1 | Profil maître (import du CV, faits révisionnés, préférences) | ✅ |
| M2 | Offres et matching | à faire |
| M3 | Vérification d'ancrage, CV adapté, évaluation | à faire |
| M4 | Dossier de candidature et suivi | à faire |
| M5 | Extension navigateur | à faire |

## Installation

Prérequis : macOS, [uv](https://docs.astral.sh/uv/), Node 20 ou plus récent, `make`.

```bash
make install    # dépendances Python (uv, Python 3.13) et front (npm)
make build      # build du front, servi ensuite par le backend
cd backend && uv run tailor
```

La commande `tailor` affiche une URL du type `http://127.0.0.1:8765/?token=…` et l'ouvre dans
le navigateur. Le jeton change à chaque lancement : c'est lui qui empêche les autres pages
web d'accéder à l'API locale.

Les données sont stockées dans `~/Library/Application Support/Tailor/` (droits `700`), jamais
dans le dépôt. Pour isoler un essai : `TAILOR_HOME=/chemin/jetable uv run tailor`.

### Configurer les modèles

Sans configuration, toutes les tâches utilisent `claude-opus-5-5` via l'API Anthropic. Pour
fournir ta clé, deux options :

```bash
export ANTHROPIC_API_KEY=...                              # option 1 : variable d'environnement
cd backend && uv run python -m keyring set tailor anthropic  # option 2 : trousseau macOS
```

Au premier appel, l'application te demande ton consentement (page **Consommation**). Le
routage par tâche, le mode local strict, le plafond mensuel et les modèles locaux (Ollama) se
règlent dans `tailor.toml` : voir [`tailor.example.toml`](tailor.example.toml).

## Développement

```bash
make dev        # backend avec rechargement (:8765) + Vite (:5173) avec proxy
make test       # pytest + vitest
make lint       # ruff + eslint
make typecheck  # pyright + tsc
make api-client # régénère le client TypeScript depuis l'OpenAPI du backend
```

En mode dev, ouvre l'URL `http://localhost:5173/?token=…` affichée par le backend. Le jeton
de dev est conservé entre deux rechargements.

Les tests n'appellent aucun fournisseur réel : ils utilisent un faux fournisseur déterministe
et `httpx2.MockTransport`. Les deux tests d'intégration réels s'activent tout seuls quand
`ANTHROPIC_API_KEY` est définie ou qu'Ollama tourne sur `:11434` :

```bash
cd backend && uv run pytest -m integration
```

## Structure

```
backend/     API FastAPI + logique métier (paquet `tailor`)
  src/tailor/llm/   passerelle LLM : routage, adaptateurs, garde-fous, journal, cache
web/         interface React + Vite + TypeScript (shadcn/ui)
extension/   extension Chrome MV3 (jalon M5)
prompts/     prompts versionnés (voir prompts/README.md)
templates/   gabarits Typst du CV et de la lettre (jalon M3)
evals/       jeu d'évaluation et runner (jalon M3)
openspec/    spécification et plan de travail
```
