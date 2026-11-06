# Tasks

## 1. Fondations du dépôt (M0)

- [x] 1.1 Créer la structure du monorepo (`backend/`, `web/`, `extension/`, `prompts/`, `templates/`, `evals/`), le `.gitignore` (données, `.env`, `node_modules`, `.venv`, builds) et le `Makefile` (`just` n'est pas installé sur la machine) ; vérifier que `make help` affiche `dev`, `test`, `eval`, `build`
- [x] 1.2 Initialiser `backend/` avec uv (Python 3.13 épinglé), FastAPI, Pydantic v2, ruff et pyright, et une route `/api/health` ; vérifier que `uv run pytest` passe sur un test de santé et que `ruff check` et `pyright` sont propres
- [x] 1.3 Mettre en place la configuration (`tailor.toml` + `platformdirs`, dossier de données créé en `700`) et SQLModel + Alembic avec une migration initiale vide ; vérifier par un test que le dossier est créé avec les bonnes permissions et que `alembic upgrade head` puis `downgrade base` fonctionnent
- [x] 1.4 Implémenter la sécurité locale (écoute `127.0.0.1`, jeton de lancement façon Jupyter, contrôle de l'en-tête `Host`, CORS strict) ; vérifier par des tests qu'une requête sans jeton, avec un mauvais `Host` ou depuis une origine étrangère est rejetée
- [x] 1.5 Initialiser `web/` (Vite, React, TS, Router, TanStack Query, Tailwind, shadcn/ui, eslint, vitest), la récupération du jeton depuis l'URL et la génération du client typé depuis l'OpenAPI ; vérifier que `npm run build` passe et que la page d'accueil affiche le statut de `/api/health`
- [x] 1.6 Servir le front buildé depuis FastAPI et câbler `make dev` (backend et Vite avec proxy) ; vérifier que `make dev` ouvre l'application authentifiée dans le navigateur
- [x] 1.7 Rédiger le `README.md` (vision, principes, installation, lancement) ; vérifier en suivant le README depuis un clone propre

## 2. Passerelle LLM (M0)

- [x] 2.1 Définir l'interface `complete(task, prompt_id, inputs, schema)` et le chargement des prompts versionnés depuis `prompts/` (front-matter `version`) ; vérifier par un test qu'un prompt modifié change de version
- [x] 2.2 Implémenter un faux fournisseur déterministe pour les tests et la boucle de validation Pydantic avec relance sur erreur ; vérifier par des tests une réponse valide, une réponse corrigée à la 2e tentative et un échec explicite après la limite
- [x] 2.3 Implémenter l'adaptateur Anthropic (sorties structurées via *tool use*) avec les clés lues dans `keyring` ou l'environnement ; vérifier par un test d'intégration optionnel (ignoré sans clé) et par un test qui confirme que la clé n'apparaît jamais dans les journaux
- [x] 2.4 Implémenter l'adaptateur compatible OpenAI (`base_url` configurable, Ollama) ; vérifier par un test d'intégration optionnel (ignoré sans Ollama) et par des tests unitaires sur `httpx2.MockTransport` (les SDK `anthropic` 2.x et `openai` 3.x reposent sur `httpx2`, que `respx` n'intercepte pas)
- [x] 2.5 Implémenter le routage par tâche avec les valeurs par défaut documentées, le journal `llm_call` (jetons, coût, durée, version de prompt) et le cache ; vérifier par des tests qu'un appel identique est servi depuis le cache et que le journal est rempli
- [x] 2.6 Implémenter le consentement par fournisseur cloud, le mode local strict (refus dans l'adaptateur cloud) et le plafond mensuel ; vérifier par des tests que chaque garde-fou bloque l'appel sans trafic réseau
- [x] 2.7 Ajouter la page « Consommation » (appels récents, coût par jour et par tâche) et l'écran de consentement ; vérifier manuellement dans l'interface avec le faux fournisseur

## 3. Profil maître (M1)

- [x] 3.1 Créer les modèles et migrations `fact`, `fact_revision`, `profile_version`, `preference`, `answer_bank` ; vérifier par des tests qu'une modification crée une révision, conserve l'identifiant et incrémente la version du profil
- [x] 3.2 Implémenter l'extraction du texte des PDF et DOCX, avec le refus explicite des PDF sans couche texte ; vérifier sur des fixtures (PDF texte, PDF scanné, DOCX)
- [x] 3.3 Implémenter l'extraction structurée du CV en faits avec passage source, et le rejet des faits dont le passage est introuvable ; vérifier avec le faux fournisseur et un test d'invariant « passage présent dans le texte »
- [x] 3.4 Créer l'API du profil (brouillon d'import, validation, CRUD des faits, retrait, liens de preuve des compétences, traductions des champs protégés) ; vérifier par des tests d'API, dont le statut « déclarative » ou « étayée » d'une compétence
- [x] 3.5 Créer l'écran d'import et de revue (brouillon à côté de l'extrait source, corrections, validation) et l'éditeur de profil ; vérifier en important un CV fictif de bout en bout dans l'interface
- [x] 3.6 Créer l'écran des préférences de recherche et de la banque de réponses ; vérifier par un test d'API et manuellement dans l'interface
- [x] 3.7 Implémenter l'export JSON complet (avec le schéma documenté dans `docs/export.md`) et la suppression totale avec confirmation ; vérifier par un test aller-retour export → suppression → base vide

## 4. Sourcing des offres (M2)

- [ ] 4.1 Créer le modèle d'offre normalisé (`offer`, `offer_source`), l'assainissement HTML `nh3` et l'interface `SourceConnector` ; vérifier par des tests de normalisation (champ absent marqué « inconnu ») et d'assainissement (balise script retirée)
- [ ] 4.2 Implémenter le connecteur France Travail (OAuth2, pagination par plages, limiteur) ; vérifier sur des réponses enregistrées avec `respx`
- [ ] 4.3 Implémenter le connecteur Adzuna avec le marquage « description partielle » ; vérifier sur des réponses enregistrées
- [ ] 4.4 Implémenter les connecteurs d'ATS (Greenhouse, Lever, Ashby, Workable, Recruitee, SmartRecruiters) et la détection de l'ATS depuis une URL de page carrière ; vérifier par un test par ATS sur réponses enregistrées et un test de détection d'URL, cas non pris en charge compris
- [ ] 4.5 Implémenter le refus des sources interdites (LinkedIn, Indeed…) et l'import manuel (texte, URL publique récupérée une fois, URL derrière connexion refusée) ; vérifier par des tests d'API
- [ ] 4.6 Implémenter la déduplication (clé normalisée + similarité des embeddings) et le cycle de vie « expirée » ; vérifier par des tests sur deux offres identiques venant de deux sources et sur une offre disparue
- [ ] 4.7 Implémenter les recherches enregistrées, le rafraîchissement manuel et planifié (APScheduler), le backoff et l'isolation des pannes ; vérifier par un test où une source en erreur n'empêche pas les autres et où son statut est enregistré
- [ ] 4.8 Implémenter l'heuristique de signalement des textes suspects (motifs d'injection) ; vérifier sur des fixtures d'offres piégées
- [ ] 4.9 Créer les écrans Sources (recherches, entreprises suivies, statut par source) et Import manuel ; vérifier manuellement avec des clés réelles France Travail et Adzuna

## 5. Analyse et matching (M2)

- [ ] 5.1 Implémenter l'analyse d'offre (exigences structurées avec passage source, rejet des passages introuvables, cache) ; vérifier avec le faux fournisseur et un test d'invariant « passage présent dans l'offre »
- [ ] 5.2 Implémenter les filtres rédhibitoires avec leurs raisons (un champ inconnu ne filtre pas) ; vérifier par des tests table-driven sur les préférences
- [ ] 5.3 Implémenter le calcul et le stockage des embeddings locaux (sentence-transformers) et le score préliminaire ; vérifier par un test de cohérence (une offre proche du profil est mieux classée qu'une offre éloignée)
- [ ] 5.4 Implémenter le score détaillé (couverture par exigence avec `fact_id`, formule versionnée, top N) et le marquage « obsolète » après modification du profil ; vérifier par des tests avec le faux fournisseur
- [ ] 5.5 Créer le flux classé (filtres, marqueur « nouveau », vue « offres filtrées ») et le détail d'offre (exigences, statut de couverture, lacunes, proposition d'ajout au profil) ; vérifier manuellement sur des offres réelles collectées en 4.9

## 6. Vérification d'ancrage (M3)

- [ ] 6.1 Implémenter les contrôles déterministes sur les nombres, pourcentages, durées et dates (normalisation FR/EN) ; vérifier par des tests table-driven (« 20 % » contre « 35 % », formats équivalents)
- [ ] 6.2 Constituer le lexique versionné de technologies et implémenter le contrôle des technologies ; vérifier par des tests (technologie ajoutée détectée, compétence du profil acceptée)
- [ ] 6.3 Intégrer spaCy (`fr_core_news_md`, `en_core_web_md`) pour le contrôle des organisations et le contrôle des citations (identifiant inexistant ou retiré) ; vérifier par des tests unitaires
- [ ] 6.4 Implémenter le juge LLM (décomposition en affirmations, jugement par inférence sur les seuls faits cités, sans accès à l'offre) et l'agrégation des verdicts avec veto déterministe ; vérifier par des tests où la couche déterministe l'emporte sur un juge qui accepte à tort
- [ ] 6.5 Implémenter la vérification textuelle des passages d'offre cités pour les affirmations sur l'entreprise ; vérifier par des tests (passage existant accepté, éloge inventé rejeté)
- [ ] 6.6 Implémenter la boucle de réparation (régénération avec raison, limite configurable, repli sur le texte original), le rapport de vérification et le seuil « prêt » avec les affirmations assumées horodatées ; vérifier par des tests de bout en bout du module avec le faux fournisseur

## 7. CV adapté (M3)

- [ ] 7.1 Implémenter le classement des faits par pertinence (embeddings + rerank LLM) et la sélection gloutonne sous budget de longueur ; vérifier par des tests (profil de trois pages réduit, éléments écartés conservés avec leur score)
- [ ] 7.2 Implémenter la réécriture contrainte (schéma de sortie sans champ protégé, entrées limitées aux faits retenus et aux exigences extraites, langue cible) ; vérifier par un test qui confirme que l'offre brute n'apparaît jamais dans le prompt du rédacteur
- [ ] 7.3 Implémenter l'assemblage (champs protégés injectés depuis le profil, traductions utilisateur, signalement des traductions manquantes) ; vérifier par un test : un employeur ou une date altérés par le LLM sont impossibles par construction
- [ ] 7.4 Créer le gabarit Typst du CV (une colonne, polices embarquées) et le rendu PDF avec ajustement à la page par réduction ; vérifier par un test sur le nombre de pages et sur l'absence de troncature
- [ ] 7.5 Implémenter le contrôle de lisibilité ATS (réextraction du texte, présence et ordre des éléments clés) ; vérifier sur un PDF valide et un PDF volontairement cassé
- [ ] 7.6 Implémenter le rapport de couverture des mots-clés, la régénération ciblée d'un élément et la traçabilité (version du profil, modèle, version des prompts) ; vérifier par des tests d'API
- [ ] 7.7 Créer l'écran de revue côte à côte (sources au survol, reformulations en évidence, rapport de vérification, édition avec revérification, assumer ou ajouter au profil) ; vérifier manuellement sur le profil réel et trois offres réelles

## 8. Évaluation qualité (M3)

- [ ] 8.1 Constituer le jeu d'évaluation synthétique versionné (profils fictifs, offres FR et EN bien et mal couvertes, cas adversariaux d'injection et de chiffres ambigus) ; vérifier par un test qu'aucun cas ne contient de donnée du profil réel
- [ ] 8.2 Implémenter le runner `make eval CONFIG=<nom>` et les métriques (taux d'affirmations non étayées, couverture des exigences et des mots-clés, lisibilité ATS, longueur, durée, coût) ; vérifier en l'exécutant avec le faux fournisseur
- [ ] 8.3 Implémenter l'outil d'annotation manuelle des affirmations et le calcul de la précision et du rappel du vérificateur ; vérifier sur un petit lot annoté à la main
- [ ] 8.4 Implémenter le rapport comparatif multi-configurations et le seuil de non-régression (code de sortie non nul) ; vérifier en comparant Anthropic et Ollama et en provoquant un dépassement volontaire
- [ ] 8.5 Documenter la démarche et les premiers résultats dans `evals/README.md` ; vérifier que les commandes documentées s'exécutent telles quelles

## 9. Dossier de candidature (M4)

- [ ] 9.1 Implémenter les tâches de fond persistées (`background_job`), la progression en SSE et la reprise « en échec, relançable » au redémarrage ; vérifier par un test qui simule un redémarrage pendant une tâche
- [ ] 9.2 Implémenter la préparation en un clic (orchestration CV → lettre → réponses, statuts « en préparation », « à relire », « en échec », relance des étapes manquantes, exigence de description complète) ; vérifier par un test d'intégration avec le faux fournisseur
- [ ] 9.3 Implémenter la lettre de motivation ancrée (gabarit Typst, citations de faits et de passages d'offre, vérification) ; vérifier par des tests et sur une offre réelle
- [ ] 9.4 Implémenter les réponses factuelles déterministes (préférences et banque) et les réponses ouvertes générées marquées « à relire » ; vérifier par des tests (prétentions absentes laissées vides et signalées)
- [ ] 9.5 Implémenter la validation « prêt », la convention de nommage des fichiers et l'instantané immuable (fichiers par hash, offre figée, versions) avec duplication pour modifier ; vérifier par un test d'immutabilité après une modification du profil
- [ ] 9.6 Créer l'écran Dossier (pièces, revue, régénération, coût et durée, téléchargement) ; vérifier manuellement en préparant un dossier complet pour une offre réelle

## 10. Suivi des candidatures (M4)

- [ ] 10.1 Implémenter les modèles `application` et `application_event`, les transitions de statut horodatées et le marquage « envoyée » qui déclenche l'instantané ; vérifier par des tests de transitions
- [ ] 10.2 Implémenter les rappels de relance (délai configurable) et l'avertissement anti-doublon (même offre, même entreprise dans le délai) ; vérifier par des tests avec une horloge simulée
- [ ] 10.3 Créer les vues tableau et liste, les notes datées et les statistiques (envois par semaine, taux et délai de réponse) ; vérifier manuellement et par un test sur le calcul des statistiques

## 11. Extension navigateur (M5)

- [ ] 11.1 Initialiser `extension/` avec WXT (MV3, TS, permissions `activeTab`, `scripting`, `storage` et hôtes ATS optionnels) et la règle eslint qui interdit toute soumission programmatique ; vérifier que l'extension se charge non empaquetée et que eslint échoue sur un `form.submit()` de test
- [ ] 11.2 Implémenter l'appairage (code à 6 chiffres, valable 5 minutes, à usage unique, jeton d'extension, CORS lié à l'ID d'extension) côté backend et extension, avec tout le réseau passant par le service worker ; vérifier par des tests backend (code réutilisé refusé) et manuellement
- [ ] 11.3 Implémenter la capture d'offre sur action (texte visible et URL, repli par sélection manuelle) ; vérifier sur une fixture de page d'offre et sur une vraie page Welcome to the Jungle
- [ ] 11.4 Créer les fixtures de formulaires (Greenhouse, Lever, générique, iframe d'une autre origine, champs React contrôlés, champ fichier) et le harnais Playwright pour l'extension ; vérifier que le harnais charge l'extension et ouvre chaque fixture
- [ ] 11.5 Implémenter l'association page ↔ dossier et le moteur de remplissage (setter natif et événements, injection du PDF via `DataTransfer`) ; vérifier par des tests Playwright sur les fixtures
- [ ] 11.6 Implémenter les adaptateurs Greenhouse, Lever, Ashby et Workable ; vérifier par un test Playwright par adaptateur
- [ ] 11.7 Implémenter l'adaptateur générique (dictionnaire de synonymes FR/EN, puis association par LLM sur les seuls libellés avec seuil de confiance, champs incertains laissés vides) ; vérifier sur la fixture générique, dont un champ volontairement ambigu laissé vide
- [ ] 11.8 Implémenter le marquage visuel par provenance, le récapitulatif (remplis par source, obligatoires vides) et l'enregistrement d'une réponse saisie dans la banque ; vérifier par des tests Playwright
- [ ] 11.9 Implémenter la détection de l'envoi (écoute de `submit` en capture) et la confirmation avant marquage ; vérifier par un test Playwright : aucune soumission par l'extension, marquage seulement après confirmation

## 12. Intégration de bout en bout

- [ ] 12.1 Dérouler le parcours complet sur des données fictives (import du CV → recherche → flux classé → Préparer → revue → prêt → pré-remplissage sur fixture → envoi manuel → marquage → relance due) ; vérifier par un test Playwright de bout en bout avec le faux fournisseur
- [ ] 12.2 Dérouler le parcours injection (offre piégée → dossier) avec les fournisseurs réels ; vérifier que le rapport de vérification et les évaluations ne montrent aucune affirmation issue de l'injection
- [ ] 12.3 Lancer `make eval` sur la configuration par défaut et sur une configuration locale, puis consigner les résultats de référence dans `evals/README.md` ; vérifier que le seuil de non-régression passe sur la configuration par défaut

## Workflow follow-up

- Relire les artefacts (proposal, specs, design, tasks) et les ajuster avant de lancer `/opsx:apply`.
- Implémenter jalon par jalon (M0 → M5), en cochant les tâches au fil de l'eau.
- Archiver la change avec `/opsx:archive` une fois le MVP vérifié, pour que les 10 specs deviennent les specs de référence dans `openspec/specs/`.
