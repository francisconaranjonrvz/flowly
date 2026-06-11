# Validadores para la imagen de avatar del usuario.

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible

AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB

validate_avatar_extension = FileExtensionValidator(
    allowed_extensions=['png', 'jpg', 'jpeg', 'webp'],
)


@deconstructible
class MaxFileSizeValidator:
    """Rechaza ficheros que superen `max_bytes`. Deconstructible para que
    makemigrations lo serialice de forma estable (con __eq__)."""

    def __init__(self, max_bytes):
        self.max_bytes = max_bytes

    def __call__(self, file):
        if file and getattr(file, 'size', None) and file.size > self.max_bytes:
            mb = self.max_bytes / (1024 * 1024)
            raise ValidationError(f'La imagen no puede superar {mb:.0f} MB.')

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and other.max_bytes == self.max_bytes


validate_avatar_size = MaxFileSizeValidator(AVATAR_MAX_BYTES)
