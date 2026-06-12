# Modelos de tableros, columnas, etiquetas y miembros.

from django.conf import settings
from django.db import models


class Board(models.Model):
    """Tablero Kanban."""

    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='boards',
        null=True,
        blank=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_boards',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='BoardMembership',
        related_name='boards',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'board'
        verbose_name_plural = 'boards'

    def __str__(self):
        return self.name


class BoardMembership(models.Model):
    """Relación usuario-tablero con rol."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
        VIEWER = 'viewer', 'Viewer'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='board_memberships',
    )
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'board')
        verbose_name = 'board membership'
        verbose_name_plural = 'board memberships'

    def __str__(self):
        return f'{self.user} → {self.board} ({self.role})'


class Column(models.Model):
    """Columna de un tablero (ej: To Do, In Progress, Done)."""

    title = models.CharField(max_length=128)
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='columns',
    )
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ('board', 'order')
        verbose_name = 'column'
        verbose_name_plural = 'columns'

    def __str__(self):
        return f'{self.board.name} / {self.title}'


class Label(models.Model):
    """Etiqueta de color asociada a un tablero."""

    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=7,
        help_text='Color en hex, ej: #ef4444',
    )
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='labels',
    )

    class Meta:
        ordering = ['name']
        unique_together = ('board', 'name')
        verbose_name = 'label'
        verbose_name_plural = 'labels'

    def __str__(self):
        return f'{self.name} ({self.board.name})'
