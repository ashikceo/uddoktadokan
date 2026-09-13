from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def qs(context, **overrides):
    """Render a query string based on request.GET with the given overrides.

    Usage: ?{% qs page=2 sort='price' %}   (values are URL-quoted)
    Pass a key with value None (i.e. {# x=None #}) to remove it: {% qs page=None %}
    """
    request = context.get('request')
    if not request:
        return ''
    params = request.GET.copy()
    for key, value in overrides.items():
        if value is None or value == '':
            params.pop(key, None)
        else:
            params[key] = str(value)
    for skip in ('ajax',):
        params.pop(skip, None)
    return params.urlencode()