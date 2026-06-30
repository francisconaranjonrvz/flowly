# Vistas de organización: cambio de org activa, creación e invitaciones.

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .middleware import SESSION_KEY
from .models import Organization, OrganizationInvite, OrganizationMembership
from .services import create_team_organization, join_organization


@login_required
@require_POST
def org_switch_view(request):
    """Cambia la organización activa en la sesión (solo si el usuario es miembro)."""
    try:
        org_id = int(request.POST.get('organization', ''))
    except (TypeError, ValueError):
        return redirect('home')

    is_member = OrganizationMembership.objects.filter(
        user=request.user, organization_id=org_id,
    ).exists()
    if is_member:
        request.session[SESSION_KEY] = org_id

    return redirect('home')


@login_required
def organization_create_view(request):
    """Crea un workspace de equipo y lo deja como organización activa."""
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        brand = request.POST.get('brand') or Organization.Brand.FLOWLY
        if brand not in Organization.Brand.values:
            brand = Organization.Brand.FLOWLY
        if name:
            org = create_team_organization(request.user, name, brand)
            request.session[SESSION_KEY] = org.id
            return redirect('home')
        # Nombre vacío: re-renderiza el formulario con el aviso.
        return render(request, 'organization_form.html', {
            'error': 'Ponle un nombre al workspace.',
            'brands': Organization.Brand.choices,
        })

    return render(request, 'organization_form.html', {
        'brands': Organization.Brand.choices,
    })


@login_required
def invite_manage_view(request):
    """Panel de invitación de la organización activa (solo managers).

    Muestra (y permite regenerar) el enlace de invitación. Devuelve el partial
    para poder cargarlo/refrescarlo vía HTMX desde la página de Equipo.
    """
    org = request.organization
    if org is None:
        return redirect('home')

    membership = OrganizationMembership.objects.filter(
        user=request.user, organization=org,
    ).first()
    if membership is None or not membership.is_manager:
        return HttpResponseForbidden('Solo los gestores pueden invitar.')

    invite, _ = OrganizationInvite.objects.get_or_create(
        organization=org, defaults={'created_by': request.user},
    )

    if request.method == 'POST' and request.POST.get('action') == 'regenerate':
        invite.regenerate()

    return render(request, 'partials/_invite_panel.html', {'invite': invite})


@login_required
def invite_accept_view(request, token):
    """Confirma y une al usuario al workspace del enlace de invitación."""
    invite = get_object_or_404(OrganizationInvite, token=token)

    if request.method == 'POST':
        join_organization(request.user, invite)
        request.session[SESSION_KEY] = invite.organization_id
        return redirect('home')

    already_member = OrganizationMembership.objects.filter(
        user=request.user, organization=invite.organization,
    ).exists()
    return render(request, 'invite_accept.html', {
        'invite': invite,
        'organization': invite.organization,
        'already_member': already_member,
    })
