from django.contrib import admin
from django.utils.html import format_html

from .models import Card, Comment, Subtask


PRIORITY_DOTS = {
    0: ('#444444', 'Sin prioridad'),
    1: ('#34d399', 'Baja'),
    2: ('#fbbf24', 'Media'),
    3: ('#f97316', 'Alta'),
    4: ('#ef4444', 'Urgente'),
}


class SubtaskInline(admin.TabularInline):
    model = Subtask
    extra = 0


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('title', 'column', 'priority_badge', 'due_date', 'assignee', 'order')
    list_filter = ('priority', 'column__board', 'labels')
    list_editable = ('order',)
    search_fields = ('title', 'description', 'column__board__name')
    autocomplete_fields = ['column', 'assignee', 'assignees', 'labels']
    ordering = ('column', 'order')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [SubtaskInline, CommentInline]

    @admin.display(description='Prioridad', ordering='priority')
    def priority_badge(self, obj):
        color, label = PRIORITY_DOTS.get(obj.priority, ('#888', '?'))
        return format_html(
            '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            'background:{};margin-right:6px;"></span>{}',
            color, label,
        )


@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'card', 'is_done', 'order')
    list_filter = ('is_done',)
    list_editable = ('is_done', 'order')
    search_fields = ('title', 'card__title')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('card', 'author', 'created_at')
    search_fields = ('body', 'card__title', 'author__username')
    readonly_fields = ('created_at',)
