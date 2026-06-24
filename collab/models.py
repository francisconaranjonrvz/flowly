# Colaboración: notificaciones (bandeja personal) y chat de tablero.

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notificación personal. `verb` lleva el texto ya formateado y `url` el
    destino; así evitamos FKs genéricas. `board` permite agrupar/filtrar."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    # Organización a la que pertenece la notificación: clave para el aislamiento
    # multi-tenant (solo se muestran las de la organización activa).
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, null=True, blank=True,
        related_name='+',
    )
    verb = models.CharField(max_length=160)
    url = models.CharField(max_length=300, blank=True)
    board = models.ForeignKey(
        'boards.Board', on_delete=models.CASCADE, null=True, blank=True, related_name='+',
    )
    unread = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
        indexes = [models.Index(fields=['recipient', 'organization', 'unread'])]

    def __str__(self):
        return f'{self.recipient}: {self.verb}'


def notify(recipient, *, verb, actor=None, url='', board=None, organization=None):
    """Crea una notificación acotada a una organización. No notifica si el
    destinatario es el propio actor, ni si recipient es None. La organización se
    deriva del board si no se pasa explícitamente."""
    if recipient is None:
        return None
    if actor is not None and recipient.pk == actor.pk:
        return None
    if organization is None and board is not None:
        organization = board.organization
    return Notification.objects.create(
        recipient=recipient, actor=actor, verb=verb, url=url,
        board=board, organization=organization,
    )


class Channel(models.Model):
    """Canal de chat de una organización (general + los que se creen)."""

    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='channels',
    )
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60)
    is_general = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_general', 'name']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'slug'], name='uniq_channel_org_slug'),
        ]

    def __str__(self):
        return f'#{self.name}'


class Message(models.Model):
    """Mensaje de chat. Pertenece a un tablero (chat de proyecto) O a un canal
    de organización (chat general). Exactamente uno de los dos está fijado."""

    board = models.ForeignKey(
        'boards.Board', on_delete=models.CASCADE, related_name='messages', null=True, blank=True,
    )
    channel = models.ForeignKey(
        'collab.Channel', on_delete=models.CASCADE, related_name='messages', null=True, blank=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+',
    )
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return f'{self.author}: {self.body[:30]}'
