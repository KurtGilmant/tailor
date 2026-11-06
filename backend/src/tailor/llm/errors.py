"""Erreurs de la passerelle LLM. Les messages sont destinés à l'utilisateur : en français,
explicites, et sans jamais contenir de clé d'API ni de donnée du profil."""


class LLMError(Exception):
    """Base de toutes les erreurs de la passerelle."""


class ConfigError(LLMError):
    """Configuration [llm] invalide ou incohérente."""


class PromptError(LLMError):
    """Prompt introuvable, mal formé ou variables manquantes."""


class ProviderError(LLMError):
    """Le fournisseur a échoué (réseau, statut HTTP, réponse tronquée…)."""


class RefusalError(LLMError):
    """Le modèle a refusé de répondre (stop_reason « refusal »)."""

    def __init__(self, provider: str, category: str | None) -> None:
        self.category = category
        detail = f" (catégorie : {category})" if category else ""
        super().__init__(f"Le fournisseur {provider} a refusé la demande{detail}.")


class SchemaValidationError(LLMError):
    """La réponse ne respecte toujours pas le schéma après toutes les tentatives."""

    def __init__(self, task: str, schema_name: str, attempts: int, last_error: str) -> None:
        self.last_error = last_error
        super().__init__(
            f"Tâche « {task} » : réponse non conforme au schéma {schema_name} "
            f"après {attempts} tentative(s). Dernière erreur : {last_error}"
        )


class CloudCallBlocked(LLMError):
    """Un garde-fou a empêché un appel vers un fournisseur cloud (aucun trafic réseau)."""


class ConsentRequired(CloudCallBlocked):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(
            f"Consentement requis : autorise l'envoi de tes données au fournisseur "
            f"« {provider} » dans la page Consommation avant la première utilisation."
        )


class LocalStrictModeError(CloudCallBlocked):
    def __init__(self, task: str, provider: str) -> None:
        super().__init__(
            f"Mode local strict : la tâche « {task} » est routée vers le fournisseur cloud "
            f"« {provider} ». Configure un modèle local pour cette tâche dans tailor.toml."
        )


class BudgetExceeded(CloudCallBlocked):
    def __init__(self, spent: float, budget: float) -> None:
        self.spent = spent
        self.budget = budget
        super().__init__(
            f"Plafond mensuel atteint : {spent:.2f} $ consommés pour un plafond de "
            f"{budget:.2f} $. Relève le plafond ou attends le mois prochain."
        )
