# ========================================
# urls.py - CÓDIGO CORREGIDO
# ========================================

from rest_framework.routers import DefaultRouter
from django.urls import path, include, re_path
from . import views
from .views import (
    RolViewSet,
    TrabajadorViewSet,
    UsuarioViewSet,
    NoticiaViewSet,
    EstadoPublicacionViewSet,
    ImagenViewSet,
    PublicidadViewSet,
    AdminViewSet,
    UserrViewSet,
    ServicioViewSet,
    SubcategoriaServicioViewSet,
    redirect_to_home,
    CurrentUserView,
    RegisterView,
    LoginView,
    RequestPasswordResetView,
    ResetPasswordView,
    UserProfileView,
    EstadoPublicacionList,
    TrabajadorList,
    VerifyTokenView,
    NewsletterSubscriberViewSet,
    upload_image
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Crear un router y registrar todos los viewsets
router = DefaultRouter()
router.register(r'roles', RolViewSet, basename='rol')
router.register(r'users', UserrViewSet, basename='user')
router.register(r'admin', AdminViewSet, basename='admin')
router.register(r'trabajadores', TrabajadorViewSet, basename='trabajador')
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'estados', EstadoPublicacionViewSet, basename='estado')
router.register(r'imagenes', ImagenViewSet, basename='imagen')
router.register(r'publicidades', PublicidadViewSet, basename='publicidad')
router.register(r'noticias', NoticiaViewSet, basename='noticia')
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'subcategorias-servicios', SubcategoriaServicioViewSet, basename='subcategoria-servicio')
router.register(r'newsletter', NewsletterSubscriberViewSet, basename='newsletter')


urlpatterns = [
    # === REDIRECCIÓN PRINCIPAL ===
    path('', redirect_to_home, name='redirect_to_home'),
    
    # === RUTAS DEL ROUTER (ViewSets) ===
    # IMPORTANTE: Esto debe ir ANTES de las rutas manuales
    path('', include(router.urls)),
    
    # === AUTENTICACIÓN ===
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/user/', views.current_user, name='current_user'),
    path('auth/current-user/', CurrentUserView.as_view(), name='current-user'),
    
    # JWT Tokens
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # === RECUPERACIÓN DE CONTRASEÑA ===
    path('password/reset/request/', RequestPasswordResetView.as_view(), name='password-reset-request'),
    path('password/reset/verify/', VerifyTokenView.as_view(), name='password-reset-verify'),
    path('password/reset/confirm/', ResetPasswordView.as_view(), name='password-reset-confirm'),
    
    # === PERFIL DE USUARIO ===
    path('user-profile/', UserProfileView.as_view(), name='user-profile'),
    
    # === LISTAS ESPECÍFICAS ===
    path('estados-publicacion/', EstadoPublicacionList.as_view(), name='estado-publicacion-list'),
    path('trabajadores/', TrabajadorList.as_view(), name='trabajador-list'),
    
    # === UPLOAD DE IMÁGENES ===
    path('upload/', upload_image, name='upload_image'),
    
    # === NOTICIAS - DETALLE ===
    # NOTA: Estas rutas específicas deben ir DESPUÉS del router
    re_path(
        r'^noticias/(?P<pk>\d+)-(?P<slug>[\w-]+)/$',
        NoticiaViewSet.as_view({'get': 'retrieve'}),
        name='noticia-detail'
    ),
    path(
        'noticias/<int:pk>/',
        NoticiaViewSet.as_view({'get': 'retrieve'}),
        name='noticia-detail-id-only'
    ),
    
    # === SERVICIOS - DETALLE ===
    re_path(
        r'^servicios/(?P<pk>\d+)-(?P<slug>[\w-]+)/$',
        ServicioViewSet.as_view({'get': 'retrieve'}),
        name='servicio-detail'
    ),
    path(
        'servicios/<int:pk>/',
        ServicioViewSet.as_view({'get': 'retrieve'}),
        name='servicio-detail-id-only'
    ),
    
    # === NEWSLETTER CONFIRMACIÓN ===
    path('newsletter/confirmar/<str:token>/', 
         NewsletterSubscriberViewSet.as_view({'get': 'confirmar'}), 
         name='newsletter-confirmar'),
]

# ========================================
# NOTAS IMPORTANTES:
# ========================================
# 
# El router automáticamente crea estas URLs:
# 
# SERVICIOS:
# - GET /servicios/ -> list (todos los servicios activos)
# - POST /servicios/ -> create
# - GET /servicios/{id}/ -> retrieve
# - PUT /servicios/{id}/ -> update
# - PATCH /servicios/{id}/ -> partial_update
# - DELETE /servicios/{id}/ -> destroy
# - GET /servicios/activos/ -> @action activos
# - GET /servicios/consultoria-estrategica/ -> @action consultoria_estrategica
# - GET /servicios/capacitaciones-especializadas/ -> @action capacitaciones_especializadas
# - POST /servicios/{id}/toggle-activo/ -> @action toggle_activo
#
# NOTICIAS:
# - GET /noticias/ -> list
# - GET /noticias/recientes/ -> @action (si lo tienes definido)
# - GET /noticias/destacadas/ -> @action (si lo tienes definido)
#
# ========================================