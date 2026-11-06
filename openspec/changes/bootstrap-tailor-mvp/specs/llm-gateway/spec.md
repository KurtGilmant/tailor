# Spec Delta

## Purpose

Donner à toutes les fonctionnalités un accès uniforme aux modèles de langage, cloud ou locaux, avec des sorties structurées validées, un routage par tâche, le contrôle des données envoyées et la traçabilité des coûts.

## ADDED Requirements

### Requirement: Fournisseurs interchangeables
Le système SHALL prendre en charge au moins un fournisseur cloud (API Anthropic) et un serveur local compatible avec l'API OpenAI (Ollama par exemple). Changer de fournisseur MUST se faire par configuration, sans modifier les fonctionnalités.

#### Scenario: Bascule vers le local
- **WHEN** l'utilisateur configure la tâche « rédaction » sur un modèle servi par Ollama
- **THEN** la génération suivante utilise ce modèle sans autre modification

### Requirement: Routage par tâche
Le système SHALL associer chaque type de tâche (extraction, notation, rédaction, vérification) à un couple fournisseur et modèle configurable, avec des valeurs par défaut fournies.

#### Scenario: Configuration par défaut
- **WHEN** l'utilisateur lance l'application sans configuration de routage
- **THEN** chaque type de tâche utilise le modèle par défaut documenté

### Requirement: Sorties structurées validées
Les réponses attendues sous forme structurée SHALL être validées contre leur schéma. Une réponse invalide SHALL être redemandée avec l'erreur de validation, dans une limite configurable de tentatives, puis MUST produire un échec explicite plutôt qu'un résultat partiel.

#### Scenario: Réponse non conforme
- **WHEN** un modèle renvoie deux fois de suite une réponse non conforme au schéma, avec une limite de deux tentatives
- **THEN** l'appel échoue avec une erreur explicite indiquant la tâche et le schéma attendu

### Requirement: Consentement avant envoi au cloud
Avant le premier envoi de données du profil à un fournisseur cloud, le système SHALL demander le consentement explicite de l'utilisateur, en nommant le fournisseur. Sans ce consentement, le système MUST n'effectuer aucun appel cloud.

#### Scenario: Première utilisation du cloud
- **WHEN** une tâche routée vers un fournisseur cloud va s'exécuter pour la première fois
- **THEN** le système demande le consentement en nommant le fournisseur et les données concernées
- **AND** n'appelle pas le fournisseur en cas de refus

### Requirement: Mode local strict
Le système SHALL proposer un mode « local strict » dans lequel aucune donnée du profil ni des offres ne quitte la machine. Dans ce mode, une tâche sans modèle local configuré MUST échouer explicitement au lieu de basculer vers le cloud.

#### Scenario: Tâche sans modèle local
- **WHEN** le mode local strict est actif et que la tâche « vérification » n'a pas de modèle local configuré
- **THEN** la tâche échoue avec un message demandant de configurer un modèle local
- **AND** aucun appel réseau vers un fournisseur cloud n'a lieu

### Requirement: Journal local des appels
Le système SHALL journaliser localement chaque appel : tâche, fournisseur, modèle, version du prompt, jetons, coût estimé, durée et résultat. Les clés d'API MUST ne jamais apparaître dans le journal.

#### Scenario: Consultation du journal
- **WHEN** l'utilisateur ouvre la page « Consommation »
- **THEN** il voit les appels récents et le coût cumulé par jour et par tâche

### Requirement: Cache des appels identiques
Un appel identique à un appel précédent (même modèle, même version de prompt, mêmes entrées) SHALL être servi depuis le cache local, sauf si l'utilisateur demande explicitement une régénération.

#### Scenario: Réanalyse d'une offre inchangée
- **WHEN** l'extraction des exigences est relancée sur une offre inchangée avec le même modèle et la même version de prompt
- **THEN** le résultat est servi depuis le cache, sans appel au fournisseur

### Requirement: Prompts versionnés
Chaque prompt SHALL avoir un identifiant de version, enregistré avec chaque résultat qu'il produit.

#### Scenario: Modification d'un prompt
- **WHEN** un prompt est modifié
- **THEN** sa version change et les nouveaux résultats enregistrent la nouvelle version

### Requirement: Plafond de dépenses
Le système SHALL permettre de fixer un plafond de dépenses mensuel pour les fournisseurs cloud. Une fois ce plafond atteint, les appels cloud MUST être refusés avec un message explicite jusqu'au mois suivant ou jusqu'à une hausse du plafond.

#### Scenario: Plafond atteint
- **WHEN** le coût cumulé du mois atteint le plafond configuré
- **THEN** la préparation d'un nouveau dossier via un fournisseur cloud est refusée avec le montant consommé et le plafond
