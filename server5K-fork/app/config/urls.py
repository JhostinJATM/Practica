from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from app.views import (
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    CompetenciaViewSet,
    EquipoViewSet,
    EstadoCompetenciaAdminView,
    RegistrarTiemposView,
    EstadoEquipoRegistrosView,
)
from app.views.registro_views import EdgeRegistroView, ValidacionPendientesView, ConfirmarRegistroView, CorregirDorsalView, DescalificarParticipanteView, AuditoriaListView, EstadoRegistroView


def health_check(request):
    """Endpoint de health check para Docker/Kubernetes."""
    return JsonResponse({"status": "ok"})


# Router de DRF para ViewSets
router = DefaultRouter()
router.register(r'competencias', CompetenciaViewSet, basename='competencia')
router.register(r'equipos', EquipoViewSet, basename='equipo')

urlpatterns = [
    # Health check (para Docker)
    path('health/', health_check, name='health_check'),
    
    # Autenticación
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    
    # Endpoint público para admin (sin autenticación)
    path('admin/estado-competencias/', EstadoCompetenciaAdminView.as_view(), name='admin_estado_competencias'),
    
    # Endpoints de registros de tiempo (HTTP)
    path('equipos/<int:equipo_id>/registros/', RegistrarTiemposView.as_view(), name='registrar_tiempos'),
    path('equipos/<int:equipo_id>/registros/estado/', EstadoEquipoRegistrosView.as_view(), name='estado_registros'),
    path('registros/', EdgeRegistroView.as_view(), name='edge_registro'),
    path('validacion/pendientes/', ValidacionPendientesView.as_view(), name='validacion_pendientes'),
    path('validacion/<uuid:record_id>/confirmar/', ConfirmarRegistroView.as_view(), name='validacion_confirmar'),
    path('validacion/<uuid:record_id>/corregir/', CorregirDorsalView.as_view(), name='validacion_corregir'),
    path('validacion/<uuid:record_id>/descalificar/', DescalificarParticipanteView.as_view(), name='validacion_descalificar'),
    path('registros/<uuid:record_id>/estado/', EstadoRegistroView.as_view(), name='registro_estado'),
    path('auditoria/', AuditoriaListView.as_view(), name='auditoria_list'),
    
    # Incluir rutas del router (Competencias y Equipos)
    path('', include(router.urls)),
]
