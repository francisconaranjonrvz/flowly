# Vistas de colaboración: presencia (ping), notificaciones y chat.

import re

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from boards.models import Board
from boards.permissions import user_can_access_board

from .models import Channel, Message, notify

NOTIF_DROPDOWN_LIMIT = 8
CHAT_RECENT = 50
_MENTION_RE = re.compile(r'@(\w+)')


@login_required
def presence_ping(request):
    """Mantiene viva la presencia sin necesidad de navegar. El middleware ya
    actualiza last_seen (throttled); este endpoint solo provoca la petición."""
    return HttpResponse(status=204)


# ---- Notificaciones (acotadas a la organización activa) ----

def _org_notifications(request):
    """Notificaciones del usuario en la organización activa. Aislamiento
    multi-tenant: nunca se mezclan notificaciones de otras organizaciones."""
    org = request.organization
    if org is None:
        return request.user.notifications.none()
    return request.user.notifications.filter(organization=org)


@login_required
def notifications_badge(request):
    """Solo el badge de la campana (HTMX poll)."""
    count = _org_notifications(request).filter(unread=True).count()
    return render(request, 'partials/_notif_badge.html', {'unread_count': count})


@login_required
def notifications_dropdown(request):
    """Lista corta de notificaciones recientes para el desplegable de la campana."""
    notifs = _org_notifications(request).select_related('actor')[:NOTIF_DROPDOWN_LIMIT]
    return render(request, 'partials/_notif_dropdown.html', {'notifications': notifs})


@login_required
def notifications_view(request):
    """Bandeja completa. Al abrirla se marcan todas como leídas."""
    notifs = list(_org_notifications(request).select_related('actor')[:100])
    _org_notifications(request).filter(unread=True).update(unread=False)
    return render(request, 'notificaciones.html', {'notifications': notifs})


@login_required
def notification_open(request, pk):
    """Marca la notificación como leída y redirige a su destino. Solo abre
    notificaciones de la organización activa (no se salta de tenant)."""
    n = get_object_or_404(_org_notifications(request), pk=pk)
    if n.unread:
        n.unread = False
        n.save(update_fields=['unread'])
    return redirect(n.url or 'home')


# ---- Chat de proyecto ----

def _recent_messages(board):
    qs = board.messages.select_related('author').order_by('-created')[:CHAT_RECENT]
    return list(reversed(qs))


@login_required
def chat_messages(request, board_id):
    """Lista de mensajes del tablero (HTMX poll)."""
    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return HttpResponseForbidden()
    return render(request, 'partials/_chat_messages.html', {
        'chat_messages': _recent_messages(board),
    })


@login_required
@require_POST
def chat_send(request, board_id):
    """Envía un mensaje al chat del tablero y notifica @menciones."""
    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return HttpResponseForbidden()
    body = (request.POST.get('body') or '').strip()
    if body:
        Message.objects.create(board=board, author=request.user, body=body)
        _notify_chat_mentions(request.user, board, body)
    return render(request, 'partials/_chat_messages.html', {
        'chat_messages': _recent_messages(board),
    })


# ---- Chat por canales (organización) ----

def _ensure_general(org):
    ch, _ = Channel.objects.get_or_create(
        organization=org, is_general=True,
        defaults={'name': 'general', 'slug': 'general'},
    )
    return ch


def _recent_channel_messages(channel):
    qs = channel.messages.select_related('author').order_by('-created')[:CHAT_RECENT]
    return list(reversed(qs))


@login_required
def chat_view(request, channel_id=None):
    """Página de Chat: lista de canales de la org + conversación del activo."""
    org = request.organization
    if org is None:
        return render(request, 'chat.html', {'channels': [], 'channel': None, 'chat_messages': []})
    _ensure_general(org)
    channels = list(org.channels.all())
    if channel_id:
        channel = get_object_or_404(Channel, pk=channel_id, organization=org)
    else:
        channel = next((c for c in channels if c.is_general), channels[0])
    return render(request, 'chat.html', {
        'channels': channels,
        'channel': channel,
        'chat_messages': _recent_channel_messages(channel),
    })


@login_required
def channel_messages(request, channel_id):
    """Mensajes de un canal (HTMX poll)."""
    channel = get_object_or_404(Channel, pk=channel_id, organization=request.organization)
    return render(request, 'partials/_chat_messages.html', {
        'chat_messages': _recent_channel_messages(channel),
    })


@login_required
@require_POST
def channel_send(request, channel_id):
    """Envía un mensaje a un canal y notifica @menciones a la org."""
    channel = get_object_or_404(Channel, pk=channel_id, organization=request.organization)
    body = (request.POST.get('body') or '').strip()
    if body:
        Message.objects.create(channel=channel, author=request.user, body=body)
        _notify_channel_mentions(request.user, channel)
    return render(request, 'partials/_chat_messages.html', {
        'chat_messages': _recent_channel_messages(channel),
    })


@login_required
@require_POST
def channel_create(request):
    """Crea un canal en la organización activa."""
    org = request.organization
    if org is None:
        raise Http404
    name = (request.POST.get('name') or '').strip()[:50]
    if name:
        slug = slugify(name)[:60] or 'canal'
        channel, _ = Channel.objects.get_or_create(
            organization=org, slug=slug,
            defaults={'name': name, 'created_by': request.user},
        )
        return redirect('chat-channel', channel_id=channel.id)
    return redirect('chat')


def _notify_channel_mentions(actor, channel):
    """@menciones en un canal → notifica a los miembros de la organización."""
    last = channel.messages.order_by('-created').first()
    if last is None:
        return
    names = {n.lower() for n in _MENTION_RE.findall(last.body)}
    if not names:
        return
    members = {
        m.user.username.lower(): m.user
        for m in channel.organization.memberships.select_related('user')
    }
    url = reverse('chat-channel', kwargs={'channel_id': channel.id})
    verb = f'{actor.get_full_name_or_username()} te mencionó en #{channel.name}'
    for name in names:
        u = members.get(name)
        if u is not None:
            notify(u, verb=verb, actor=actor, url=url, organization=channel.organization)


def _notify_chat_mentions(actor, board, body):
    """Notifica a los miembros del tablero mencionados con @usuario en el chat."""
    names = {n.lower() for n in _MENTION_RE.findall(body)}
    if not names:
        return
    from tasks.views import _board_members
    members = {m.username.lower(): m for m in _board_members(board)}
    url = reverse('board-detail', kwargs={'board_id': board.id})
    verb = f'{actor.get_full_name_or_username()} te mencionó en el chat de «{board.name}»'
    for name in names:
        m = members.get(name)
        if m is not None:
            notify(m, verb=verb, actor=actor, url=url, board=board)
