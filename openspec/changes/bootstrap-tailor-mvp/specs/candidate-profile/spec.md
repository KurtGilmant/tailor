# Spec Delta

## Purpose

Construire et maintenir le profil maître du candidat : la base de faits vérifiables dont dérive tout contenu généré, ainsi que ses préférences de recherche.

## ADDED Requirements

### Requirement: Import d'un CV existant
Le système SHALL permettre d'importer un CV au format PDF (texte sélectionnable) ou DOCX et SHALL en proposer une version structurée en faits, présentée à l'utilisateur pour validation avant tout enregistrement. Chaque fait proposé MUST être relié à l'extrait du CV dont il provient.

#### Scenario: Import d'un PDF texte
- **WHEN** l'utilisateur importe un CV PDF dont le texte est sélectionnable
- **THEN** le système affiche un brouillon de profil (expériences, réalisations, compétences, formations, projets, langues)
- **AND** chaque élément du brouillon affiche l'extrait source du CV
- **AND** rien n'est enregistré dans le profil tant que l'utilisateur n'a pas validé

#### Scenario: PDF sans couche texte
- **WHEN** l'utilisateur importe un PDF scanné ne contenant aucun texte extractible
- **THEN** le système refuse l'import avec un message expliquant la cause
- **AND** propose l'import DOCX ou la saisie manuelle

#### Scenario: Élément mal extrait
- **WHEN** l'utilisateur corrige ou supprime un élément du brouillon avant validation
- **THEN** seule la version corrigée est enregistrée

### Requirement: Faits atomiques identifiés
Le profil SHALL être composé de faits atomiques (une réalisation, une compétence, une formation, etc.), chacun doté d'un identifiant stable conservé à travers les modifications. Chaque modification d'un fait MUST créer une nouvelle révision sans effacer les précédentes.

#### Scenario: Modification d'un fait
- **WHEN** l'utilisateur reformule une réalisation existante
- **THEN** le fait conserve son identifiant
- **AND** une nouvelle révision est créée et la précédente reste consultable

#### Scenario: Fait référencé par un dossier envoyé
- **WHEN** l'utilisateur retire du profil un fait cité par un dossier déjà envoyé
- **THEN** le fait n'est plus proposé pour les futurs CV
- **AND** le dossier envoyé continue d'afficher la révision du fait qu'il citait

### Requirement: Profil maître sur-ensemble du CV
Le profil SHALL pouvoir contenir plus d'expériences, de réalisations et de projets qu'un CV d'une page, sans limite de longueur, afin de servir de réservoir de faits pour l'adaptation.

#### Scenario: Ajout d'une réalisation hors CV
- **WHEN** l'utilisateur ajoute une réalisation qui ne figurait pas dans le CV importé
- **THEN** elle est enregistrée comme fait du profil et devient sélectionnable pour les CV adaptés

### Requirement: Compétences étayées
Chaque compétence du profil SHALL pouvoir être reliée aux expériences ou projets qui la démontrent. Une compétence sans lien MUST être signalée comme « déclarative ».

#### Scenario: Compétence sans preuve
- **WHEN** l'utilisateur ajoute la compétence « Docker » sans la relier à une expérience ou un projet
- **THEN** la compétence est enregistrée avec le statut « déclarative »
- **AND** l'interface invite à la relier à une expérience ou un projet

#### Scenario: Compétence étayée
- **WHEN** l'utilisateur relie « Docker » à un projet du profil
- **THEN** la compétence passe au statut « étayée » et affiche ce projet comme preuve

### Requirement: Champs factuels protégés
Les champs factuels (nom de l'employeur, intitulé de poste, dates, diplôme, établissement, nom de certification) SHALL être stockés tels que saisis. Le système SHALL permettre à l'utilisateur de renseigner une traduction par champ, seule variante utilisable dans une autre langue.

#### Scenario: Traduction d'un intitulé
- **WHEN** l'utilisateur renseigne « Software Engineer » comme traduction anglaise de l'intitulé « Ingénieur logiciel »
- **THEN** cette traduction est enregistrée et rattachée au champ d'origine

### Requirement: Préférences de recherche
Le système SHALL stocker les préférences de recherche : types de contrat, lieux, télétravail accepté, prétentions salariales, date de disponibilité, langues de travail, autorisation de travail, entreprises exclues. Elles SHALL être réutilisables par le matching et le pré-remplissage.

#### Scenario: Saisie des préférences
- **WHEN** l'utilisateur indique « alternance, Bordeaux ou télétravail complet, disponible le 1er septembre »
- **THEN** ces préférences sont enregistrées et visibles dans les réglages

### Requirement: Banque de réponses
Le système SHALL conserver les réponses que l'utilisateur rédige ou valide pour des questions de candidature récurrentes, afin de les réutiliser à l'identique.

#### Scenario: Réutilisation d'une réponse
- **WHEN** l'utilisateur a validé une réponse à « Quel est votre préavis ? »
- **AND** qu'un nouveau formulaire pose la même question
- **THEN** la réponse validée est proposée telle quelle, sans génération

### Requirement: Versionnement du profil
Le système SHALL attribuer un numéro de version au profil à chaque modification validée, afin que tout contenu généré puisse indiquer la version du profil dont il dérive.

#### Scenario: Version citée par un CV
- **WHEN** un CV adapté est généré
- **THEN** il enregistre la version du profil utilisée

### Requirement: Export et suppression des données
Le système SHALL permettre d'exporter l'intégralité des données de l'utilisateur dans un format JSON documenté, et de les supprimer définitivement après une confirmation explicite.

#### Scenario: Export complet
- **WHEN** l'utilisateur demande un export
- **THEN** il obtient un fichier JSON contenant le profil avec ses révisions, les préférences, les offres, les dossiers et les candidatures

#### Scenario: Suppression
- **WHEN** l'utilisateur confirme la suppression de toutes ses données
- **THEN** la base locale et les fichiers générés sont effacés
- **AND** l'application redémarre sur un profil vide
