# URLs principales del proyecto.

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from django.views.static import serve as static_serve

from boards.views import (
    board_create_view,
    board_delete_view,
    board_detail_view,
    board_update_view,
    calendario_view,
    column_create_view,
    column_delete_view,
    column_move_view,
    column_rename_view,
    equipo_member_view,
    equipo_view,
    home_view,
    mis_tareas_view,
    office_customize,
    office_room,
    office_status,
    office_view,
    search_suggest,
    search_view,
)
from tasks.views import (
    card_create_view,
    card_delete_view,
    card_edit_view,
    card_move_view,
    comment_create_view,
    comment_delete_view,
    subtask_create_view,
    subtask_delete_view,
    subtask_toggle_view,
)
from collab.views import (
    channel_create,
    channel_messages,
    channel_send,
    chat_messages,
    chat_send,
    chat_view,
    notification_open,
    notifications_badge,
    notifications_dropdown,
    notifications_view,
    presence_ping,
)
from organizations.views import org_switch_view
from users.views import appearance_update_view, perfil_view, register_view

from .health import liveness, readiness

urlpatterns = [
    path('admin/', admin.site.urls),

    # Healthchecks para Docker
    path('healthz', liveness, name='healthz'),
    path('readyz', readiness, name='readyz'),


    # Autenticación con sesiones
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),

    # Organizaciones
    path('org/switch/', org_switch_view, name='org-switch'),

    # Presencia (heartbeat)
    path('presence/ping/', presence_ping, name='presence-ping'),

    # Notificaciones
    path('notificaciones/', notifications_view, name='notificaciones'),
    path('notificaciones/badge/', notifications_badge, name='notifications-badge'),
    path('notificaciones/dropdown/', notifications_dropdown, name='notifications-dropdown'),
    path('notificaciones/<int:pk>/abrir/', notification_open, name='notification-open'),

    # Chat de proyecto
    path('board/<int:board_id>/chat/', chat_messages, name='chat-messages'),
    path('board/<int:board_id>/chat/send/', chat_send, name='chat-send'),

    # Chat por canales (organización)
    path('chat/', chat_view, name='chat'),
    path('chat/canal/crear/', channel_create, name='channel-create'),
    path('chat/<int:channel_id>/', chat_view, name='chat-channel'),
    path('chat/<int:channel_id>/mensajes/', channel_messages, name='channel-messages'),
    path('chat/<int:channel_id>/enviar/', channel_send, name='channel-send'),

    # Secciones de la app
    path('buscar/', search_view, name='buscar'),
    path('buscar/sugerencias/', search_suggest, name='search-suggest'),
    path('mis-tareas/', mis_tareas_view, name='mis-tareas'),
    path('calendario/', calendario_view, name='calendario'),
    path('office/', office_view, name='office'),
    path('office/room/', office_room, name='office-room'),
    path('office/status/', office_status, name='office-status'),
    path('office/personaje/', office_customize, name='office-customize'),
    path('equipo/', equipo_view, name='equipo'),
    path('equipo/<int:user_id>/', equipo_member_view, name='equipo-member'),
    path('perfil/', perfil_view, name='perfil'),
    path('perfil/apariencia/', appearance_update_view, name='perfil-apariencia'),

    # Home
    path('', home_view, name='home'),

    # Tableros
    path('board/create/', board_create_view, name='board-create'),
    path('board/<int:board_id>/', board_detail_view, name='board-detail'),
    path('board/<int:board_id>/edit/', board_update_view, name='board-update'),
    path('board/<int:board_id>/delete/', board_delete_view, name='board-delete'),

    # Columnas
    path('board/<int:board_id>/column/create/', column_create_view, name='column-create'),
    path('board/<int:board_id>/column/<int:column_id>/rename/', column_rename_view, name='column-rename'),
    path('board/<int:board_id>/column/<int:column_id>/delete/', column_delete_view, name='column-delete'),
    path('board/<int:board_id>/column/move/', column_move_view, name='column-move'),

    # Tarjetas
    path('board/<int:board_id>/card/create/', card_create_view, name='card-create'),
    path('board/<int:board_id>/card/<int:card_id>/edit/', card_edit_view, name='card-edit'),
    path('board/<int:board_id>/card/<int:card_id>/delete/', card_delete_view, name='card-delete'),
    path('board/<int:board_id>/card/move/', card_move_view, name='card-move'),

    # Subtareas (checklist) — HTMX
    path('board/<int:board_id>/card/<int:card_id>/subtask/create/', subtask_create_view, name='subtask-create'),
    path('board/<int:board_id>/card/<int:card_id>/subtask/<int:subtask_id>/toggle/', subtask_toggle_view, name='subtask-toggle'),
    path('board/<int:board_id>/card/<int:card_id>/subtask/<int:subtask_id>/delete/', subtask_delete_view, name='subtask-delete'),

    # Comentarios — HTMX
    path('board/<int:board_id>/card/<int:card_id>/comment/create/', comment_create_view, name='comment-create'),
    path('board/<int:board_id>/card/<int:card_id>/comment/<int:comment_id>/delete/', comment_delete_view, name='comment-delete'),
]

# Servir /media/ (subidas, p.ej. avatares) en desarrollo y despliegue local.
# django.views.static.serve funciona aunque DEBUG=False (a diferencia de
# static()); en producción SERVE_MEDIA=False (FS efímero de Railway).
if getattr(settings, 'SERVE_MEDIA', False):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
