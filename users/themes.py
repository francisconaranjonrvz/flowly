# Catálogo de temas visuales seleccionables por el usuario.
#
# Fuente única de verdad para la galería de Apariencia (Perfil). Añadir un
# tema nuevo = una entrada aquí + un valor en User.ThemeBrand + un bloque
# [data-brand="..."] en static/css/design-system.css. El claro/oscuro es
# ortogonal (todo tema soporta ambos), por eso no vive aquí.
#
# Los swatches reflejan los colores de cada bloque de design-system.css y
# solo se usan para pintar la miniatura de selección.

THEMES = [
    {
        'key': 'flowly',
        'label': 'Flowly',
        'brand': 'flowly',
        'description': 'Indigo sobre superficies neutras.',
        'swatch': {
            'surface': '#f7f9fb',
            'container': '#fbfcfd',
            'primary': '#6366f1',
            'accent': '#4f46e5',
        },
    },
    {
        'key': 'nsw',
        'label': 'NoSoloWebs',
        'brand': 'nsw',
        'description': 'Lima eléctrico sobre tinta oscura.',
        'swatch': {
            'surface': '#1d1d1d',
            'container': '#262626',
            'primary': '#d6ff00',
            'accent': '#d6ff00',
        },
    },
]

THEME_KEYS = {t['key'] for t in THEMES}
