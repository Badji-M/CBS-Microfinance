"""
Custom template filters pour le dashboard
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Récupère une valeur d'un dictionnaire par clé.
    Utilisation: {{ my_dict|get_item:"key" }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''
