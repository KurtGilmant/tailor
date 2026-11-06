# Spec Delta

## Purpose

Suivre chaque candidature de sa préparation jusqu'à la réponse, en gardant l'historique exact de ce qui a été envoyé et en rappelant les relances à faire.

## ADDED Requirements

### Requirement: Cycle de vie d'une candidature
Une candidature SHALL avoir l'un des statuts suivants : « à relire », « prête », « envoyée », « relancée », « entretien », « offre reçue », « refusée », « abandonnée ». Chaque changement de statut SHALL être horodaté et conservé dans l'historique.

#### Scenario: Passage en entretien
- **WHEN** l'utilisateur passe une candidature de « envoyée » à « entretien »
- **THEN** le nouveau statut et sa date apparaissent dans l'historique de la candidature

### Requirement: Marquage de l'envoi
Une candidature SHALL passer au statut « envoyée » uniquement sur confirmation de l'utilisateur, que ce soit depuis l'application ou en réponse à une proposition de l'extension. Ce marquage MUST déclencher l'instantané figé du dossier.

#### Scenario: Marquage manuel
- **WHEN** l'utilisateur clique sur « Marquer comme envoyée » pour un dossier prêt
- **THEN** la candidature passe au statut « envoyée » à la date du jour
- **AND** l'instantané du dossier est figé

### Requirement: Rappels de relance
Le système SHALL afficher un rappel de relance pour toute candidature « envoyée » restée sans changement de statut au-delà d'un délai configurable (7 jours par défaut). Le système MUST ne jamais envoyer lui-même de message de relance.

#### Scenario: Relance due
- **WHEN** une candidature est « envoyée » depuis 8 jours sans autre changement de statut
- **THEN** elle apparaît dans la liste « relances à faire » du tableau de bord

### Requirement: Anti-doublon
Avant de préparer un dossier, le système SHALL avertir l'utilisateur s'il a déjà candidaté à la même offre, ou à la même entreprise dans un délai configurable.

#### Scenario: Deuxième candidature dans la même entreprise
- **WHEN** l'utilisateur prépare un dossier pour une entreprise à laquelle il a candidaté il y a 10 jours
- **THEN** le système affiche un avertissement avec un lien vers la candidature précédente
- **AND** laisse l'utilisateur poursuivre s'il le confirme

### Requirement: Vues de suivi
Le système SHALL présenter les candidatures en vue tableau par statut et en vue liste triable, et SHALL afficher des statistiques simples : candidatures envoyées par semaine, taux de réponse et délai moyen de réponse.

#### Scenario: Statistiques
- **WHEN** l'utilisateur ouvre le tableau de bord
- **THEN** il voit le nombre de candidatures envoyées par semaine et le taux de réponse

### Requirement: Notes libres
L'utilisateur SHALL pouvoir ajouter des notes datées à chaque candidature (contact, échange, préparation d'entretien).

#### Scenario: Ajout d'une note
- **WHEN** l'utilisateur ajoute une note à une candidature
- **THEN** la note apparaît datée dans l'historique de la candidature
