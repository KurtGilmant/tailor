# Spec Delta

## Purpose

Classer les offres selon leur adéquation réelle avec le profil et expliquer ce classement, pour ne préparer de candidature que là où elle a du sens.

## ADDED Requirements

### Requirement: Extraction structurée des exigences
Le système SHALL extraire de chaque offre une liste structurée d'exigences : compétences indispensables, compétences appréciées, années d'expérience, niveau de séniorité, langues, formation, contrat, lieu et télétravail. Chaque exigence MUST être reliée au passage de l'offre dont elle provient.

#### Scenario: Exigence tracée
- **WHEN** l'utilisateur consulte les exigences extraites d'une offre
- **THEN** chaque exigence affiche le passage exact de l'offre qui la justifie

#### Scenario: Exigence non trouvée dans le texte
- **WHEN** l'extraction produit une exigence dont le passage cité n'existe pas dans l'offre
- **THEN** cette exigence est rejetée et n'est pas utilisée pour le score

### Requirement: Filtres rédhibitoires
Le système SHALL appliquer les préférences de recherche (type de contrat, lieu et télétravail, entreprises exclues, langues de travail) comme filtres avant tout calcul de score. Une offre filtrée SHALL rester consultable avec la raison du filtrage.

#### Scenario: Contrat incompatible
- **WHEN** l'utilisateur cherche une alternance et qu'une offre est un CDI
- **THEN** l'offre est masquée du flux par défaut
- **AND** reste visible dans la vue « offres filtrées » avec la raison « type de contrat »

#### Scenario: Critère inconnu
- **WHEN** le type de contrat d'une offre est « inconnu »
- **THEN** l'offre n'est pas filtrée sur ce critère
- **AND** le critère est signalé « à vérifier » dans le détail de l'offre

### Requirement: Score d'adéquation explicable
Le système SHALL attribuer à chaque offre non filtrée un score de 0 à 100. Le score MUST s'accompagner, pour chaque exigence, d'un statut (couverte, partielle, absente) et des faits du profil qui la couvrent. Aucun score ne SHALL être affiché sans son explication.

#### Scenario: Détail du score
- **WHEN** l'utilisateur ouvre une offre notée 78
- **THEN** il voit chaque exigence avec son statut
- **AND** pour chaque exigence couverte, les faits du profil qui la couvrent

### Requirement: Lacunes sans incitation à mentir
Le système SHALL lister les exigences indispensables non couvertes. Il MUST ne jamais proposer d'ajouter une lacune au CV ; il SHALL seulement proposer de l'ajouter au profil si l'utilisateur confirme qu'elle est vraie.

#### Scenario: Lacune réellement maîtrisée
- **WHEN** une offre exige « SQL », que le profil ne le mentionne pas, et que l'utilisateur indique le maîtriser
- **THEN** le système propose de créer un fait « SQL » dans le profil, à étayer par une expérience ou un projet
- **AND** ne modifie aucun CV tant que ce fait n'est pas enregistré

### Requirement: Score préliminaire et score détaillé
Le système SHALL calculer un score préliminaire peu coûteux pour toutes les offres non filtrées, et un score détaillé uniquement pour les N meilleures offres de chaque rafraîchissement (N configurable) ou à la demande. Un score préliminaire MUST être affiché comme tel.

#### Scenario: Offre hors du top N
- **WHEN** une offre n'est pas dans les N meilleures après un rafraîchissement
- **THEN** elle affiche un score marqué « préliminaire »
- **AND** l'utilisateur peut demander son score détaillé en un clic

### Requirement: Flux d'offres classé
Le système SHALL présenter les offres dans un flux trié par score, filtrable par source, date de publication, statut de candidature et score minimal, et SHALL distinguer les offres apparues depuis la dernière visite.

#### Scenario: Nouvelles offres
- **WHEN** l'utilisateur ouvre le flux après un rafraîchissement
- **THEN** les offres apparues depuis sa dernière visite portent un marqueur « nouveau »

### Requirement: Recalcul après modification du profil
Quand le profil change, le système SHALL marquer les scores détaillés existants comme « obsolètes » et SHALL les recalculer à la demande ou en tâche de fond.

#### Scenario: Ajout d'une compétence
- **WHEN** l'utilisateur ajoute une compétence au profil
- **THEN** les scores détaillés existants affichent un marqueur « obsolète » jusqu'à leur recalcul
