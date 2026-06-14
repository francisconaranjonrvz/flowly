# Vistas de organización (cambio de organización activa).

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .middleware import SESSION_KEY
from .models import OrganizationMembership


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
