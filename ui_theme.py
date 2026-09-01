"""
ui_theme.py
------------
The same 7 preset color themes as the desktop app, now used two ways:

  - PDF generation (pdf_export.py, voucher_print.py) calls get_colors()
    for the current tenant's theme, same as before.
  - The web UI reads THEMES via app.py's template context to render
    CSS custom properties, so the whole page (not just PDFs) matches
    the tenant's chosen color.
"""

THEMES = {
    "Purple": {"primary": "#6f42c1", "primary_dark": "#533291", "light": "#f0eaf9"},
    "Blue":   {"primary": "#2563eb", "primary_dark": "#1e40af", "light": "#eff6ff"},
    "Green":  {"primary": "#16a34a", "primary_dark": "#15803d", "light": "#f0fdf4"},
    "Red":    {"primary": "#dc2626", "primary_dark": "#991b1b", "light": "#fef2f2"},
    "Grey":   {"primary": "#4b5563", "primary_dark": "#1f2937", "light": "#f3f4f6"},
    "Orange": {"primary": "#ea580c", "primary_dark": "#9a3412", "light": "#fff7ed"},
    "Navy":   {"primary": "#1e3a5f", "primary_dark": "#0f2440", "light": "#eef2f7"},
    "Black":  {"primary": "#111827", "primary_dark": "#000000", "light": "#f4f4f5"},
}

DEFAULT_THEME = "Purple"


def get_colors(theme_name=None):
    if theme_name is None:
        import settings
        theme_name = settings.get_theme()
    return THEMES.get(theme_name, THEMES[DEFAULT_THEME])
