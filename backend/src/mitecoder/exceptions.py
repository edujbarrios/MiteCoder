"""Project-specific exceptions."""


class MiteCoderError(Exception):
    """Base error shown to CLI users."""


class ConfigurationError(MiteCoderError):
    """Configuration is invalid."""


class WorkspaceSecurityError(MiteCoderError):
    """A path would escape the selected workspace."""


class ProtocolError(MiteCoderError):
    """Model output does not satisfy the action protocol."""


class ModelVerificationError(MiteCoderError):
    """A local model failed verification."""
