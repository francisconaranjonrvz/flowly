# Vistas de tarjetas (Card).

import json
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from boards.models import Board, Column
from boards.permissions import user_can_access_board
from collab.models import notify

from .models import Card, Comment, Subtask

User = get_user_model()

_MENTION_RE = re.compile(r'@(\w+)')


def _board_members(board):
    """Usuarios candidatos a asignar: dueño + miembros del tablero."""
    ids = {board.owner_id}
    ids.update(board.members.values_list('id', flat=True))
    return User.objects.filter(id__in=ids).order_by('username')


def _card_url(card):
    return reverse('card-edit', kwargs={'board_id': card.column.board_id, 'card_id': card.id})


def _notify_assigned(actor, card, user_ids):
    """Notifica a los recién asignados (ids), excepto al actor."""
    user_ids = {int(i) for i in user_ids}
    user_ids.discard(actor.id)
    if not user_ids:
        return
    url = _card_url(card)
    verb = f'{actor.get_full_name_or_username()} te asignó «{card.title}»'
    for u in User.objects.filter(id__in=user_ids):
        notify(u, verb=verb, actor=actor, url=url, board=card.column.board)


def _notify_comment(actor, card, body, members):
    """Notifica el comentario: a los mencionados (@usuario) y a los asignados."""
    url = _card_url(card)
    names = {n.lower() for n in _MENTION_RE.findall(body)}
    by_username = {m.username.lower(): m for m in members}
    mentioned = {by_username[n] for n in names if n in by_username}
    assignees = set(card.assignees.all())
    for u in mentioned:
        notify(u, verb=f'{actor.get_full_name_or_username()} te mencionó en «{card.title}»',
               actor=actor, url=url, board=card.column.board)
    for u in assignees - mentioned:
        notify(u, verb=f'{actor.get_full_name_or_username()} comentó en «{card.title}»',
               actor=actor, url=url, board=card.column.board)


def _get_card_or_403(request, board_id, card_id):
    """Devuelve (card, board) si el usuario tiene acceso, o lanza 403."""
    card = get_object_or_404(
        Card.objects.select_related('column__board'),
        pk=card_id, column__board_id=board_id,
    )
    board = card.column.board
    if not user_can_access_board(request.user, board):
        return None, None
    return card, board


@login_required
@require_POST
def card_create_view(request, board_id):
    """Crear tarjeta en una columna."""
    column_id = request.POST.get('column')
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    if not user_can_access_board(request.user, column.board):
        return HttpResponseForbidden()

    title = request.POST.get('title', '').strip()
    if not title:
        return redirect('board-detail', board_id=board_id)

    last = column.cards.order_by('-order').first()
    order = (last.order + 1) if last else 0

    due = request.POST.get('due_date', '').strip() or None

    card = Card.objects.create(
        column=column,
        title=title,
        description=request.POST.get('description', '').strip(),
        priority=int(request.POST.get('priority', 0) or 0),
        due_date=due,
        order=order,
    )

    # Etiquetas (acotadas al tablero) y asignados (acotados a sus miembros).
    label_ids = request.POST.getlist('labels')
    if label_ids:
        valid_labels = column.board.labels.filter(id__in=label_ids)
        card.labels.set(valid_labels)

    assignee_ids = request.POST.getlist('assignees')
    if assignee_ids:
        member_ids = set(_board_members(column.board).values_list('id', flat=True))
        valid_assignees = [int(i) for i in assignee_ids if int(i) in member_ids]
        if valid_assignees:
            card.assignees.set(valid_assignees)
            card.assignee = card.assignees.first()
            card.save(update_fields=['assignee'])
            _notify_assigned(request.user, card, valid_assignees)

    return redirect('board-detail', board_id=board_id)


@login_required
def card_edit_view(request, board_id, card_id):
    """Página de edición de una tarjeta."""
    card = get_object_or_404(Card, pk=card_id, column__board_id=board_id)
    board = card.column.board
    if not user_can_access_board(request.user, board):
        return HttpResponseForbidden()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            title = card.title

        card.title = title
        card.description = request.POST.get('description', '').strip()
        card.priority = int(request.POST.get('priority', 0) or 0)
        card.due_date = request.POST.get('due_date', '').strip() or None

        new_col_id = request.POST.get('column')
        if new_col_id:
            new_col = get_object_or_404(Column, pk=new_col_id, board=board)
            card.column = new_col

        card.save()

        label_ids = request.POST.getlist('labels')
        card.labels.set(label_ids)

        assignee_ids = request.POST.getlist('assignees')
        member_ids = set(_board_members(board).values_list('id', flat=True))
        valid_assignees = [int(i) for i in assignee_ids if int(i) in member_ids]
        before = set(card.assignees.values_list('id', flat=True))
        card.assignees.set(valid_assignees)
        # Mantener el FK assignee sincronizado con el primer asignado (compat).
        card.assignee = card.assignees.first()
        card.save(update_fields=['assignee'])
        # Notificar solo a los recién añadidos.
        _notify_assigned(request.user, card, set(valid_assignees) - before)

        # Al guardar, volver al tablero (no quedarse en la edición).
        return redirect('board-detail', board_id=board_id)

    labels = board.labels.all()
    columns = board.columns.order_by('order')
    card_label_ids = set(card.labels.values_list('id', flat=True))
    members = _board_members(board)
    card_assignee_ids = set(card.assignees.values_list('id', flat=True))

    return render(request, 'card_edit.html', {
        'board': board,
        'card': card,
        'labels': labels,
        'columns': columns,
        'card_label_ids': card_label_ids,
        'members': members,
        'card_assignee_ids': card_assignee_ids,
        'subtasks': card.subtasks.all(),
        'comments': card.comments.select_related('author').all(),
    })


@login_required
@require_POST
def card_delete_view(request, board_id, card_id):
    """Eliminar una tarjeta."""
    card = get_object_or_404(Card, pk=card_id, column__board_id=board_id)
    if not user_can_access_board(request.user, card.column.board):
        return HttpResponseForbidden()
    card.delete()
    return redirect('board-detail', board_id=board_id)


@login_required
@require_POST
def card_move_view(request, board_id):
    """Mover tarjeta entre columnas (AJAX, para drag & drop)."""
    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return JsonResponse({'error': 'forbidden'}, status=403)

    data = json.loads(request.body)
    card_id = data.get('card_id')
    column_id = data.get('column_id')
    target_order = int(data.get('order', 0))

    card = get_object_or_404(Card, pk=card_id, column__board_id=board_id)
    target_column = get_object_or_404(Column, pk=column_id, board_id=board_id)

    with transaction.atomic():
        source_column = card.column
        source_order = card.order

        card.column = target_column
        card.save(update_fields=['column'])

        if source_column.id != target_column.id:
            Card.objects.filter(
                column=source_column, order__gt=source_order,
            ).update(order=F('order') - 1)

        Card.objects.filter(
            column=target_column, order__gte=target_order,
        ).exclude(pk=card.pk).update(order=F('order') + 1)

        card.order = target_order
        card.save(update_fields=['order'])

    return JsonResponse({'ok': True})


# ---- Subtareas (checklist) ----

def _render_subtasks(request, card, board):
    return render(request, 'partials/_subtasks.html', {
        'card': card,
        'board': board,
        'subtasks': card.subtasks.all(),
    })


@login_required
@require_POST
def subtask_create_view(request, board_id, card_id):
    """Añadir un elemento de checklist a la tarjeta (HTMX)."""
    card, board = _get_card_or_403(request, board_id, card_id)
    if card is None:
        return HttpResponseForbidden()
    title = request.POST.get('title', '').strip()
    if title:
        last = card.subtasks.order_by('-order').first()
        order = (last.order + 1) if last else 0
        Subtask.objects.create(card=card, title=title, order=order)
    return _render_subtasks(request, card, board)


@login_required
@require_POST
def subtask_toggle_view(request, board_id, card_id, subtask_id):
    """Marcar/desmarcar una subtarea (HTMX)."""
    card, board = _get_card_or_403(request, board_id, card_id)
    if card is None:
        return HttpResponseForbidden()
    subtask = get_object_or_404(Subtask, pk=subtask_id, card=card)
    subtask.is_done = not subtask.is_done
    subtask.save(update_fields=['is_done'])
    return _render_subtasks(request, card, board)


@login_required
@require_POST
def subtask_delete_view(request, board_id, card_id, subtask_id):
    """Eliminar una subtarea (HTMX)."""
    card, board = _get_card_or_403(request, board_id, card_id)
    if card is None:
        return HttpResponseForbidden()
    Subtask.objects.filter(pk=subtask_id, card=card).delete()
    return _render_subtasks(request, card, board)


# ---- Comentarios ----

def _render_comments(request, card, board):
    return render(request, 'partials/_comments.html', {
        'card': card,
        'board': board,
        'comments': card.comments.select_related('author').all(),
    })


@login_required
@require_POST
def comment_create_view(request, board_id, card_id):
    """Añadir un comentario a la tarjeta (HTMX)."""
    card, board = _get_card_or_403(request, board_id, card_id)
    if card is None:
        return HttpResponseForbidden()
    body = request.POST.get('body', '').strip()
    if body:
        Comment.objects.create(card=card, author=request.user, body=body)
        _notify_comment(request.user, card, body, _board_members(board))
    return _render_comments(request, card, board)


@login_required
@require_POST
def comment_delete_view(request, board_id, card_id, comment_id):
    """Eliminar un comentario propio (o si es dueño del tablero) (HTMX)."""
    card, board = _get_card_or_403(request, board_id, card_id)
    if card is None:
        return HttpResponseForbidden()
    comment = get_object_or_404(Comment, pk=comment_id, card=card)
    if comment.author_id == request.user.id or board.owner_id == request.user.id:
        comment.delete()
    return _render_comments(request, card, board)
