from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Extend the default UserAdmin to include our custom fields (bio, avatar)
    and surface useful counts (boards owned, cards assigned).
    """

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('bio', 'avatar')}),
    )
    list_display = ('username', 'email', 'boards_owned', 'cards_assigned', 'is_staff', 'date_joined')
    list_filter = BaseUserAdmin.list_filter + ('date_joined',)
    search_fields = ('username', 'email', 'first_name', 'last_name')

    @admin.display(description='Tableros')
    def boards_owned(self, obj):
        return obj.owned_boards.count()

    @admin.display(description='Tarjetas')
    def cards_assigned(self, obj):
        return obj.assigned_cards.count()
