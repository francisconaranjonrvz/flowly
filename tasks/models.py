# Modelo de tarjeta (Card).

from django.conf import settings
from django.db import models


class Card(models.Model):
    """Tarjeta de tarea dentro de una columna Kanban."""

    class Priority(models.IntegerChoices):
        NONE = 0, 'None'
        LOW = 1, 'Low'
        MEDIUM = 2, 'Medium'
        HIGH = 3, 'High'
        URGENT = 4, 'Urgent'

    title = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    column = models.ForeignKey(
        'boards.Column',
        on_delete=models.CASCADE,
        related_name='cards',
    )
    order = models.PositiveIntegerField()
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.NONE,
    )
    due_date = models.DateField(null=True, blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cards',
        help_text='Asignado principal (compatibilidad). Ver tambien assignees.',
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='cards',
    )
    labels = models.ManyToManyField(
        'boards.Label',
        blank=True,
        related_name='cards',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'card'
        verbose_name_plural = 'cards'

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        """Devuelve True si la fecha límite ya pasó."""
        if not self.due_date:
            return False
        from django.utils import timezone
        return self.due_date < timezone.now().date()

    @property
    def board(self):
        """Atajo para acceder al tablero a través de la columna."""
        return self.column.board

    @property
    def subtask_total(self):
        """Numero total de subtareas."""
        return self.subtasks.count()

    @property
    def subtask_done(self):
        """Numero de subtareas completadas."""
        return self.subtasks.filter(is_done=True).count()

    @property
    def progress(self):
        """Porcentaje de subtareas completadas (0-100)."""
        total = self.subtask_total
        if not total:
            return 0
        return round(self.subtask_done * 100 / total)


class Subtask(models.Model):
    """Elemento de checklist dentro de una tarjeta."""

    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='subtasks',
    )
    title = models.CharField(max_length=256)
    is_done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'subtask'
        verbose_name_plural = 'subtasks'

    def __str__(self):
        return self.title


class Comment(models.Model):
    """Comentario en una tarjeta."""

    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comments',
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'comment'
        verbose_name_plural = 'comments'

    def __str__(self):
        return f'{self.author}: {self.body[:40]}'
