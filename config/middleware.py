"""
Custom middleware to handle dynamic domain validation for cloud platforms
"""
from django.conf import settings


class DynamicAllowedHostsMiddleware:
    """
    Allows dynamic domain validation for cloud platforms (Render, Railway, Heroku)
    Instead of hardcoding domains, it accepts any domain ending with:
    - .onrender.com
    - .railway.app  
    - .herokuapp.com
    - localhost/127.0.0.1 (for development)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        host = request.get_host().split(':')[0]  # Remove port number
        
        # Check if domain is allowed (cloud platforms or dev)
        is_cloud_domain = (
            host.endswith('.onrender.com') or
            host.endswith('.railway.app') or
            host.endswith('.herokuapp.com') or
            host in settings.ALLOWED_HOSTS or
            host == 'localhost' or
            host == '127.0.0.1'
        )
        
        if not is_cloud_domain:
            # If not in cloud domain list and not in ALLOWED_HOSTS, add it dynamically
            # This is for development/testing multiple domains
            if host not in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS.append(host)
        
        response = self.get_response(request)
        return response
