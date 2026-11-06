# Spec Delta

## Purpose

Fournir une extension navigateur qui capture une offre depuis la page consultée et pré-remplit le formulaire de candidature avec le dossier préparé, de façon transparente et sans jamais l'envoyer.

## ADDED Requirements

### Requirement: Appairage avec l'application locale
L'extension SHALL communiquer uniquement avec l'application locale, sur l'adresse de bouclage de la machine, après un appairage par code à usage unique affiché dans l'application. L'application MUST rejeter toute requête d'une extension non appairée ou d'une autre origine.

#### Scenario: Appairage réussi
- **WHEN** l'utilisateur saisit dans l'extension le code affiché par l'application
- **THEN** l'extension est appairée et le code ne peut plus être réutilisé

#### Scenario: Requête non appairée
- **WHEN** une page web ou une extension non appairée envoie une requête à l'application locale
- **THEN** la requête est rejetée sans exposer de donnée

### Requirement: Aucune lecture de page sans action
L'extension SHALL lire le contenu d'une page uniquement à la suite d'une action explicite de l'utilisateur sur cette page. Elle MUST ne jamais naviguer, ouvrir d'onglet ni parcourir de site en arrière-plan.

#### Scenario: Navigation ordinaire
- **WHEN** l'utilisateur navigue sur des sites sans interagir avec l'extension
- **THEN** l'extension ne lit ni ne transmet aucun contenu de page

### Requirement: Capture d'une offre
L'extension SHALL permettre, sur action de l'utilisateur, de capturer l'offre affichée dans la page courante (texte visible et URL) et de l'envoyer à l'application comme import manuel.

#### Scenario: Capture sur un site non pris en charge par le sourcing
- **WHEN** l'utilisateur clique sur « Capturer cette offre » depuis une offre affichée dans son navigateur
- **THEN** l'offre apparaît dans le flux de l'application avec l'URL de la page comme source

#### Scenario: Page sans offre identifiable
- **WHEN** l'utilisateur capture une page où aucun texte d'offre n'est identifiable
- **THEN** l'extension l'indique et propose de sélectionner manuellement le texte à capturer

### Requirement: Association de la page à un dossier
Sur une page de candidature, l'extension SHALL retrouver le dossier prêt qui correspond à l'offre (URL de candidature ou offre associée) ou SHALL laisser l'utilisateur en choisir un.

#### Scenario: Dossier reconnu
- **WHEN** l'utilisateur ouvre l'URL de candidature d'une offre dont le dossier est prêt
- **THEN** l'extension affiche ce dossier et propose « Pré-remplir »

### Requirement: Pré-remplissage sur action
Sur clic de l'utilisateur, l'extension SHALL remplir les champs d'identité et de liens, joindre le PDF du CV (et de la lettre si un champ existe) et remplir les réponses du dossier. Seules des données du dossier et du profil MUST être utilisées.

#### Scenario: Formulaire d'un ATS pris en charge
- **WHEN** l'utilisateur clique sur « Pré-remplir » sur un formulaire Greenhouse, Lever, Ashby ou Workable
- **THEN** les champs connus sont remplis et le CV est joint au champ de fichier prévu

#### Scenario: Formulaire générique
- **WHEN** l'utilisateur clique sur « Pré-remplir » sur un formulaire d'un site inconnu
- **THEN** l'extension remplit les champs qu'elle associe avec une confiance suffisante

### Requirement: Jamais d'envoi automatique
L'extension MUST ne jamais soumettre un formulaire, ne jamais cliquer sur un bouton d'envoi et ne jamais tenter de résoudre un captcha. L'envoi SHALL toujours résulter d'une action de l'utilisateur.

#### Scenario: Après le pré-remplissage
- **WHEN** le pré-remplissage est terminé
- **THEN** le formulaire reste sur la page, non soumis, et l'extension invite l'utilisateur à relire puis à envoyer lui-même

### Requirement: Transparence du remplissage
L'extension SHALL mettre en évidence chaque champ rempli et indiquer sa provenance (profil, préférence, banque de réponses ou réponse générée). Les réponses générées SHALL être marquées distinctement, et les champs obligatoires restés vides SHALL être listés.

#### Scenario: Récapitulatif après remplissage
- **WHEN** le pré-remplissage est terminé
- **THEN** l'extension affiche le nombre de champs remplis par provenance
- **AND** la liste des champs obligatoires restés vides

### Requirement: Champs incertains laissés vides
Un champ que l'extension ne peut pas associer avec une confiance suffisante MUST rester vide. L'utilisateur SHALL pouvoir enregistrer la réponse qu'il y saisit dans la banque de réponses pour les prochaines fois.

#### Scenario: Question inconnue
- **WHEN** un formulaire contient la question « Comment avez-vous connu notre entreprise ? » sans réponse connue
- **THEN** le champ reste vide et signalé
- **AND** après saisie, l'extension propose d'enregistrer la réponse dans la banque

### Requirement: Détection de l'envoi
Quand l'utilisateur soumet lui-même un formulaire pré-rempli, l'extension SHALL proposer de marquer la candidature comme envoyée, et SHALL attendre sa confirmation pour le faire.

#### Scenario: Envoi détecté
- **WHEN** l'utilisateur soumet un formulaire que l'extension a pré-rempli
- **THEN** l'extension propose « Marquer comme envoyée ? »
- **AND** la candidature n'est marquée qu'après confirmation
