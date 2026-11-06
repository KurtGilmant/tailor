# Spec Delta

## Purpose

Vérifier que tout texte généré au sujet du candidat (CV, lettre, réponses) est entièrement étayé par le profil maître, et bloquer ce qui ne l'est pas avant que l'utilisateur ne l'envoie.

## ADDED Requirements

### Requirement: Périmètre de la vérification
Le système SHALL vérifier tout élément de texte généré qui affirme quelque chose sur le candidat, dans le CV adapté, la lettre de motivation et les réponses générées aux questions de candidature.

#### Scenario: Réponse générée
- **WHEN** le système génère une réponse à la question « Pourquoi ce poste ? »
- **THEN** cette réponse est vérifiée avant d'être proposée

### Requirement: Vérification affirmation par affirmation
Le système SHALL décomposer chaque élément généré en affirmations atomiques et SHALL classer chacune comme « étayée », « non étayée » ou « contredite » au regard des seuls faits du profil que l'élément cite.

#### Scenario: Élément partiellement étayé
- **WHEN** une puce générée affirme « Développé une API FastAPI utilisée par 3 équipes » et que le fait cité mentionne l'API FastAPI sans le nombre d'équipes
- **THEN** l'affirmation sur l'API est classée « étayée »
- **AND** l'affirmation « utilisée par 3 équipes » est classée « non étayée »

### Requirement: Contrôles déterministes avec droit de veto
Le système SHALL contrôler de façon déterministe que chaque nombre, pourcentage, durée, date, ainsi que chaque nom de technologie, d'outil ou d'organisation présent dans un élément généré, figure dans les faits cités ou dans les compétences du profil. Un échec de ce contrôle MUST classer l'élément « non étayé », quel que soit l'avis du juge LLM.

#### Scenario: Chiffre modifié
- **WHEN** le fait source indique « réduction de 20 % du temps de traitement » et que la puce générée indique « 35 % »
- **THEN** l'élément est classé « contredit » par le contrôle déterministe

#### Scenario: Technologie ajoutée
- **WHEN** une puce générée mentionne « Kubernetes » alors qu'aucun fait cité ni aucune compétence du profil ne le mentionne
- **THEN** l'élément est classé « non étayé », même si le juge LLM l'a accepté

### Requirement: Citations valides
Un élément généré qui ne cite aucun fait, ou qui cite un fait inexistant ou retiré du profil, SHALL être classé « non étayé ».

#### Scenario: Identifiant inventé
- **WHEN** un élément généré cite un identifiant de fait absent du profil
- **THEN** l'élément est classé « non étayé »

### Requirement: L'offre n'est jamais une preuve
Le contenu de l'offre MUST ne jamais être accepté comme preuve d'une affirmation sur le candidat. La vérification d'une affirmation sur le candidat SHALL s'appuyer exclusivement sur le profil.

#### Scenario: Affirmation copiée de l'offre
- **WHEN** l'offre mentionne « maîtrise de Spark exigée » et qu'un élément généré affirme que le candidat maîtrise Spark sans fait correspondant dans le profil
- **THEN** l'affirmation est classée « non étayée »

### Requirement: Affirmations sur l'entreprise
Dans la lettre de motivation et les réponses générées, toute affirmation sur l'entreprise ou le poste SHALL citer un passage de l'offre, qui MUST exister textuellement dans l'offre enregistrée.

#### Scenario: Éloge inventé
- **WHEN** la lettre affirme « votre engagement reconnu pour l'environnement » sans passage correspondant dans l'offre
- **THEN** cette affirmation est classée « non étayée »

### Requirement: Réparation puis repli
Un élément classé « non étayé » ou « contredit » SHALL être régénéré avec la raison de l'échec, dans la limite d'un nombre de tentatives configurable. Une fois ce nombre atteint, l'élément MUST être remplacé par le texte original du fait source et signalé à l'utilisateur.

#### Scenario: Échec persistant
- **WHEN** une puce échoue encore à la vérification après le nombre maximal de tentatives
- **THEN** elle est remplacée par le texte original du fait qu'elle cite
- **AND** elle est signalée « reformulation abandonnée » dans la revue

### Requirement: Rapport de vérification
Le système SHALL produire, pour chaque document généré, un rapport listant le nombre d'affirmations vérifiées et chaque affirmation signalée avec sa raison. Ce rapport SHALL être visible pendant la revue du document.

#### Scenario: Consultation du rapport
- **WHEN** l'utilisateur ouvre la revue d'un CV adapté
- **THEN** il voit le nombre d'affirmations vérifiées et le détail des affirmations signalées

### Requirement: Seuil bloquant avant le statut « prêt »
Un document SHALL passer au statut « prêt » seulement si aucune affirmation n'y reste « non étayée » ou « contredite », à l'exception de celles que l'utilisateur a explicitement assumées une par une.

#### Scenario: Document avec une affirmation non étayée
- **WHEN** un document contient une affirmation « non étayée » que l'utilisateur n'a pas assumée
- **THEN** le document reste au statut « à relire »
- **AND** l'action « marquer comme prêt » est indisponible avec la raison affichée

#### Scenario: Affirmation assumée par l'utilisateur
- **WHEN** l'utilisateur assume explicitement une affirmation non étayée
- **THEN** cette décision est enregistrée et horodatée
- **AND** le système propose d'ajouter le fait correspondant au profil
