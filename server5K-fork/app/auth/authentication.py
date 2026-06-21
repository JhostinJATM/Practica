"""
Backend de autenticación personalizado para Jueces y Edge.
Los jueces NO son usuarios de Django, tienen su propio modelo.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from app.models import Juez, Competencia


class JuezJWTAuthentication(JWTAuthentication):
    """
    Autenticación JWT personalizada para el modelo Juez.
    """

    def get_user(self, validated_token):
        """
        Obtiene el juez desde el token JWT validado.
        """
        try:
            juez_id = validated_token.get('juez_id')
            if juez_id is None:
                raise InvalidToken('Token no contiene juez_id')

            juez = Juez.objects.get(id=juez_id, is_active=True)
            return juez
        except Juez.DoesNotExist:
            raise InvalidToken('Juez no encontrado o inactivo')


class EdgeTokenAuth(BaseAuthentication):
    """
    Autenticación por token de competencia para dispositivos Edge y Simulador.
    Valida el header: Authorization: Token <uuid>
    """

    keyword = 'Token'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith(f'{self.keyword} '):
            return None

        token_str = auth_header[len(self.keyword) + 1:].strip()

        if not token_str:
            raise AuthenticationFailed('Token de autorizacion requerido')

        try:
            competencia = Competencia.objects.get(token=token_str)
        except Competencia.DoesNotExist:
            raise AuthenticationFailed('Token invalido o competencia no activa')

        if not competencia.is_active:
            raise AuthenticationFailed('Token invalido o competencia no activa')

        return (competencia, competencia.token)

    def authenticate_header(self, request):
        return f'{self.keyword}'
