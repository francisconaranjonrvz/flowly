# Admin de tableros, columnas, etiquetas y miembros.

from django.contrib import admin
from django.utils.html import format_html

from .models import Board, BoardMembership, Column, Label


admin.site.site_header = 'Flowly · Administración'
admin.site.site_title = 'Flowly admin'
admin.site.index_title = 'Panel de control'


class ColumnInline(admin.TabularInline):
    model = Column
    extra = 0
    ordering = ['order']
    fields = ('title', 'order')


class LabelInline(admin.TabularInline):
    model = Label
    extra = 0
    fields = ('name', 'color')


class MembershipInline(admin.TabularInline):
    model = BoardMembership
    extra = 0
    autocomplete_fields = ['user']
    fields = ('user', 'role', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'owner', 'column_count', 'card_count', 'updated_at')
    list_filter = ('organization', 'owner', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    date_hierarchy = 'updated_at'
    autocomplete_fields = ['owner', 'organization']
    inlines = [MembershipInline, ColumnInline, LabelInline]
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Columnas', ordering='columns__count')
    def column_count(self, obj):
        return obj.columns.count()

    @admin.display(description='Tarjetas')
    def card_count(self, obj):
        from tasks.models import Card
        return Card.objects.filter(column__board=obj).count()


@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display = ('title', 'board', 'order', 'card_count')
    list_filter = ('board',)
    list_editable = ('order',)
    search_fields = ('title', 'board__name')
    ordering = ('board', 'order')

    @admin.display(description='Tarjetas')
    def card_count(self, obj):
        return obj.cards.count()


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'swatch', 'color', 'board')
    list_filter = ('board',)
    search_fields = ('name', 'board__name')

    @admin.display(description='Color')
    def swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:18px;height:18px;border-radius:50%;'
            'border:1px solid #999;background:{};"></span>',
            obj.color,
        )


@admin.register(BoardMembership)
class BoardMembershipAdmin(admin.ModelAdmin):
    list_display = ('board', 'user', 'role', 'joined_at')
    list_filter = ('role',)
    search_fields = ('board__name', 'user__username')
    autocomplete_fields = ['user', 'board']
