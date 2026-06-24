from django.contrib import admin

from .models import Message, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'verb', 'unread', 'created')
    list_filter = ('unread',)
    search_fields = ('recipient__username', 'verb')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('board', 'author', 'created')
    search_fields = ('body',)
