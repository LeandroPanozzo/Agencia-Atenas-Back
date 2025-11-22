# views.py - CÓDIGO COMPLETO SIN SISTEMA DE ROLES

from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework import generics
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Count
from django.core.mail import send_mail

from datetime import timedelta
import os
import uuid

from .models import (
    Servicio, 
    SubcategoriaServicio, 
    Trabajador, 
    UserProfile, 
    Usuario, 
    Noticia, 
    EstadoPublicacion, 
    Imagen, 
    Publicidad, 
    upload_to_imgbb,
    NewsletterSubscriber,
    PasswordResetToken
)

from .serializers import (
    ServicioSerializer, 
    SubcategoriaServicioSerializer, 
    UserProfileSerializer, 
    UserRegistrationSerializer, 
    LoginSerializer,
    TrabajadorSerializer, 
    UsuarioSerializer, 
    NoticiaSerializer,
    EstadoPublicacionSerializer, 
    ImagenSerializer, 
    PublicidadSerializer,
    UserSerializer,
    RequestPasswordResetSerializer,
    VerifyTokenSerializer,
    ResetPasswordSerializer,
    NewsletterSubscriberSerializer
)

from .newsletter_utils import send_newsletter_notification, send_confirmation_email


User = get_user_model()
BASE_QUERYSET = User.objects.all()


# ============================================
# VIEWSETS BÁSICOS
# ============================================

class UserrViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class TrabajadorViewSet(viewsets.ModelViewSet):
    queryset = Trabajador.objects.all()
    serializer_class = TrabajadorSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer


class EstadoPublicacionViewSet(viewsets.ModelViewSet):
    queryset = EstadoPublicacion.objects.all()
    serializer_class = EstadoPublicacionSerializer


class ImagenViewSet(viewsets.ModelViewSet):
    queryset = Imagen.objects.all()
    serializer_class = ImagenSerializer


class PublicidadViewSet(viewsets.ModelViewSet):
    queryset = Publicidad.objects.all()
    serializer_class = PublicidadSerializer


# ============================================
# VIEWSET DE NOTICIAS
# ============================================

# En views.py - Reemplaza la clase NoticiaViewSet

# En views.py - Reemplaza la clase NoticiaViewSet

class NoticiaViewSet(viewsets.ModelViewSet):
    """
    ViewSet optimizado para gestionar noticias con carga ultrarrápida
    """
    # OPTIMIZACIÓN 1: select_related y prefetch_related
    queryset = Noticia.objects.select_related(
        'autor',
        'estado'
    ).prefetch_related(
        'editores_en_jefe'
    ).all()
    
    serializer_class = NoticiaSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha_publicacion']
    ordering = ['-fecha_publicacion']
    lookup_field = 'pk'
    lookup_value_regex = r'[0-9]+(?:-[a-zA-Z0-9-_]+)?'
    
    # OPTIMIZACIÓN 2: Override get_queryset para optimizar según la acción
    def get_queryset(self):
        """Optimiza el queryset según la acción"""
        queryset = Noticia.objects.select_related(
            'autor',
            'estado'
        ).prefetch_related(
            'editores_en_jefe'
        )
        
        # Para listados, cargar solo campos necesarios
        if self.action == 'list':
            # CORREGIDO: Solo campos que existen en los modelos
            queryset = queryset.only(
                'id', 'nombre_noticia', 'subtitulo', 'fecha_publicacion',
                'Palabras_clave', 'imagen_1', 'estado', 'slug', 
                'mostrar_creditos', 'solo_para_subscriptores',
                'autor',
                # Campos del autor que realmente existen
                'autor__id', 'autor__nombre', 'autor__apellido'
            )
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Override list con optimizaciones"""
        print("\n" + "="*50)
        print("LIST NOTICIAS - OPTIMIZADO")
        print("="*50)
        
        # Obtener parámetros de filtro
        estado = request.query_params.get('estado')
        autor = request.query_params.get('autor')
        
        # Usar el queryset optimizado
        queryset = self.get_queryset()
        
        # OPTIMIZACIÓN 3: Filtros eficientes
        if estado:
            queryset = queryset.filter(estado_id=estado)
        
        if autor:
            queryset = queryset.filter(autor_id=autor)
        
        # Aplicar ordenamiento
        queryset = self.filter_queryset(queryset)
        
        # OPTIMIZACIÓN 4: Limitar resultados si es necesario
        limit = request.query_params.get('limit')
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except ValueError:
                pass
        
        # CORREGIDO: No usar count() con only() que puede causar problemas
        # En su lugar, evaluar el queryset directamente
        print(f"Cargando noticias...")
        
        # Serializar con contexto optimizado
        serializer = self.get_serializer(queryset, many=True)
        
        print(f"Noticias serializadas: {len(serializer.data)}")
        print("="*50 + "\n")
        
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve optimizado para detalle"""
        # Extraer ID si viene con slug
        pk = self.kwargs.get(self.lookup_field)
        if '-' in str(pk):
            pk = pk.split('-')[0]
        
        # Cargar con todas las relaciones
        instance = Noticia.objects.select_related(
            'autor',
            'estado'
        ).prefetch_related(
            'editores_en_jefe'
        ).get(pk=pk)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create optimizado - mantener igual que antes"""
        print("=== CREATE NOTICIA ===")
        
        try:
            user = request.user
            if not user.is_authenticated:
                return Response(
                    {'error': 'Usuario no autenticado'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            try:
                trabajador = Trabajador.objects.only('id', 'nombre', 'apellido').get(user=user)
            except Trabajador.DoesNotExist:
                return Response(
                    {'error': 'No se encontró un trabajador asociado a este usuario'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            def get_value(data, key, default=None):
                value = data.get(key, default)
                if isinstance(value, list) and len(value) > 0:
                    return value[0]
                return value if value != '' else default
            
            data = {}
            data['nombre_noticia'] = get_value(request.data, 'nombre_noticia', '')
            data['subtitulo'] = get_value(request.data, 'subtitulo', '')
            data['contenido'] = get_value(request.data, 'contenido', '')
            data['Palabras_clave'] = get_value(request.data, 'Palabras_clave', '')
            data['fecha_publicacion'] = get_value(request.data, 'fecha_publicacion')
            
            estado_value = get_value(request.data, 'estado', '1')
            data['estado'] = int(estado_value) if estado_value else 1
            
            autor_value = get_value(request.data, 'autor')
            if autor_value:
                data['autor'] = int(autor_value) if autor_value else trabajador.id
            else:
                data['autor'] = trabajador.id
            
            solo_subs = get_value(request.data, 'solo_para_subscriptores', 'false')
            data['solo_para_subscriptores'] = solo_subs.lower() in ['true', '1', 'yes'] if isinstance(solo_subs, str) else bool(solo_subs)
            
            mostrar_cred = get_value(request.data, 'mostrar_creditos', 'true')
            data['mostrar_creditos'] = mostrar_cred.lower() in ['true', '1', 'yes'] if isinstance(mostrar_cred, str) else bool(mostrar_cred)
            
            if not data.get('nombre_noticia'):
                return Response(
                    {'error': 'El título es obligatorio'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not data.get('contenido'):
                return Response(
                    {'error': 'El contenido es obligatorio'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar estado
            try:
                estado_obj = EstadoPublicacion.obtener_o_crear_estado(data['estado'])
            except Exception as e:
                return Response(
                    {'error': f'Error al procesar estado: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar autor
            if not Trabajador.objects.filter(pk=data['autor']).exists():
                return Response(
                    {'error': f'Autor con ID {data["autor"]} no existe'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Manejar imagen
            imagen_file = None
            if 'imagen_1_local' in request.FILES:
                imagen_file = request.FILES['imagen_1_local']
                if isinstance(imagen_file, list) and len(imagen_file) > 0:
                    imagen_file = imagen_file[0]
                
                try:
                    imgbb_url = upload_to_imgbb(imagen_file)
                    if imgbb_url:
                        data['imagen_1'] = imgbb_url
                except Exception as img_error:
                    print(f"Error al subir imagen: {str(img_error)}")
            
            serializer = self.get_serializer(data=data)
            
            if not serializer.is_valid():
                return Response(
                    {'error': 'Datos inválidos', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                noticia = serializer.save()
                print(f"✅ Noticia creada: ID {noticia.id}")
            except Exception as save_error:
                return Response(
                    {'error': f'Error al guardar: {str(save_error)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Si se publicó, enviar newsletter
            if data['estado'] == 3:
                subscribers = NewsletterSubscriber.objects.filter(
                    activo=True,
                    confirmado=True
                ).only('email', 'nombre')
                
                if subscribers.exists():
                    success_count = send_newsletter_notification(noticia, subscribers)
                    print(f"Newsletter enviado: {success_count}/{subscribers.count()}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Error interno del servidor: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update optimizado"""
        instance = self.get_object()
        old_estado = instance.estado.id if instance.estado else None
        
        response = super().update(request, *args, **kwargs)
        
        instance.refresh_from_db()
        new_estado = instance.estado.id if instance.estado else None
        
        # Si cambió a Publicado
        if new_estado == 3 and old_estado != 3:
            subscribers = NewsletterSubscriber.objects.filter(
                activo=True,
                confirmado=True
            ).only('email', 'nombre')
            
            if subscribers.exists():
                success_count = send_newsletter_notification(instance, subscribers)
                response.data['newsletter_sent'] = {
                    'total_subscribers': subscribers.count(),
                    'successful_sends': success_count
                }
        
        return response

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial con el mismo comportamiento"""
        instance = self.get_object()
        old_estado = instance.estado.id if instance.estado else None
        
        response = super().partial_update(request, *args, **kwargs)
        
        instance.refresh_from_db()
        new_estado = instance.estado.id if instance.estado else None
        
        # Si cambió a estado "Publicado" (ID = 3)
        if new_estado == 3 and old_estado != 3:
            subscribers = NewsletterSubscriber.objects.filter(
                activo=True,
                confirmado=True
            )
            
            if subscribers.exists():
                success_count = send_newsletter_notification(instance, subscribers)
                print(f"Newsletter enviado: {success_count}/{subscribers.count()}")
        
        return response


# ============================================
# AUTENTICACIÓN Y REGISTRO
# ============================================

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print(f"Login attempt with data: {request.data}")
        
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'Please provide both username and password'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({'error': 'Invalid credentials'}, 
                            status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Check if user is a worker (Trabajador)
        try:
            from .models import Trabajador
            trabajador = Trabajador.objects.get(user=user)
            from .serializers import TrabajadorSerializer
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'trabajador': TrabajadorSerializer(trabajador).data
            })
        except Exception as e:
            # Regular user or error occurred
            print(f"Error fetching trabajador: {e}")
            from .serializers import UserSerializer
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if user is a worker
        try:
            trabajador = Trabajador.objects.get(user=user)
            return Response({
                'isWorker': True,
                **TrabajadorSerializer(trabajador).data
            })
        except Trabajador.DoesNotExist:
            # Regular user
            return Response({
                'isWorker': False,
                **UserSerializer(user).data
            })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    return Response({
        'id': request.user.id,
        'email': request.user.email,
        'username': request.user.username,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
    })


# ============================================
# PERFIL DE USUARIO
# ============================================

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("Usuario no autenticado.")
        
        # Primero verificamos si es un trabajador
        try:
            trabajador = Trabajador.objects.get(user=user)
            # Si es un trabajador, verificamos si tiene UserProfile
            try:
                profile = UserProfile.objects.get(user=user)
                # Sincronizamos los datos del trabajador con el perfil
                profile.nombre = trabajador.nombre
                profile.apellido = trabajador.apellido
                profile.foto_perfil = trabajador.foto_perfil
                profile.descripcion_usuario = trabajador.descripcion_usuario
                profile.es_trabajador = True
                profile.save()
                return profile
            except UserProfile.DoesNotExist:
                # Si no tiene UserProfile, lo creamos con los datos del trabajador
                profile = UserProfile.objects.create(
                    user=user,
                    nombre=trabajador.nombre,
                    apellido=trabajador.apellido,
                    foto_perfil=trabajador.foto_perfil,
                    descripcion_usuario=trabajador.descripcion_usuario,
                    es_trabajador=True
                )
                return profile
        except Trabajador.DoesNotExist:
            # Si no es un trabajador, manejamos como usuario normal
            try:
                return UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                # Creamos un perfil para usuario normal
                profile = UserProfile.objects.create(
                    user=user,
                    nombre=user.first_name,
                    apellido=user.last_name,
                    es_trabajador=False
                )
                return profile

    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        profile = self.get_object()
        user = self.request.user
        
        # Verificar si es un trabajador para actualizar ambos modelos
        try:
            trabajador = Trabajador.objects.get(user=user)
            # Si es trabajador, actualizamos tanto el Trabajador como el UserProfile
            
            # Actualizar los campos del trabajador
            nombre = request.data.get('nombre')
            apellido = request.data.get('apellido')
            descripcion_usuario = request.data.get('descripcion_usuario')
            foto_perfil_local = request.FILES.get('foto_perfil_local')
            
            if nombre:
                trabajador.nombre = nombre
            if apellido:
                trabajador.apellido = apellido
            if descripcion_usuario is not None:
                trabajador.descripcion_usuario = descripcion_usuario
            
            # Manejo de la imagen
            if foto_perfil_local:
                # Subir a ImgBB usando tu función existente
                imgbb_url = upload_to_imgbb(foto_perfil_local)
                if imgbb_url:
                    trabajador.foto_perfil = imgbb_url
                    profile.foto_perfil = imgbb_url
                else:
                    return Response(
                        {'error': 'Error al subir la imagen a ImgBB'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Guardar el trabajador
            trabajador.save()
            
            # Sincronizar los datos en el UserProfile
            profile.nombre = trabajador.nombre
            profile.apellido = trabajador.apellido
            profile.foto_perfil = trabajador.foto_perfil
            profile.descripcion_usuario = trabajador.descripcion_usuario
            profile.save()
            
        except Trabajador.DoesNotExist:
            # Si no es trabajador, usar el serializer normal
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Devolver la respuesta con los datos actualizados
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_trabajador(request, pk):
    try:
        trabajador = Trabajador.objects.get(pk=pk)
    except Trabajador.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = TrabajadorSerializer(trabajador, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def update_user_profile(request):
    trabajador = request.user.trabajador
    
    nombre = request.data.get('nombre')
    apellido = request.data.get('apellido')
    foto_perfil_url = request.data.get('foto_perfil')
    foto_perfil_file = request.FILES.get('foto_perfil_local')

    if nombre:
        trabajador.nombre = nombre
    if apellido:
        trabajador.apellido = apellido

    if foto_perfil_file:
        try:
            file_name = default_storage.save(f'perfil/{foto_perfil_file.name}', ContentFile(foto_perfil_file.read()))
            trabajador.foto_perfil_local = file_name
            trabajador.foto_perfil = None
        except Exception as e:
            return Response({'error': f'Error uploading file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif foto_perfil_url:
        trabajador.foto_perfil = foto_perfil_url
        trabajador.foto_perfil_local = None

    trabajador.save()

    return Response({
        'nombre': trabajador.nombre,
        'apellido': trabajador.apellido,
        'foto_perfil': trabajador.get_foto_perfil(),
    }, status=status.HTTP_200_OK)


# ============================================
# RECUPERACIÓN DE CONTRASEÑA
# ============================================

class RequestPasswordResetView(APIView):
    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Crear token de recuperación
            token_obj = PasswordResetToken.objects.create(user=user)
            
            # Enviar correo con el token
            subject = "Recuperación de contraseña"
            message = f"""
            Hola {user.username},
            
            Recibimos una solicitud para restablecer tu contraseña.
            
            Tu código de recuperación es: {token_obj.token}
            
            Este código es válido por 24 horas.
            
            Si no solicitaste este cambio, puedes ignorar este correo.
            
            Saludos,
            El equipo de [Nombre de tu aplicación]
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return Response({"message": "Se ha enviado un correo con instrucciones para recuperar tu contraseña."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyTokenView(APIView):
    def post(self, request):
        serializer = VerifyTokenSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "Token válido."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            password = serializer.validated_data['password']
            
            # Buscar el token
            token_obj = PasswordResetToken.objects.get(token=token)
            
            # Cambiar la contraseña del usuario
            user = token_obj.user
            user.set_password(password)
            user.save()
            
            # Marcar el token como usado
            token_obj.used = True
            token_obj.save()
            
            return Response({"message": "Contraseña actualizada exitosamente."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# ADMIN VIEWSET
# ============================================

class AdminViewSet(viewsets.ModelViewSet):
    queryset = BASE_QUERYSET.filter(is_staff=True)
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        total_users = User.objects.count()
        total_noticias = Noticia.objects.count()
        return Response({
            'total_users': total_users,
            'total_noticias': total_noticias,
        })


# ============================================
# LISTAS GENERICAS
# ============================================

class EstadoPublicacionList(generics.ListAPIView):
    queryset = EstadoPublicacion.objects.all()
    serializer_class = EstadoPublicacionSerializer


class TrabajadorList(generics.ListAPIView):
    queryset = Trabajador.objects.all()
    serializer_class = TrabajadorSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

    def perform_update(self, serializer):
        serializer.save()


# ============================================
# UPLOAD DE IMÁGENES
# ============================================

@api_view(['POST'])
def upload_image(request):
    if 'image' not in request.FILES:
        return Response({'error': 'No image file found'}, status=status.HTTP_400_BAD_REQUEST)

    image = request.FILES['image']

    # Verificar tipo de archivo
    if not image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return Response({
            'error': 'Tipo de archivo no soportado. Por favor suba una imagen PNG, JPG, JPEG, GIF o WebP.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Verificar tamaño del archivo (ImgBB tiene un límite de 32MB)
    if image.size > 32 * 1024 * 1024:  # 32MB en bytes
        return Response({
            'error': 'El archivo es demasiado grande. El tamaño máximo es 32MB.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Subir directamente a ImgBB
    uploaded_url = upload_to_imgbb(image)

    if uploaded_url:
        return Response({
            'success': True, 
            'url': uploaded_url,
            'message': 'Imagen subida exitosamente a ImgBB'
        })
    else:
        return Response({
            'error': 'Error al subir la imagen a ImgBB. Verifique que la imagen sea válida.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# REDIRECCIÓN
# ============================================

def redirect_to_home(request):
    return redirect('/home/')


# ============================================
# SERVICIOS VIEWSET
# ============================================

class SubcategoriaServicioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para las subcategorías de servicios
    """
    queryset = SubcategoriaServicio.objects.all()
    serializer_class = SubcategoriaServicioSerializer
    permission_classes = [AllowAny]


# En views.py - Reemplaza toda la clase ServicioViewSet

# En views.py - Reemplaza toda la clase ServicioViewSet

class ServicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet optimizado para gestionar servicios con carga rápida
    """
    # OPTIMIZACIÓN 1: Usar select_related para cargar subcategoría en una sola query
    queryset = Servicio.objects.select_related('subcategoria').all()
    serializer_class = ServicioSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titulo', 'descripcion', 'palabras_clave']
    ordering_fields = ['fecha_creacion', 'titulo']
    ordering = ['-fecha_creacion']
    lookup_field = 'pk'
    permission_classes = [IsAuthenticatedOrReadOnly]

    # OPTIMIZACIÓN 2: Sobrescribir get_queryset para optimizar queries
    def get_queryset(self):
        """Optimiza el queryset según el usuario y usa select_related"""
        queryset = Servicio.objects.select_related('subcategoria')
        
        if self.request.user.is_authenticated and self.request.user.is_staff:
            # Staff ve todos los servicios
            return queryset.all()
        else:
            # Usuarios normales solo ven servicios activos
            return queryset.filter(activo=True)
    
    def list(self, request, *args, **kwargs):
        """Override list con queryset optimizado"""
        print("\n" + "="*50)
        print("LIST SERVICIOS - DEBUG OPTIMIZADO")
        print("="*50)
        print(f"Usuario: {request.user}")
        print(f"Es staff: {request.user.is_staff if request.user.is_authenticated else 'No auth'}")
        
        # Usar el queryset ya optimizado
        queryset = self.filter_queryset(self.get_queryset())
        
        print(f"Total servicios en queryset: {queryset.count()}")
        
        # OPTIMIZACIÓN 3: Usar serializer con many=True de forma eficiente
        serializer = self.get_serializer(queryset, many=True)
        
        print(f"Servicios serializados: {len(serializer.data)}")
        print("="*50 + "\n")
        
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Obtener un servicio específico con select_related"""
        instance = self.get_object()
        print(f"\nRETRIEVE Servicio ID {instance.id}: activo={instance.activo}")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Crear un nuevo servicio"""
        print("\n" + "="*50)
        print("CREATE SERVICIO")
        print("="*50)
        print(f"Datos recibidos: {request.data}")
        
        response = super().create(request, *args, **kwargs)
        
        print(f"Servicio creado: ID {response.data.get('id')}")
        print(f"Estado activo: {response.data.get('activo')}")
        print("="*50 + "\n")
        
        return response
    
    def update(self, request, *args, **kwargs):
        """Actualizar un servicio"""
        print("\n" + "="*50)
        print("UPDATE SERVICIO")
        print("="*50)
        
        instance = self.get_object()
        print(f"Servicio ID: {instance.id}")
        print(f"Estado activo anterior: {instance.activo}")
        print(f"Datos recibidos: {request.data}")
        
        response = super().update(request, *args, **kwargs)
        
        # Refrescar instancia
        instance.refresh_from_db()
        print(f"Estado activo después: {instance.activo}")
        print("="*50 + "\n")
        
        return response
    
    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial de un servicio"""
        print("\n" + "="*50)
        print("PARTIAL UPDATE SERVICIO")
        print("="*50)
        
        instance = self.get_object()
        print(f"Servicio ID: {instance.id}")
        print(f"Estado activo anterior: {instance.activo}")
        print(f"Datos recibidos: {request.data}")
        
        response = super().partial_update(request, *args, **kwargs)
        
        # Refrescar instancia
        instance.refresh_from_db()
        print(f"Estado activo después: {instance.activo}")
        print("="*50 + "\n")
        
        return response
    
    @action(detail=False, methods=['get'], url_path='activos')
    def activos(self, request):
        """Obtener servicios activos - OPTIMIZADO"""
        # Usar el queryset base ya optimizado
        servicios = self.get_queryset().filter(activo=True)
        
        limit = request.query_params.get('limit')
        if limit:
            try:
                servicios = servicios[:int(limit)]
            except ValueError:
                pass
        
        serializer = self.get_serializer(servicios, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='consultoria-estrategica')
    def consultoria_estrategica(self, request):
        """Obtener servicios de Consultoría Estratégica - OPTIMIZADO"""
        servicios = self.get_queryset().filter(
            activo=True,
            subcategoria__nombre='consultoria_estrategica'
        )
        
        limit = request.query_params.get('limit')
        if limit:
            try:
                servicios = servicios[:int(limit)]
            except ValueError:
                pass
        
        serializer = self.get_serializer(servicios, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='capacitaciones-especializadas')
    def capacitaciones_especializadas(self, request):
        """Obtener servicios de Capacitaciones Especializadas - OPTIMIZADO"""
        servicios = self.get_queryset().filter(
            activo=True,
            subcategoria__nombre='capacitaciones_especializadas'
        )
        
        limit = request.query_params.get('limit')
        if limit:
            try:
                servicios = servicios[:int(limit)]
            except ValueError:
                pass
        
        serializer = self.get_serializer(servicios, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='toggle-activo')
    def toggle_activo(self, request, pk=None):
        """Cambiar el estado activo/inactivo de un servicio - OPTIMIZADO"""
        print(f"\n{'='*50}")
        print(f"TOGGLE ACTIVO - Servicio ID: {pk}")
        print(f"{'='*50}")
        
        try:
            # Usar select_related incluso aquí
            servicio = self.get_queryset().get(pk=pk)
            
            estado_anterior = servicio.activo
            print(f"Estado anterior: {estado_anterior}")
            
            # Cambiar estado
            servicio.activo = not servicio.activo
            
            # Guardar EXPLÍCITAMENTE solo el campo activo
            servicio.save(update_fields=['activo'])
            
            # Verificar que se guardó en la BD
            servicio.refresh_from_db()
            print(f"Estado nuevo en BD: {servicio.activo}")
            print(f"✅ Cambio guardado exitosamente")
            print(f"{'='*50}\n")
            
            # Serializar la respuesta completa
            serializer = self.get_serializer(servicio)
            
            return Response({
                'success': True,
                'activo': servicio.activo,
                'message': f'Servicio {"activado" if servicio.activo else "desactivado"} exitosamente',
                'servicio': serializer.data
            })
        
        except Servicio.DoesNotExist:
            print(f"❌ ERROR: Servicio con ID {pk} no encontrado")
            return Response(
                {'error': f'Servicio con ID {pk} no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            print(f"❌ ERROR al cambiar estado: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    


# ============================================
# NEWSLETTER VIEWSET
# ============================================

class NewsletterSubscriberViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Suscribirse al newsletter"""
        email = request.data.get('email')
        nombre = request.data.get('nombre', '')
        
        if not email:
            return Response(
                {'error': 'El email es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar si ya existe
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'nombre': nombre}
        )
        
        if not created:
            if subscriber.confirmado:
                return Response(
                    {'message': 'Este email ya está suscrito'},
                    status=status.HTTP_200_OK
                )
            else:
                # Reenviar email de confirmación
                send_confirmation_email(subscriber)
                return Response(
                    {'message': 'Te hemos reenviado el email de confirmación'},
                    status=status.HTTP_200_OK
                )
        
        # Enviar email de confirmación
        if send_confirmation_email(subscriber):
            return Response(
                {'message': 'Suscripción exitosa. Por favor revisa tu email para confirmar.'},
                status=status.HTTP_201_CREATED
            )
        else:
            subscriber.delete()
            return Response(
                {'error': 'Error al enviar el email de confirmación'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='confirmar/(?P<token>[^/.]+)')
    def confirmar(self, request, token=None):
        """Confirmar suscripción"""
        try:
            subscriber = NewsletterSubscriber.objects.get(token_confirmacion=token)
            subscriber.confirmado = True
            subscriber.activo = True
            subscriber.save()
            
            return Response(
                {'message': 'Suscripción confirmada exitosamente'},
                status=status.HTTP_200_OK
            )
        except NewsletterSubscriber.DoesNotExist:
            return Response(
                {'error': 'Token inválido'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def cancelar(self, request):
        """Cancelar suscripción"""
        email = request.data.get('email')
        
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email)
            subscriber.activo = False
            subscriber.save()
            
            return Response(
                {'message': 'Suscripción cancelada exitosamente'},
                status=status.HTTP_200_OK
            )
        except NewsletterSubscriber.DoesNotExist:
            return Response(
                {'error': 'Email no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def enviar_noticia(self, request):
        """Enviar noticia a todos los suscriptores (solo para admins)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'No tienes permisos para esta acción'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        noticia_id = request.data.get('noticia_id')
        
        try:
            noticia = Noticia.objects.get(pk=noticia_id)
            subscribers = NewsletterSubscriber.objects.filter(
                activo=True,
                confirmado=True
            )
            
            if not subscribers.exists():
                return Response(
                    {'message': 'No hay suscriptores activos'},
                    status=status.HTTP_200_OK
                )
            
            success_count = send_newsletter_notification(noticia, subscribers)
            
            return Response({
                'message': f'Newsletter enviado a {success_count} suscriptores',
                'total': subscribers.count(),
                'success': success_count
            }, status=status.HTTP_200_OK)
            
        except Noticia.DoesNotExist:
            return Response(
                {'error': 'Noticia no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

# Agregar estos imports al inicio de views.py
from .models import Contacto
from .serializers import ContactoSerializer

# Agregar este ViewSet al final de views.py

# En views.py - Reemplaza la clase ContactoViewSet

class ContactoViewSet(viewsets.ModelViewSet):
    """
    ViewSet optimizado para gestionar mensajes de contacto
    """
    # OPTIMIZACIÓN 1: Ordenar con índices
    queryset = Contacto.objects.all().order_by('-fecha_envio')
    serializer_class = ContactoSerializer
    
    # OPTIMIZACIÓN 2: Filtros optimizados
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha_envio', 'leido', 'respondido']
    ordering = ['-fecha_envio']
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated(), permissions.IsAdminUser()]
    
    # OPTIMIZACIÓN 3: Override get_queryset para usar only()
    def get_queryset(self):
        """Optimiza el queryset cargando solo campos necesarios"""
        return Contacto.objects.only(
            'id', 'nombre', 'email', 'asunto', 'mensaje',
            'fecha_envio', 'leido', 'respondido'
        ).order_by('-fecha_envio')
    
    def list(self, request, *args, **kwargs):
        """Override list con queryset optimizado"""
        queryset = self.get_queryset()
        
        # Filtros opcionales
        leido = request.query_params.get('leido')
        respondido = request.query_params.get('respondido')
        
        if leido is not None:
            queryset = queryset.filter(leido=leido.lower() == 'true')
        
        if respondido is not None:
            queryset = queryset.filter(respondido=respondido.lower() == 'true')
        
        # OPTIMIZACIÓN 4: Usar values() para la lista ligera
        # Esto evita cargar objetos completos si no se necesitan
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'no_leidos': Contacto.objects.filter(leido=False).count(),
            'resultados': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        """Crear un nuevo mensaje de contacto"""
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Datos inválidos', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            contacto = serializer.save()
            
            # Opcional: Enviar notificación asíncrona
            try:
                self._enviar_notificacion_admin(contacto)
            except Exception as email_error:
                print(f"⚠️ Error al enviar notificación: {email_error}")
            
            return Response(
                {
                    'success': True,
                    'message': 'Mensaje enviado exitosamente. Te contactaremos pronto.',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            return Response(
                {'error': f'Error al enviar mensaje: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def marcar_leido(self, request, pk=None):
        """Marcar mensaje como leído - OPTIMIZADO"""
        # OPTIMIZACIÓN: update() es más rápido que save()
        Contacto.objects.filter(pk=pk).update(leido=True)
        
        return Response({
            'success': True,
            'message': 'Mensaje marcado como leído'
        })
    
    @action(detail=True, methods=['post'])
    def marcar_respondido(self, request, pk=None):
        """Marcar mensaje como respondido - OPTIMIZADO"""
        Contacto.objects.filter(pk=pk).update(respondido=True)
        
        return Response({
            'success': True,
            'message': 'Mensaje marcado como respondido'
        })
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Obtener estadísticas - OPTIMIZADO con aggregate
        """
        from django.db.models import Count, Q
        
        # OPTIMIZACIÓN: Una sola query con aggregate
        stats = Contacto.objects.aggregate(
            total=Count('id'),
            no_leidos=Count('id', filter=Q(leido=False)),
            no_respondidos=Count('id', filter=Q(respondido=False))
        )
        
        return Response(stats)
    
    def _enviar_notificacion_admin(self, contacto):
        """Enviar email de notificación a los administradores"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        admin_emails = User.objects.filter(
            is_staff=True, 
            is_active=True
        ).values_list('email', flat=True)
        
        if not admin_emails:
            return
        
        subject = f"Nuevo mensaje de contacto: {contacto.asunto}"
        message = f"""
        Has recibido un nuevo mensaje de contacto:
        
        Nombre: {contacto.nombre}
        Email: {contacto.email}
        Asunto: {contacto.asunto}
        
        Mensaje:
        {contacto.mensaje}
        
        Fecha: {contacto.fecha_envio.strftime('%d/%m/%Y %H:%M')}
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            list(admin_emails),
            fail_silently=True,
        )