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
