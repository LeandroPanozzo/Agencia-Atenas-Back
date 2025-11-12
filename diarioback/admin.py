# ========================================
# urls.py - CÓDIGO COMPLETO
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
    ServicioViewSet,  # NUEVO
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
router.register(r'servicios', ServicioViewSet, basename='servicio')  # NUEVO

urlpatterns = [
    # === REDIRECCIÓN PRINCIPAL ===
    path('', redirect_to_home, name='redirect_to_home'),
    
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
    path('upload/', upload_image, name='upload_image'),
    path('noticias/upload-image/', NoticiaViewSet.as_view({'post': 'upload_image'}), name='noticia-upload-image'),
    path('servicios/upload-image/', ServicioViewSet.as_view({'post': 'upload_image'}), name='servicio-upload-image'),  # NUEVO
    
    # === NOTICIAS - DETALLE ===
    # URL con slug (preferida para SEO)
    re_path(
        r'^noticias/(?P<pk>\d+)-(?P<slug>[\w-]+)/$',
        NoticiaViewSet.as_view({'get': 'retrieve'}),
        name='noticia-detail'
    ),
    # URL solo con ID (compatibilidad)
    path(
        'noticias/<int:pk>/',
        NoticiaViewSet.as_view({'get': 'retrieve'}),
        name='noticia-detail-id-only'
    ),
    
    # === NOTICIAS - CATEGORÍAS Y FILTROS ===
    path('noticias/recientes/', NoticiaViewSet.as_view({'get': 'recientes'}), name='noticias-recientes'),
    path('noticias/destacadas/', NoticiaViewSet.as_view({'get': 'destacadas'}), name='noticias-destacadas'),
    
    # === SERVICIOS - DETALLE ===  # NUEVO
    # URL con slug (preferida para SEO)
    re_path(
        r'^servicios/(?P<pk>\d+)-(?P<slug>[\w-]+)/$',
        ServicioViewSet.as_view({'get': 'retrieve'}),
        name='servicio-detail'
    ),
    # URL solo con ID (compatibilidad)
    path(
        'servicios/<int:pk>/',
        ServicioViewSet.as_view({'get': 'retrieve'}),
        name='servicio-detail-id-only'
    ),
    
    # === SERVICIOS - FILTROS ===  # NUEVO
    path('servicios/activos/', ServicioViewSet.as_view({'get': 'activos'}), name='servicios-activos'),
]


# ========================================
# admin.py - CÓDIGO COMPLETO
# ========================================

from django.contrib import admin
from django.urls import reverse
from django.contrib.auth.models import User, Group, Permission
from django.utils.html import format_html
from django.contrib.contenttypes.models import ContentType
from .models import (
    Rol, 
    Trabajador, 
    Usuario, 
    Noticia, 
    EstadoPublicacion, 
    Imagen, 
    Publicidad, 
    UserProfile,
    Servicio  # NUEVO
)

# --- Función helper para verificar permisos de admin ---
def es_admin_completo(user):
    """Verifica si el usuario tiene permisos de administración completos"""
    return user.is_superuser or user.is_staff

# --- Signal para asignar permisos automáticamente a usuarios staff ---
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def asignar_permisos_staff(sender, instance, **kwargs):
    """Asigna todos los permisos a usuarios con is_staff=True"""
    if instance.is_staff and not instance.is_superuser:
        # Obtener todos los permisos disponibles
        all_permissions = Permission.objects.all()
        # Asignar todos los permisos al usuario
        instance.user_permissions.set(all_permissions)
        print(f"Permisos asignados a {instance.username}")

# --- Clase base para todos los ModelAdmin con permisos de staff ---
class StaffPermissionMixin:
    """Mixin que otorga todos los permisos a usuarios staff"""
    
    def has_module_permission(self, request):
        return es_admin_completo(request.user)
    
    def has_view_permission(self, request, obj=None):
        return es_admin_completo(request.user)
    
    def has_add_permission(self, request):
        return es_admin_completo(request.user)

    def has_change_permission(self, request, obj=None):
        return es_admin_completo(request.user)

    def has_delete_permission(self, request, obj=None):
        return es_admin_completo(request.user)

# --- Restricciones de permisos para User y Group ---
class UserAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Asignar permisos si es staff pero no superuser
        if obj.is_staff and not obj.is_superuser:
            all_permissions = Permission.objects.all()
            obj.user_permissions.set(all_permissions)

class GroupAdmin(StaffPermissionMixin, admin.ModelAdmin):
    pass

# Desregistrar los modelos por defecto y registrarlos con las restricciones
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

# --- Administración de los modelos personalizados ---

@admin.register(Rol)
class RolAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('nombre_rol', 'puede_publicar', 'puede_editar', 'puede_eliminar', 'puede_asignar_roles', 'puede_dejar_comentarios')
    search_fields = ('nombre_rol',)

from django import forms
from .models import Trabajador

class TrabajadorForm(forms.ModelForm):
    foto_perfil_temp = forms.ImageField(
        required=False, 
        label="Foto de Perfil",
        help_text="La imagen será subida automáticamente a ImgBB"
    )
    
    class Meta:
        model = Trabajador
        fields = ['nombre', 'apellido', 'rol', 'user', 'foto_perfil_temp']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and instance.foto_perfil:
            self.fields['foto_perfil_temp'].help_text += f"<br>Imagen actual: <a href='{instance.foto_perfil}' target='_blank'>{instance.foto_perfil}</a>"

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if not instance.user_profile:
            instance.user_profile = UserProfile.objects.create(
                nombre=instance.nombre,
                apellido=instance.apellido,
                es_trabajador=True
            )
        else:
            if not instance.user_profile.es_trabajador:
                instance.user_profile.es_trabajador = True
                instance.user_profile.save()

        foto_temp = self.cleaned_data.get('foto_perfil_temp')
        if foto_temp:
            instance.foto_perfil_temp = foto_temp

        if commit:
            instance.save()
            
        return instance

@admin.register(Trabajador)
class TrabajadorAdmin(StaffPermissionMixin, admin.ModelAdmin):
    form = TrabajadorForm
    
    list_display = (
        'correo', 'nombre', 'apellido', 'rol', 'user_link', 'mostrar_foto_perfil'
    )
    search_fields = ('correo', 'nombre', 'apellido', 'user__username', 'user__email')
    list_filter = ('rol',)
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'apellido', 'user', 'rol')
        }),
        ('Foto de Perfil', {
            'fields': ('foto_perfil_temp',),
            'description': 'La imagen se subirá automáticamente a ImgBB al guardar'
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user}</a>')
    
    user_link.short_description = 'Usuario'

    def mostrar_foto_perfil(self, obj):
        if obj.foto_perfil:
            return format_html('<img src="{}" style="max-height: 100px;">', obj.foto_perfil)
        elif obj.foto_perfil_local:
            return format_html('<img src="{}" style="max-height: 100px;">', obj.foto_perfil_local)
        return "No tiene foto de perfil"
    
    mostrar_foto_perfil.short_description = 'Foto de Perfil'

    def save_model(self, request, obj, form, change):
        obj.correo = obj.user.email
        super().save_model(request, obj, form, change)

@admin.register(Usuario)
class UsuarioAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('correo', 'nombre_usuario', 'esta_subscrito')
    search_fields = ('correo', 'nombre_usuario')
    list_filter = ('esta_subscrito',)

@admin.register(Noticia)
class NoticiaAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = (
        'nombre_noticia', 
        'autor_link', 
        'editores_en_jefe_links',
        'fecha_publicacion', 
        'solo_para_subscriptores', 
        'estado'
    )
    
    list_filter = (
        'autor', 
        'fecha_publicacion', 
        'solo_para_subscriptores', 
        'estado'
    )
    
    search_fields = ('nombre_noticia', 'Palabras_clave')
    date_hierarchy = 'fecha_publicacion'
    ordering = ['-fecha_publicacion']
    
    fieldsets = (
        ('Información Principal', {
            'fields': (
                'nombre_noticia', 
                'subtitulo', 
                'contenido', 
                'Palabras_clave'
            )
        }),
        ('Metadatos', {
            'fields': (
                'autor', 
                'editores_en_jefe',
                'fecha_publicacion', 
                'estado'
            )
        }),
        ('Imágenes', {
            'fields': (
                'imagen_1', 
                'imagen_2', 
                'imagen_3', 
                'imagen_4', 
                'imagen_5', 
                'imagen_6'
            )
        }),
        ('Opciones Avanzadas', {
            'fields': (
                'solo_para_subscriptores', 
                'mostrar_creditos',
                'url'
            )
        })
    )
    
    readonly_fields = ('url',)

    def editores_en_jefe_links(self, obj):
        links = []
        for editor in obj.editores_en_jefe.all():
            url = reverse('admin:auth_user_change', args=[editor.user.id])
            links.append(format_html(f'<a href="{url}">{editor}</a>'))
        
        if links:
            return format_html(', '.join(links))
        return "No asignados"
    
    editores_en_jefe_links.short_description = 'Editores en Jefe'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
    
    def autor_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.autor.user.id])
        return format_html(f'<a href="{url}">{obj.autor}</a>')

    autor_link.short_description = 'Autor'

@admin.register(EstadoPublicacion)
class EstadoPublicacionAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('nombre_estado',)
    search_fields = ('nombre_estado',)

@admin.register(Imagen)
class ImagenAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('nombre_imagen', 'noticia')
    search_fields = ('nombre_imagen',)
    list_filter = ('noticia',)

@admin.register(Publicidad)
class PublicidadAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('tipo_anuncio', 'fecha_inicio', 'fecha_fin', 'noticia', 'impresiones', 'clics')
    search_fields = ('tipo_anuncio', 'noticia__nombre_noticia')
    list_filter = ('fecha_inicio', 'fecha_fin')


# ========================================
# NUEVO: Admin para Servicios
# ========================================

@admin.register(Servicio)
class ServicioAdmin(StaffPermissionMixin, admin.ModelAdmin):
    list_display = ('titulo', 'activo', 'fecha_creacion', 'mostrar_imagen', 'ver_url')
    list_filter = ('activo', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion', 'palabras_clave')
    readonly_fields = ('slug', 'fecha_creacion', 'fecha_actualizacion', 'ver_url')
    date_hierarchy = 'fecha_creacion'
    ordering = ['-fecha_creacion']
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('titulo', 'descripcion')
        }),
        ('Imagen', {
            'fields': ('imagen',),
            'description': 'URL de la imagen en ImgBB (puede subirse desde el frontend)'
        }),
        ('Metadatos', {
            'fields': ('palabras_clave', 'activo')
        }),
        ('Información del Sistema', {
            'fields': ('slug', 'ver_url', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    def mostrar_imagen(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 150px; border-radius: 8px;">',
                obj.imagen
            )
        return "Sin imagen"
    
    mostrar_imagen.short_description = 'Vista Previa'
    
    def ver_url(self, obj):
        if obj.pk:
            url = obj.get_absolute_url()
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return "Guarde primero para generar la URL"
    
    ver_url.short_description = 'URL'