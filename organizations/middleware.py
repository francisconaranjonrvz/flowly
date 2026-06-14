# Middleware que resuelve la organización activa de cada petición.

from django.utils import timezone

from .models import OrganizationMembership

SESSION_KEY = 'active_org_id'
PING_KEY = 'last_seen_ping'
PING_THROTTLE_SECS = 30


class OrganizationMiddleware:
    """Fija ``request.organization`` y ``request.user_organizations``.

    Debe ir DESPUÉS de AuthenticationMiddleware. Hace UNA sola consulta de
    membresías (con el tema precargado) que reutiliza el context processor,
    evitando consultas duplicadas por petición. Para usuarios anónimos o sin
    membresías deja ``request.organization = None``.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._attach(request)
        return self.get_response(request)

    def _heartbeat(self, request, user):
        """Actualiza last_seen como mucho cada PING_THROTTLE_SECS (1 UPDATE,
        sin señales) para alimentar la presencia sin coste por petición."""
        now = timezone.now()
        last = request.session.get(PING_KEY, 0)
        if now.timestamp() - last >= PING_THROTTLE_SECS:
            user.__class__.objects.filter(pk=user.pk).update(last_seen=now)
            request.session[PING_KEY] = now.timestamp()

    def _attach(self, request):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            request.organization = None
            request.user_organizations = []
            return

        self._heartbeat(request, user)

        memberships = list(
            OrganizationMembership.objects
            .filter(user=user)
            .select_related('organization', 'organization__theme')
        )
        orgs = [m.organization for m in memberships]
        request.user_organizations = orgs

        if not orgs:
            request.organization = None
            return

        orgs_by_id = {org.id: org for org in orgs}
        active_id = request.session.get(SESSION_KEY)
        if active_id in orgs_by_id:
            request.organization = orgs_by_id[active_id]
            return

        # Por defecto: la organización personal, o la primera por nombre.
        default = sorted(orgs, key=lambda o: (not o.is_personal, o.name.lower()))[0]
        request.session[SESSION_KEY] = default.id
        request.organization = default
