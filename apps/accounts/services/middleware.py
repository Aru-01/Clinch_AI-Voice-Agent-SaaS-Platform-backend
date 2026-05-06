from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError

class JWTCookieMiddleware(MiddlewareMixin):
    def process_request(self, request):
        access_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])

        # If access token is missing but refresh token exists, try to refresh
        if not access_token and refresh_token:
            try:
                refresh = RefreshToken(refresh_token)
                new_access_token = str(refresh.access_token)
                
                # We can't set the cookie in the response yet, 
                # but we can attach it to the request so the authentication class can see it
                request.COOKIES[settings.SIMPLE_JWT['AUTH_COOKIE']] = new_access_token
                request._new_access_token = new_access_token
            except TokenError:
                pass

    def process_response(self, request, response):
        # If we generated a new access token in process_request, set it in the response cookie
        if hasattr(request, '_new_access_token'):
            response.set_cookie(
                key=settings.SIMPLE_JWT['AUTH_COOKIE'],
                value=request._new_access_token,
                expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
                path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
            )
        return response
