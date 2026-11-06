# Spec Delta

## Purpose

Produire pour une offre donnée un CV adapté qui sélectionne, ordonne et reformule uniquement des faits du profil maître, afin de mettre en avant ce qui compte pour cette offre sans rien inventer.

## ADDED Requirements

### Requirement: Contenu dérivé du seul profil
Chaque élément de contenu du CV adapté (puce, compétence listée, phrase d'accroche) SHALL citer au moins un fait du profil dont il dérive. Le contenu MUST provenir exclusivement du profil ; l'offre sert uniquement à choisir et à orienter.

#### Scenario: Traçabilité d'une puce
- **WHEN** l'utilisateur survole une puce du CV adapté
- **THEN** le ou les faits sources du profil s'affichent

### Requirement: Opérations de transformation autorisées
Le système SHALL se limiter à sélectionner, réordonner, fusionner, raccourcir, traduire et reformuler des faits, y compris en reprenant le vocabulaire de l'offre quand il est strictement équivalent. Le système MUST ne jamais ajouter une compétence ou un outil, modifier un chiffre, ni gonfler un périmètre, une responsabilité ou une séniorité.

#### Scenario: Reformulation avec le vocabulaire de l'offre
- **WHEN** le profil indique « mise en place d'une chaîne d'intégration continue avec GitHub Actions » et que l'offre demande « CI/CD »
- **THEN** la puce peut employer le terme « CI/CD » en citant ce fait

#### Scenario: Gonflement de responsabilité
- **WHEN** le fait source indique « participé au développement d'un modèle de recommandation »
- **THEN** le CV adapté ne contient pas « dirigé le développement d'un modèle de recommandation »

### Requirement: Champs factuels reproduits à l'identique
Les noms d'employeurs, intitulés de poste, dates, diplômes, établissements et noms de certifications SHALL apparaître dans le CV exactement tels qu'ils figurent dans le profil, ou sous la traduction que l'utilisateur a renseignée. Ces champs MUST ne jamais être produits par le modèle de langage.

#### Scenario: CV en anglais sans traduction renseignée
- **WHEN** un CV anglais est généré et que l'intitulé « Ingénieur logiciel » n'a pas de traduction renseignée
- **THEN** l'intitulé apparaît en français tel quel
- **AND** la revue signale qu'une traduction peut être renseignée dans le profil

### Requirement: Sélection sous contrainte de longueur
Le système SHALL sélectionner les faits les plus pertinents pour l'offre dans une longueur cible (une page par défaut, configurable jusqu'à deux). En cas de dépassement, il MUST retirer les éléments les moins pertinents plutôt que tronquer un élément.

#### Scenario: Profil trop long
- **WHEN** le profil contient de quoi remplir trois pages
- **THEN** le CV généré tient sur une page
- **AND** les éléments écartés restent consultables dans la revue avec leur score de pertinence

### Requirement: Langue du CV
Le CV adapté SHALL être rédigé dans la langue de l'offre (français ou anglais) par défaut, et l'utilisateur SHALL pouvoir choisir une autre langue avant ou après génération.

#### Scenario: Offre en anglais
- **WHEN** l'utilisateur prépare un CV pour une offre rédigée en anglais
- **THEN** le CV est généré en anglais

### Requirement: Couverture des mots-clés sans bourrage
Le système SHALL employer la terminologie de l'offre pour les exigences couvertes par le profil et SHALL afficher un rapport de couverture des exigences. Il MUST ne jamais insérer de texte invisible ni de liste de mots-clés non couverts par le profil.

#### Scenario: Rapport de couverture
- **WHEN** un CV adapté est généré
- **THEN** la revue affiche les exigences de l'offre couvertes par le CV et celles non couvertes

### Requirement: Vérification obligatoire
Tout CV adapté SHALL passer par la vérification d'ancrage avant d'être présenté comme « prêt ».

#### Scenario: CV fraîchement généré
- **WHEN** la génération d'un CV adapté se termine
- **THEN** le CV n'est présenté qu'avec son rapport de vérification

### Requirement: Revue côte à côte et édition
Le système SHALL présenter le CV adapté à côté des faits sources, en mettant en évidence les reformulations. Toute modification manuelle de l'utilisateur SHALL être vérifiée à nouveau.

#### Scenario: Ajout manuel d'une information absente du profil
- **WHEN** l'utilisateur modifie une puce en y ajoutant une information absente du profil
- **THEN** la vérification signale l'affirmation comme « non étayée »
- **AND** le système propose soit d'ajouter le fait au profil, soit d'assumer explicitement l'affirmation

### Requirement: Régénération ciblée
L'utilisateur SHALL pouvoir régénérer un seul élément ou une seule section du CV, éventuellement avec une consigne libre, sans modifier le reste.

#### Scenario: Régénération d'une puce
- **WHEN** l'utilisateur demande de régénérer une puce avec la consigne « plus concis »
- **THEN** seule cette puce est remplacée, puis vérifiée

### Requirement: Traçabilité de la génération
Chaque CV adapté SHALL enregistrer l'offre, la version du profil, le fournisseur et le modèle utilisés, ainsi que la version des prompts.

#### Scenario: Consultation des métadonnées
- **WHEN** l'utilisateur consulte les détails d'un CV adapté
- **THEN** il voit la version du profil, le modèle et la version des prompts utilisés
