class ApplicationError(Exception):
    """Base for errors the API layer translates into HTTP responses."""


class NotFoundError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class ValidationError(ApplicationError):
    pass


class InvalidCredentialsError(ApplicationError):
    pass


class InvalidTokenError(ApplicationError):
    pass


class ServiceUnavailableError(ApplicationError):
    pass
