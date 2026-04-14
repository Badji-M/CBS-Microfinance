"""
Custom template tags for MicroFinance Platform
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get dict item by key in templates"""
    if hasattr(dictionary, 'get'):
        return dictionary.get(key, 0)
    return 0


@register.filter
def multiply(value, arg):
    """Multiply two numbers"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        if float(total) == 0:
            return 0
        return round(float(value) / float(total) * 100, 1)
    except (ValueError, TypeError):
        return 0


@register.filter
def fcfa(value):
    """Format number as FCFA"""
    try:
        return f"{float(value):,.0f} FCFA".replace(',', ' ')
    except (ValueError, TypeError):
        return "—"


@register.filter
def abs_value(value):
    """Absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.simple_tag
def progress_color(percentage):
    """Return Bootstrap color class based on percentage"""
    try:
        pct = float(percentage)
        if pct >= 90:
            return 'success'
        elif pct >= 70:
            return 'info'
        elif pct >= 50:
            return 'warning'
        else:
            return 'danger'
    except (ValueError, TypeError):
        return 'secondary'
