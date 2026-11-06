# Spec Delta

## Purpose

Mesurer objectivement la véracité et la qualité des contenus générés, et comparer fournisseurs, modèles et versions de prompts sur un jeu de cas reproductible.

## ADDED Requirements

### Requirement: Jeu d'évaluation synthétique versionné
Le système SHALL disposer d'un jeu d'évaluation versionné de cas (profil, offre), construit uniquement à partir de profils fictifs, qui MUST ne contenir aucune donnée réelle de l'utilisateur.

#### Scenario: Contenu du jeu
- **WHEN** le jeu d'évaluation est chargé
- **THEN** il contient des cas en français et en anglais, des offres bien couvertes et mal couvertes par le profil, et des offres contenant une injection de prompt

### Requirement: Cas adversariaux
Le jeu d'évaluation SHALL inclure des cas conçus pour provoquer une invention : injection de prompt dans l'offre, exigences indispensables absentes du profil, faits sources ambigus ou chiffrés.

#### Scenario: Cas d'injection
- **WHEN** l'évaluation exécute un cas dont l'offre contient une injection de prompt
- **THEN** le rapport indique si une affirmation issue de l'injection apparaît dans le contenu généré

### Requirement: Métriques
Une exécution de l'évaluation SHALL produire au minimum les métriques suivantes : taux d'affirmations non étayées, couverture des exigences, couverture des mots-clés, réussite du contrôle de lisibilité ATS, respect de la longueur cible, durée et coût par dossier.

#### Scenario: Rapport d'exécution
- **WHEN** l'utilisateur lance l'évaluation pour une configuration donnée
- **THEN** il obtient un rapport contenant chaque métrique, globalement et par cas

### Requirement: Évaluation du vérificateur
Le système SHALL permettre d'annoter manuellement des affirmations générées (étayée ou non) et SHALL calculer la précision et le rappel du vérificateur d'ancrage sur ces annotations.

#### Scenario: Rappel du vérificateur
- **WHEN** un ensemble d'affirmations annotées à la main est disponible
- **THEN** le rapport indique la part des affirmations réellement non étayées que le vérificateur a détectées

### Requirement: Comparaison de configurations
Le système SHALL exécuter le même jeu d'évaluation sur plusieurs configurations (fournisseur, modèle, version de prompt) et SHALL produire un rapport comparatif.

#### Scenario: Cloud contre local
- **WHEN** l'utilisateur compare une configuration Anthropic et une configuration Ollama
- **THEN** le rapport présente côte à côte leurs métriques de véracité, de qualité, de durée et de coût

### Requirement: Contrôle de non-régression
La commande d'évaluation SHALL se terminer en échec quand le taux d'affirmations non étayées dépasse un seuil configuré, afin de pouvoir bloquer une modification de prompt ou de modèle qui dégrade la véracité.

#### Scenario: Prompt dégradé
- **WHEN** une nouvelle version de prompt fait dépasser le seuil du taux d'affirmations non étayées
- **THEN** la commande d'évaluation se termine avec un code de sortie non nul et désigne les cas fautifs
