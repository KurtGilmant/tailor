# Spec Delta

## Purpose

Assembler en un clic, pour une offre, le dossier de candidature complet (CV, lettre, réponses) prêt à être relu, puis le figer tel qu'il a été envoyé.

## ADDED Requirements

### Requirement: Préparation en un clic
Le système SHALL permettre, en une seule action depuis une offre, de lancer la préparation d'un dossier contenant le CV adapté, la lettre de motivation et les réponses aux questions usuelles. La préparation SHALL s'exécuter en tâche de fond avec une progression visible.

#### Scenario: Lancement de la préparation
- **WHEN** l'utilisateur clique sur « Préparer » depuis une offre
- **THEN** un dossier est créé au statut « en préparation » et sa progression s'affiche étape par étape
- **AND** le dossier passe au statut « à relire » quand toutes les pièces sont générées et vérifiées

#### Scenario: Échec d'une étape
- **WHEN** une étape de la préparation échoue (fournisseur LLM indisponible, par exemple)
- **THEN** le dossier passe au statut « en échec » avec la cause
- **AND** l'utilisateur peut relancer uniquement les étapes manquantes

### Requirement: Lettre de motivation ancrée
Le système SHALL générer une lettre de motivation fondée sur les faits du profil et sur les seuls éléments de l'offre, dans la langue du CV, avec une longueur cible configurable. La lettre MUST passer par la vérification d'ancrage.

#### Scenario: Lettre générée
- **WHEN** la lettre d'un dossier est générée
- **THEN** chaque affirmation sur le candidat cite un fait du profil
- **AND** chaque affirmation sur l'entreprise cite un passage de l'offre

### Requirement: Réponses factuelles déterministes
Les réponses aux questions factuelles (prétentions salariales, date de disponibilité, autorisation de travail, préavis, liens de profil) SHALL provenir des préférences et de la banque de réponses, sans génération. Une question factuelle sans réponse connue MUST rester vide et être signalée.

#### Scenario: Prétentions non renseignées
- **WHEN** le dossier doit répondre à « Quelles sont vos prétentions salariales ? » et que la préférence n'est pas renseignée
- **THEN** la réponse reste vide et est signalée « à compléter »

### Requirement: Réponses ouvertes générées et signalées
Les réponses aux questions ouvertes (« Pourquoi nous rejoindre ? ») SHALL être générées, vérifiées, puis marquées comme générées pour être relues avant usage.

#### Scenario: Question ouverte
- **WHEN** un dossier contient une réponse générée à une question ouverte
- **THEN** elle porte un marqueur « générée, à relire »

### Requirement: PDF compatible ATS
Le CV et la lettre SHALL être rendus en PDF compatible avec les ATS : une seule colonne, texte sélectionnable, intitulés de section standards, aucune image ni tableau de mise en page, polices embarquées. Le nom de fichier SHALL suivre la convention `Prenom_Nom_CV_Entreprise.pdf`.

#### Scenario: Contrôle de lisibilité automatique
- **WHEN** un PDF de CV est produit
- **THEN** le système en réextrait le texte et vérifie que le nom, l'e-mail, chaque section et chaque intitulé d'expérience sont lisibles dans le bon ordre
- **AND** signale tout échec de ce contrôle dans la revue

#### Scenario: Dépassement de page
- **WHEN** le rendu d'un CV ciblé sur une page produit deux pages
- **THEN** le système retire l'élément le moins pertinent et refait le rendu jusqu'à tenir sur la longueur cible

### Requirement: Revue et validation du dossier
L'utilisateur SHALL pouvoir relire, modifier et régénérer chaque pièce du dossier. Le dossier SHALL passer au statut « prêt » uniquement quand toutes ses pièces respectent le seuil de la vérification d'ancrage.

#### Scenario: Validation du dossier
- **WHEN** toutes les pièces sont vérifiées sans affirmation non étayée et que l'utilisateur valide
- **THEN** le dossier passe au statut « prêt » et ses fichiers sont téléchargeables

### Requirement: Instantané figé à l'envoi
Quand une candidature est marquée comme envoyée, le système SHALL figer un instantané du dossier : fichiers exacts, texte de l'offre à cette date, version du profil, modèles et versions des prompts. Un instantané MUST ne plus jamais être modifié.

#### Scenario: Consultation d'un dossier envoyé
- **WHEN** l'utilisateur rouvre une candidature envoyée trois semaines plus tôt alors que le profil a changé depuis
- **THEN** il voit exactement le CV, la lettre et les réponses envoyés, ainsi que l'offre telle qu'elle était

#### Scenario: Tentative de modification
- **WHEN** l'utilisateur tente de modifier une pièce d'un dossier figé
- **THEN** le système propose de créer un nouveau dossier à partir de celui-ci au lieu de le modifier

### Requirement: Coût et durée affichés
Chaque dossier SHALL afficher le nombre d'appels LLM, les jetons consommés, le coût estimé et la durée de préparation.

#### Scenario: Coût d'un dossier
- **WHEN** l'utilisateur consulte un dossier préparé
- **THEN** il voit son coût estimé et sa durée de préparation
