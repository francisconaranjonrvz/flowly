# Admin de organizaciones, membresías y temas.

from django.contrib import admin

from .models import (
    Organization,
    OrganizationInvite,
    OrganizationMembership,
    OrganizationTheme,
)


class OrganizationThemeInline(admin.StackedInline):
    model = OrganizationTheme
    extra = 0
    can_delete = True


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 0
    autocomplete_fields = ['user']
    fields = ('user', 'role', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_personal', 'member_count', 'created_at')
    list_filter = ('is_personal',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [OrganizationThemeInline, OrganizationMembershipInline]

    @admin.display(description='Miembros')
    def member_count(self, obj):
        return obj.memberships.count()


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ('organization', 'user', 'role', 'joined_at')
    list_filter = ('role',)
    search_fields = ('organization__name', 'user__username')
    autocomplete_fields = ['user', 'organization']


@admin.register(OrganizationInvite)
class OrganizationInviteAdmin(admin.ModelAdmin):
    list_display = ('organization', 'role', 'created_by', 'created_at')
    search_fields = ('organization__name',)
    autocomplete_fields = ['organization', 'created_by']
    readonly_fields = ('token', 'created_at')
