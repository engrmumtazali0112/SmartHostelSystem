from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Filter to access dictionary items by key in Django templates
    Usage: {{ my_dict|get_item:my_key }}
    """
    if dictionary is None:
        return None
    
    return dictionary.get(key)