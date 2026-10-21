# Vistas de autenticación y perfil.

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from boards.demo import DEMO_MAX_AGE, cleanup_expired_demos, create_demo_sandbox
from organizations.middleware import SESSION_KEY as ACTIVE_ORG_SESSION_KEY
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


# Cookie firmada que recuerda el sandbox demo del visitante: sobrevive al
# logout, así volver a pulsar "demo" reabre su espacio en vez de crear otro.
DEMO_COOKIE = 'flowly_demo'
DEMO_COOKIE_SALT = 'flowly.demo-sandbox'


def _remembered_demo_user(request):
    """Usuario demo vivo recordado por la cookie, o None."""
    try:
        user_id = request.get_signed_cookie(
            DEMO_COOKIE, salt=DEMO_COOKIE_SALT, max_age=int(DEMO_MAX_AGE.total_seconds()),
        )
    except (KeyError, signing.BadSignature):
        return None
    return (
        get_user_model().objects
        .filter(pk=user_id, is_demo=True, is_active=True,
                date_joined__gte=timezone.now() - DEMO_MAX_AGE)
        .first()
    )


@require_http_methods(['GET', 'POST'])
def demo_login_view(request):
    """Acceso demo sin credenciales (enlace para CV/portfolio).

    GET muestra una página que se auto-envía por POST (los bots que solo
    previsualizan enlaces no crean sandboxes). POST crea, o reabre, un sandbox
    aislado del visitante, inicia sesión y le lleva al primer tablero.
    """
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'GET':
        return render(request, 'demo_start.html')

    user = _remembered_demo_user(request)
    if user is None:
        cleanup_expired_demos()
        user, organization, first_board = create_demo_sandbox()
    else:
        organization = get_or_create_personal_organization(user)
        first_board = organization.boards.order_by('id').first()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session[ACTIVE_ORG_SESSION_KEY] = organization.id

    response = redirect('board-detail', board_id=first_board.id) if first_board else redirect('home')
    response.set_signed_cookie(
        DEMO_COOKIE, user.pk, salt=DEMO_COOKIE_SALT,
        max_age=int(DEMO_MAX_AGE.total_seconds()),
        secure=settings.SESSION_COOKIE_SECURE, httponly=True, samesite='Lax',
    )
    return response


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
