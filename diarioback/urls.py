# urls.py - SIN SISTEMA DE ROLES

from rest_framework.routers import DefaultRouter
from django.urls import path, include, re_path
from . import views
from .views import (
    ContactoViewSet,
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
    upload_image  # ¡Asegúrate de que está importada!
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Crear un router y registrar todos los viewsets (SIN roles)
router = DefaultRouter()
router.register(r'users', UserrViewSet, basename='user')
router.register(r'admin', AdminViewSet, basename='admin')
router.register(r'trabajadores', TrabajadorViewSet, basename='trabajador')
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'estados', EstadoPublicacionViewSet, basename='estado')
router.register(r'imagenes', ImagenViewSet, basename='imagen')
router.register(r'publicidades', PublicidadViewSet, basename='publicidad')
router.register(r'noticias', NoticiaViewSet, basename='noticia')
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'categorias-servicios', SubcategoriaServicioViewSet, basename='categoria-servicio')
router.register(r'newsletter', NewsletterSubscriberViewSet, basename='newsletter')
router.register(r'contactos', ContactoViewSet, basename='contacto')


urlpatterns = [
    # === REDIRECCIÓN PRINCIPAL ===
    path('', redirect_to_home, name='redirect_to_home'),
    
    # === NEWSLETTER - ACCIONES ESPECIALES (ANTES DEL ROUTER) ===
    path('newsletter/enviar-correo-personalizado/',
         NewsletterSubscriberViewSet.as_view({'post': 'enviar_correo_personalizado'}),
         name='newsletter-enviar-correo-personalizado'),
    
    path('newsletter/confirmar/<str:token>/', 
         NewsletterSubscriberViewSet.as_view({'get': 'confirmar'}), 
         name='newsletter-confirmar'),
    
    # === RUTAS DEL ROUTER (ViewSets) ===
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
    # ⭐ RUTA ACTUAL (usada en otros lugares)
    path('upload/', upload_image, name='upload_image'),
    
    # ⭐ RUTA ESPECÍFICA PARA TINYMCE (lo que está buscando tu frontend)
    path('noticias/upload-image/', upload_image, name='noticias-upload-image'),
    
    # === NOTICIAS - DETALLE ===
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
    
    # === SERVICIOS - CATEGORÍAS ESPECÍFICAS ===
    # Rutas directas para categorías específicas
    path('servicios/categoria/estrategias-impacto/',
         ServicioViewSet.as_view({'get': 'estrategias_impacto'}),
         name='servicios-estrategias-impacto'),
    
    path('servicios/categoria/asuntos-corporativos/',
         ServicioViewSet.as_view({'get': 'asuntos_corporativos'}),
         name='servicios-asuntos-corporativos'),
    
    path('servicios/categoria/comunicacion-estrategica/',
         ServicioViewSet.as_view({'get': 'comunicacion_estrategica'}),
         name='servicios-comunicacion-estrategica'),
    
    path('servicios/categoria/analisis-datos/',
         ServicioViewSet.as_view({'get': 'analisis_datos'}),
         name='servicios-analisis-datos'),
    
    path('servicios/categoria/informes-tecnicos/',
         ServicioViewSet.as_view({'get': 'informes_tecnicos'}),
         name='servicios-informes-tecnicos'),
    
    # === SERVICIOS - ACCIONES ESPECIALES ===
    path('servicios/categoria/todos-agrupados/',
         ServicioViewSet.as_view({'get': 'servicios_por_categoria'}),
         name='servicios-por-categoria'),
    
    path('servicios/estadisticas/resumen/',
         ServicioViewSet.as_view({'get': 'resumen_estadisticas'}),
         name='servicios-resumen-estadisticas'),
    
    path('servicios/<int:pk>/toggle-activo/',
         ServicioViewSet.as_view({'post': 'toggle_activo'}),
         name='servicio-toggle-activo'),
    
    # === CONTACTOS - ACCIONES ESPECIALES ===
    path('contactos/<int:pk>/marcar-leido/',
         ContactoViewSet.as_view({'post': 'marcar_leido'}),
         name='contacto-marcar-leido'),
    
    path('contactos/<int:pk>/marcar-respondido/',
         ContactoViewSet.as_view({'post': 'marcar_respondido'}),
         name='contacto-marcar-respondido'),
    
    path('contactos/estadisticas/',
         ContactoViewSet.as_view({'get': 'estadisticas'}),
         name='contacto-estadisticas'),
]