# Proposal

## Why

Bien préparer une candidature prend 30 à 60 minutes : relire l'offre, réordonner son CV, reformuler des puces avec le vocabulaire de l'annonce, rédiger une lettre, puis remplir un formulaire qui redemande tout ce qui figure déjà dans le CV. Les outils d'« auto-apply » existants règlent le problème en envoyant en masse des CV génériques, ou des CV « optimisés » par IA qui inventent des compétences.

Tailor prend le parti inverse. Il ramène la préparation d'une candidature **de qualité** à un clic, garantit que chaque ligne du CV adapté est vraie et reliée à sa source, et laisse toujours l'envoi à l'humain. C'est un projet personnel, local et mono-utilisateur, sans aucune visée commerciale. Il sert aussi de terrain d'apprentissage sur les sujets IA les plus exigeants : génération ancrée (*grounded generation*), vérification d'affirmations, évaluation de LLM et robustesse à l'injection de prompt.

## What Changes

Ce bootstrap couvre le MVP de bout en bout, de zéro.

- **Profil maître** : import d'un CV PDF/DOCX, extrait en une base de **faits atomiques identifiés** (expériences, réalisations, compétences étayées, formations, projets). C'est un sur-ensemble du CV, enrichi au fil de l'eau, qui s'accompagne des préférences de recherche (contrat, lieu, télétravail, disponibilité…).
- **Sourcing d'offres légitime** : API France Travail, Adzuna, API publiques des ATS (Greenhouse, Lever, Ashby, Workable, Recruitee, SmartRecruiters) via une liste d'entreprises suivies, et import manuel (texte, URL ou capture depuis l'extension). Les offres sont normalisées et dédupliquées.
- **Matching explicable** : extraction structurée des exigences de l'offre, filtres rédhibitoires, puis un score détaillé exigence par exigence. Chaque exigence est soit couverte par un fait du profil, soit signalée comme lacune.
- **CV adapté ancré** : sélection, réordonnancement et reformulation des seuls faits du profil, sous contrainte de longueur et dans la langue de l'offre. Chaque élément cite ses faits sources, et les champs factuels (employeurs, intitulés, dates, diplômes) ne passent jamais par le LLM.
- **Vérification d'ancrage** : chaque affirmation générée est contrôlée par une couche déterministe (chiffres, dates, technologies), qui a un droit de veto, puis par un juge LLM qui ne voit que les faits cités. Aucun document n'est déclaré « prêt » tant qu'une affirmation reste non étayée.
- **Dossier de candidature en un clic** : CV PDF compatible ATS, lettre de motivation et réponses aux questions usuelles. Le dossier est relu, modifiable, puis figé sous forme d'instantané au moment de l'envoi.
- **Suivi des candidatures** : statuts, relances, anti-doublon, historique exact de ce qui a été envoyé.
- **Extension navigateur** : capture d'une offre depuis la page consultée, pré-remplissage du formulaire de candidature (identité, CV joint, réponses) avec un marquage visible de chaque champ rempli. L'extension **ne soumet jamais** le formulaire.
- **Passerelle LLM** : fournisseurs cloud et locaux interchangeables, routage par tâche, sorties structurées validées, journal local des coûts, cache, mode « local strict ».
- **Évaluation qualité** : un jeu de cas synthétiques (dont des cas adversariaux), des métriques de véracité, de couverture et de lisibilité ATS, et la comparaison des fournisseurs, modèles et versions de prompts.

Hors périmètre, explicitement :
- tout envoi automatique de candidature, toute résolution de captcha ;
- le scraping de LinkedIn, Indeed ou de tout site dont les CGU l'interdisent ;
- le multi-utilisateur, l'hébergement, les comptes, la monétisation ;
- l'ajout au CV de compétences ou d'expériences absentes du profil, quelle que soit la demande de l'offre ;
- l'envoi d'e-mails de relance (le système rappelle, l'humain écrit).

## Capabilities

### New Capabilities

- `candidate-profile` : profil maître du candidat (faits atomiques identifiés et versionnés, import de CV, préférences de recherche, export et suppression des données).
- `job-sourcing` : collecte des offres depuis des sources légitimes, import manuel, normalisation, déduplication, cycle de vie et traitement du contenu d'offre comme donnée non fiable.
- `job-matching` : extraction des exigences, filtres rédhibitoires, score d'adéquation explicable, lacunes et flux d'offres classé.
- `cv-tailoring` : génération du CV adapté à une offre à partir des seuls faits du profil, contraintes de format et de langue, revue côte à côte.
- `grounding-verification` : vérification, affirmation par affirmation, que tout texte généré sur le candidat est étayé par le profil, et seuil bloquant avant le statut « prêt ».
- `application-kit` : assemblage en un clic du dossier (CV PDF compatible ATS, lettre, réponses), régénération partielle et instantané figé à l'envoi.
- `application-tracking` : cycle de vie des candidatures, relances, anti-doublon et statistiques.
- `browser-autofill` : extension navigateur (appairage local, capture d'offre, pré-remplissage transparent, détection de l'envoi, jamais de soumission automatique).
- `llm-gateway` : accès uniforme aux modèles (cloud et local), routage par tâche, sorties structurées, journal, cache, mode local strict et plafond de dépenses.
- `quality-evaluation` : jeu d'évaluation synthétique, métriques de véracité et de qualité, comparaison de configurations et contrôle de non-régression.

### Modified Capabilities

Aucune : le projet part de zéro.

## Impact

- **Nouveau dépôt** `~/tailor` (monorepo) : `backend/` (FastAPI), `web/` (React), `extension/` (Chrome MV3), `prompts/`, `templates/`, `evals/`.
- **Dépendances externes** : API France Travail (inscription gratuite sur francetravail.io), API Adzuna (clé gratuite), endpoints publics des ATS, API Anthropic (payante à l'usage, plafonnable), Ollama en option pour le mode local.
- **Données personnelles** : CV, préférences et historique de candidatures restent stockés localement. Ils ne partent vers un fournisseur cloud qu'après consentement explicite, et le mode local strict permet de l'empêcher totalement.
- **Coûts** : quelques appels LLM par offre analysée et par dossier préparé, mesurés par le journal local et bornés par un plafond mensuel configurable.
