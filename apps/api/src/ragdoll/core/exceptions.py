class ApplicationError(Exception):
    """Base application exception translated to RFC 7807 responses."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 500,
        title: str = "Application error",
        type_uri: str = "https://ragdoll.dev/problems/application-error",
        code: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.title = title
        self.type_uri = type_uri
        self.code = code


class ConfigurationError(ApplicationError):
    """Raised when required runtime configuration is missing or invalid."""

    def __init__(self, detail: str = "Runtime configuration is incomplete.") -> None:
        super().__init__(
            detail,
            status_code=500,
            title="Configuration error",
            type_uri="https://ragdoll.dev/problems/configuration-error",
            code="configuration_error",
        )


class RuntimeScaffoldNotReadyError(ApplicationError):
    """Raised when a placeholder runtime dependency is used before being wired."""

    def __init__(self, detail: str = "Requested runtime scaffold is not wired yet.") -> None:
        super().__init__(
            detail,
            status_code=501,
            title="Runtime scaffold not ready",
            type_uri="https://ragdoll.dev/problems/runtime-scaffold-not-ready",
            code="runtime_scaffold_not_ready",
        )


class AuthenticationRequiredError(ApplicationError):
    """Raised when a request requires authentication."""

    def __init__(self, detail: str = "Authentication is required.") -> None:
        super().__init__(
            detail,
            status_code=401,
            title="Authentication required",
            type_uri="https://ragdoll.dev/problems/authentication-required",
            code="authentication_required",
        )


class AuthorizationError(ApplicationError):
    """Raised when an authenticated request is forbidden."""

    def __init__(self, detail: str = "You do not have access to this resource.") -> None:
        super().__init__(
            detail,
            status_code=403,
            title="Forbidden",
            type_uri="https://ragdoll.dev/problems/forbidden",
            code="forbidden",
        )


class StorageUnavailableError(ApplicationError):
    """Raised when the document storage backend cannot complete a request."""

    def __init__(self, detail: str = "Document storage is temporarily unavailable.") -> None:
        super().__init__(
            detail,
            status_code=503,
            title="Storage unavailable",
            type_uri="https://ragdoll.dev/problems/storage-unavailable",
            code="storage_unavailable",
        )


class QueueUnavailableError(ApplicationError):
    """Raised when the background queue backend cannot complete a request."""

    def __init__(self, detail: str = "Document processing queue is temporarily unavailable.") -> None:
        super().__init__(
            detail,
            status_code=503,
            title="Queue unavailable",
            type_uri="https://ragdoll.dev/problems/queue-unavailable",
            code="queue_unavailable",
        )
