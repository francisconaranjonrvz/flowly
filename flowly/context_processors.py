# Context processors del proyecto.

from django.utils.safestring import mark_safe

# Stacks de fuente permitidos (el template nunca confía en una cadena cruda).
_FONT_STACKS = {
    'spacegrotesk': "'Space Grotesk', 'Inter', sans-serif",
    'mulish': "'Mulish', 'Inter', sans-serif",
    'inter': "'Inter', -apple-system, sans-serif",
    'ibmplexsans': "'IBM Plex Sans', 'Inter', sans-serif",
    'ppgoshasans': "'PPGoshaSans', 'Space Grotesk', sans-serif",
}

# (campo del modelo -> variable CSS) para los primitivos de color.
_COLOR_PRIMITIVES = [
    ('brand_accent', '--brand-accent'),
    ('brand_accent_hover', '--brand-accent-hover'),
    ('brand_bg_primary', '--brand-bg-primary'),
    ('brand_bg_secondary', '--brand-bg-secondary'),
    ('brand_bg_tertiary', '--brand-bg-tertiary'),
    ('brand_bg_hover', '--brand-bg-hover'),
    ('brand_bg_active', '--brand-bg-active'),
    ('brand_bg_elevated', '--brand-bg-elevated'),
    ('brand_text_primary', '--brand-text-primary'),
    ('brand_text_secondary', '--brand-text-secondary'),
    ('brand_text_tertiary', '--brand-text-tertiary'),
    ('brand_overlay', '--brand-overlay'),
    ('brand_success', '--brand-success'),
    ('brand_warning', '--brand-warning'),
]

# Sombras suaves para tema claro (sustituyen las fuertes del oscuro).
_LIGHT_SHADOWS = '--shadow-alpha-sm:0.06;--shadow-alpha-md:0.10;--shadow-alpha-lg:0.16;'

# Sección de navegación activa según la URL resuelta (para resaltar la sidebar).
_SECTION_BY_URL = {
    'home': 'tableros',
    'board-detail': 'tableros',
    'board-create': 'tableros',
    'board-update': 'tableros',
    'board-delete': 'tableros',
    'mis-tareas': 'mis-tareas',
    'calendario': 'calendario',
    'equipo': 'equipo',
    'equipo-member': 'equipo',
    'chat': 'chat',
    'chat-channel': 'chat',
    'office': 'office',
    'perfil': 'perfil',
}


def _active_section(request):
    match = getattr(request, 'resolver_match', None)
    if match is None:
        return ''
    return _SECTION_BY_URL.get(match.url_name or '', '')


def _unread_count(user, org):
    """Nº de notificaciones sin leer en la organización activa (badge de la
    campana). Aislamiento multi-tenant: solo cuenta las de esa organización."""
    if org is None:
        return 0
    from collab.models import Notification
    return Notification.objects.filter(recipient=user, organization=org, unread=True).count()


def _hex_to_channels(value):
    """'#d6ff00' -> ('214 255 0', (214, 255, 0)), o None si el hex es inválido.

    Defensa en profundidad: un valor corrupto en BD no debe tumbar las páginas
    (este processor corre en cada render).
    """
    try:
        raw = value.lstrip('#')
        r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except (ValueError, IndexError, AttributeError):
        return None
    return f'{r} {g} {b}', (r, g, b)


def _relative_luminance(rgb):
    """Luminancia relativa WCAG de un (r, g, b) 0-255."""
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _resolve_on_accent(mode, accent_rgb):
    """Canales del color de texto sobre el acento, o None."""
    if mode == 'light':
        return '255 255 255'
    if mode == 'dark':
        return '17 24 39'
    if mode == 'auto' and accent_rgb is not None:
        # Acentos claros (lime) -> texto oscuro; oscuros (indigo) -> blanco.
        return '17 24 39' if _relative_luminance(accent_rgb) > 0.4 else '255 255 255'
    return None


def org_theme(request):
    """Organización activa, sus hermanas y el override de tema (CSS seguro)."""
    org = getattr(request, 'organization', None)
    org_brand = org.brand if org is not None else 'flowly'

    # Preferencia de aspecto por usuario (gana sobre el default de la org).
    user = getattr(request, 'user', None)
    is_auth = user is not None and user.is_authenticated
    user_brand = getattr(user, 'theme_brand', '') if is_auth else ''
    user_mode = getattr(user, 'theme_mode', '') if is_auth else ''
    effective_brand = user_brand or org_brand or 'flowly'

    context = {
        'active_organization': org,
        'org_brand': effective_brand,
        'user_theme_brand': user_brand,
        'user_theme_mode': user_mode,
        'active_section': _active_section(request),
        # El middleware ya resolvió la lista (una sola consulta por petición).
        'user_organizations': getattr(request, 'user_organizations', None),
        'org_theme_css': '',
        'org_theme_mode': '',
        'unread_count': _unread_count(user, org) if is_auth else 0,
    }
    if context['user_organizations'] is None:
        # Fallback defensivo si el middleware no se ejecutó (p.ej. en tests).
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            from organizations.models import OrganizationMembership
            context['user_organizations'] = [
                m.organization for m in
                OrganizationMembership.objects.filter(user=user).select_related('organization')
            ]
        else:
            context['user_organizations'] = []

    if org is None:
        return context

    from organizations.models import OrganizationTheme
    try:
        theme = org.theme  # precargado por el middleware vía select_related
    except OrganizationTheme.DoesNotExist:
        return context

    lines = []
    accent_rgb = None
    for field, var in _COLOR_PRIMITIVES:
        value = getattr(theme, field, '')
        if not value:
            continue
        channels = _hex_to_channels(value)
        if channels is None:
            continue
        lines.append(f'{var}:{channels[0]};')
        if field == 'brand_accent':
            accent_rgb = channels[1]

    # Si hay acento pero no se fijó el hover, usar el acento como hover.
    if theme.brand_accent and not theme.brand_accent_hover:
        ch = _hex_to_channels(theme.brand_accent)
        if ch is not None:
            lines.append(f'--brand-accent-hover:{ch[0]};')

    on_accent = _resolve_on_accent(theme.on_accent_mode, accent_rgb)
    if on_accent is not None:
        lines.append(f'--brand-on-accent:{on_accent};')

    if theme.font_display in _FONT_STACKS:
        lines.append(f'--font-display:{_FONT_STACKS[theme.font_display]};')
    if theme.font_body in _FONT_STACKS:
        lines.append(f'--font-family:{_FONT_STACKS[theme.font_body]};')

    # Modo (color-scheme + dureza de sombras) coherente con la paleta.
    mode = theme.theme_mode
    if mode == 'light':
        lines.append('color-scheme:light;')
        lines.append(_LIGHT_SHADOWS)
    elif mode == 'dark':
        lines.append('color-scheme:dark;')

    if lines:
        context['org_theme_css'] = mark_safe(':root{' + ''.join(lines) + '}')
    context['org_theme_mode'] = mode or ''
    return context
