from django.urls import path
from app.views import competencia_list_view, competencia_detail_view, competencia_results_partial_view, equipo_detail_view
from app.views.html_views import validacion_panel_view
from app.views.auth_views import JudgeRegisterView, JudgeLoginView, JudgeLogoutView

app_name = 'ui'

urlpatterns = [
    path('', competencia_list_view, name='competencia_list'),
    path('<int:pk>/', competencia_detail_view, name='competencia_detail'),
    path('<int:pk>/partial/', competencia_results_partial_view, name='competencia_results_partial'),
    path('equipo/<int:pk>/', equipo_detail_view, name='equipo_detail'),
    path('jueces/register/', JudgeRegisterView.as_view(), name='juez_register'),
    path('jueces/login/', JudgeLoginView.as_view(), name='juez_login'),
    path('jueces/logout/', JudgeLogoutView.as_view(), name='juez_logout'),
    path('validacion/', validacion_panel_view, name='validacion_panel'),
]
