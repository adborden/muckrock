"""
Site-wide context processors
"""
from django.conf import settings

def domain(request):
    """Add the domain to the context for constructing absolute urls."""
    return {'domain': request.get_host()}

def google_analytics(request):
    """
    Retrieve and delete any google analytics session data and send it to the template
    """
    return {
            'ga': request.session.pop('ga', None),
            'donated': request.session.pop('donated', 0),
            }

def cache_timeout(request):
    """Cache timeout settings"""
    # pylint: disable=unused-argument
    return {'cache_timeout': settings.DEFAULT_CACHE_TIMEOUT}
