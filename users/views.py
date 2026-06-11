# Vistas de autenticación y perfil.

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from organizations.services import get_or_create_personal_organization

from .forms import ProfileForm, RegisterForm
from .themes import THEMES, THEME_KEYS


def register_view(request):
    """Registro clásico con formulario y sesión."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Usuario + organización personal en una sola transacción: si la
            # provisión falla, no queda una cuenta a medias.
            with transaction.atomic():
                user = form.save()
                get_or_create_personal_organization(user)
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


@login_required
def perfil_view(request):
    """Perfil del usuario: edición de datos + resumen de actividad."""
    from boards.models import Board
    from tasks.models import Card

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado.')
            return redirect('perfil')
    else:
        form = ProfileForm(instance=request.user)

    # Resumen de actividad del usuario en la organización activa.
    boards = Board.objects.filter(Q(owner=request.user) | Q(members=request.user)).distinct()
    if request.organization is not None:
        boards = boards.filter(organization=request.organization)
    board_ids = list(boards.values_list('id', flat=True))

    assigned = Card.objects.filter(assignees=request.user, column__board_id__in=board_ids)
    stats = {
        'boards': len(board_ids),
        'assigned': assigned.count(),
        'overdue': sum(1 for c in assigned if c.is_overdue),
        'memberships': request.user.organization_memberships.count(),
    }

    return render(request, 'perfil.html', {
        'form': form,
        'stats': stats,
        'themes': THEMES,
    })


@login_required
@require_POST
def appearance_update_view(request):
    """Guarda la preferencia de tema (marca + claro/oscuro) del usuario."""
    brand = request.POST.get('theme_brand', '')
    mode = request.POST.get('theme_mode', '')
    # Validar contra los valores permitidos; vacío = heredar/automático.
    if brand not in THEME_KEYS:
        brand = ''
    if mode not in {'light', 'dark'}:
        mode = ''
    request.user.theme_brand = brand
    request.user.theme_mode = mode
    request.user.save(update_fields=['theme_brand', 'theme_mode'])
    messages.success(request, 'Apariencia actualizada.')
    return redirect('perfil')
