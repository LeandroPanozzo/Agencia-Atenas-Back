from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Rol, Trabajador, UserProfile, Usuario, Noticia, Comentario, EstadoPublicacion, Imagen, Publicidad, upload_to_imgbb
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from .serializers import UserProfileSerializer, UserRegistrationSerializer, LoginSerializer
from django.core.files.storage import default_storage
import uuid

from django.core.files.base import ContentFile
from rest_framework.decorators import api_view
import os
from django.conf import settings
from rest_framework import generics
from rest_framework.exceptions import NotFound
from django.shortcuts import redirect
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.models import User
from .serializers import UserSerializer
from django.utils import timezone  # Añade esta importación
from datetime import timedelta     # Añade esta importación
from rest_framework.permissions import AllowAny, IsAuthenticated

from .serializers import (
    RolSerializer, TrabajadorSerializer, UsuarioSerializer, NoticiaSerializer,
    ComentarioSerializer, EstadoPublicacionSerializer, ImagenSerializer, PublicidadSerializer
)

BASE_QUERYSET = User.objects.all()

class UserrViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Permite el acceso sin autenticación

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer

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

class ComentarioViewSet(viewsets.ModelViewSet):
    queryset = Comentario.objects.all()
    serializer_class = ComentarioSerializer

    def get_queryset(self):
        noticia_id = self.kwargs['noticia_id']
        return self.queryset.filter(noticia_id=noticia_id)

    def destroy(self, request, noticia_id, comment_id):
        try:
            comentario = self.get_queryset().get(id=comment_id)
            comentario.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Comentario.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error deleting comment: {e}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CommentDeleteView(APIView):
    def delete(self, request, noticia_id, comment_id):
        try:
            comment = Comentario.objects.get(id=comment_id, noticia_id=noticia_id)
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Comentario.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class ComentarioListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ComentarioSerializer

    def get_queryset(self):
        noticia_id = self.kwargs['noticia_id']
        return Comentario.objects.filter(noticia_id=noticia_id)

    def perform_create(self, serializer):
        noticia_id = self.kwargs['noticia_id']
        serializer.save(noticia_id=noticia_id)

class PublicidadViewSet(viewsets.ModelViewSet):
    queryset = Publicidad.objects.all()
    serializer_class = PublicidadSerializer

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
from .models import Noticia, Trabajador
from .serializers import NoticiaSerializer
from django.shortcuts import get_object_or_404


class NoticiaViewSet(viewsets.ModelViewSet):
    queryset = Noticia.objects.all()
    serializer_class = NoticiaSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha_publicacion', 'contador_visitas']
    ordering = ['-fecha_publicacion']
    lookup_field = 'pk'
    lookup_value_regex = r'[0-9]+(?:-[a-zA-Z0-9-_]+)?'
    
    def get_queryset(self):
        """
        Queryset optimizado con select_related y prefetch_related
        """
        base_queryset = Noticia.objects.select_related(
            'autor', 'estado'
        ).prefetch_related(
            'editores_en_jefe'
        )
        
        # Aplicar filtros solo si se necesitan
        autor = self.request.query_params.get('autor')
        if autor:
            base_queryset = base_queryset.filter(autor=autor)
        
        estado = self.request.query_params.get('estado')
        if estado:
            base_queryset = base_queryset.filter(estado=estado)
        
        categoria = self.request.query_params.get('categoria')
        if categoria:
            categorias = categoria.split(',')
            if len(categorias) > 1:
                from django.db.models import Q
                category_query = Q()
                for cat in categorias:
                    category_query |= Q(categorias__contains=cat)
                base_queryset = base_queryset.filter(category_query)
            else:
                base_queryset = base_queryset.filter(categorias__contains=categoria)
        
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            base_queryset = base_queryset.filter(fecha_publicacion__gte=fecha_desde)
            
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            base_queryset = base_queryset.filter(fecha_publicacion__lte=fecha_hasta)
            
        return base_queryset

    def list(self, request, *args, **kwargs):
        """Override list method to apply limit after ordering"""
        queryset = self.filter_queryset(self.get_queryset())
        
        limit = self.request.query_params.get('limit')
        if limit and limit.isdigit():
            queryset = queryset[:int(limit)]
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        instance.incrementar_visitas(ip_address=ip)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def mas_vistas(self, request):
        """Versión optimizada de mas_vistas."""
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        
        # Optimizar consulta
        noticias_mas_vistas = self.queryset.select_related('autor', 'estado').filter(
            estado=3
        ).only(
            'id', 'nombre_noticia', 'fecha_publicacion', 'slug', 'contenido', 
            'imagen_1', 'categorias', 'contador_visitas', 'contador_visitas_total',
            'mostrar_creditos', 'autor__nombre', 'autor__apellido'
        ).order_by('-contador_visitas')[:limit]
        
        serializer = self.get_serializer(noticias_mas_vistas, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['get'])
    def mas_leidas(self, request):
        """Versión optimizada de mas_leidas."""
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        
        # Optimizar consulta
        noticias_mas_leidas = self.queryset.select_related('autor', 'estado').filter(
            estado=3
        ).only(
            'id', 'nombre_noticia', 'fecha_publicacion', 'slug', 'contenido', 
            'imagen_1', 'categorias', 'contador_visitas_total',
            'mostrar_creditos', 'autor__nombre', 'autor__apellido'
        ).order_by('-contador_visitas_total')[:limit]
        
        serializer = self.get_serializer(noticias_mas_leidas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def populares_semana(self, request):
        """Alias para mas_vistas"""
        return self.mas_vistas(request)

    @action(detail=False, methods=['get'])
    def populares_historico(self, request):
        """Alias para mas_leidas"""
        return self.mas_leidas(request)

    @action(detail=False, methods=['get'])
    def estadisticas_visitas(self, request):
        """Retorna estadísticas generales de visitas"""
        from django.db.models import Sum, Avg, Max
        
        stats = self.queryset.filter(estado=3).aggregate(
            total_visitas_semanales=Sum('contador_visitas'),
            total_visitas_historicas=Sum('contador_visitas_total'),
            promedio_visitas_semanales=Avg('contador_visitas'),
            promedio_visitas_historicas=Avg('contador_visitas_total'),
            max_visitas_semanales=Max('contador_visitas'),
            max_visitas_historicas=Max('contador_visitas_total'),
            total_noticias=models.Count('id')
        )
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def recientes(self, request):
        """Versión optimizada de recientes."""
        limit = request.query_params.get('limit', 5)
        try:
            limit = int(limit)
        except ValueError:
            limit = 5
        
        # Optimizar consulta
        noticias_recientes = self.queryset.select_related('autor', 'estado').filter(
            estado=3
        ).only(
            'id', 'nombre_noticia', 'fecha_publicacion', 'slug', 'contenido', 
            'imagen_1', 'categorias', 'mostrar_creditos', 'autor__nombre', 'autor__apellido'
        ).order_by('-fecha_publicacion')[:limit]
        
        serializer = self.get_serializer(noticias_recientes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def destacadas(self, request):
        """Versión optimizada de destacadas."""
        limit = request.query_params.get('limit', 12)
        try:
            limit = int(limit)
        except ValueError:
            limit = 12
        
        # Optimizar consulta
        noticias_destacadas = self.queryset.select_related('autor', 'estado').filter(
            estado=3
        ).only(
            'id', 'nombre_noticia', 'fecha_publicacion', 'slug', 'contenido', 
            'imagen_1', 'categorias', 'mostrar_creditos', 'autor__nombre', 'autor__apellido'
        ).order_by('-fecha_publicacion')[:limit]
        
        serializer = self.get_serializer(noticias_destacadas, many=True)
        return Response(serializer.data)

    # MÉTODOS SIMPLIFICADOS PARA CATEGORÍAS
    @action(detail=False, methods=['get'])
    def locales(self, request):
        """Return news from the Politics category."""
        return self._get_category_news(request, 'locales')

    @action(detail=False, methods=['get'])
    def policiales(self, request):
        """Return news from the Culture category."""
        return self._get_category_news(request, 'policiales')

    @action(detail=False, methods=['get'])
    def politica_y_economia(self, request):
        """Return news from the Economy category."""
        return self._get_category_news(request, 'politica y economia')

    @action(detail=False, methods=['get'])
    def provinciales(self, request):
        """Return news from the World category."""
        return self._get_category_news(request, 'provinciales')

    @action(detail=False, methods=['get'])
    def nacionales(self, request):
        """Return analysis news."""
        return self._get_category_news(request, 'nacionales')

    @action(detail=False, methods=['get'])
    def deportes(self, request):
        """Return opinion news."""
        return self._get_category_news(request, 'deportes')

    @action(detail=False, methods=['get'])
    def familia(self, request):
        """Return informative news."""
        return self._get_category_news(request, 'familia')

    @action(detail=False, methods=['get'])
    def internacionales(self, request):
        """Return interview news."""
        return self._get_category_news(request, 'internacionales')
    
    @action(detail=False, methods=['get'])
    def interes_general(self, request):
        """Return interview news."""
        return self._get_category_news(request, 'interes general')

    def _get_category_news(self, request, category):
        """Helper method optimizado para obtener noticias por categoría."""
        limit = request.query_params.get('limit', 7)
        try:
            limit = int(limit)
        except ValueError:
            limit = 7
        
        # Usar select_related para optimizar
        category_news = self.queryset.select_related('autor', 'estado').filter(
            categorias__contains=category,
            estado=3
        ).only(
            'id', 'nombre_noticia', 'fecha_publicacion', 'slug', 'contenido', 
            'imagen_1', 'categorias', 'contador_visitas', 'mostrar_creditos',
            'autor__nombre', 'autor__apellido'
        ).order_by('-fecha_publicacion')[:limit]
        
        serializer = self.get_serializer(category_news, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_categoria(self, request):
        """Return news filtered by one or more categories."""
        categoria = request.query_params.get('categoria')
        if not categoria:
            return Response({"error": "Se requiere el parámetro 'categoria'"}, status=status.HTTP_400_BAD_REQUEST)
            
        categorias = categoria.split(',')
        estado = request.query_params.get('estado', 3)
        limit = request.query_params.get('limit')
        
        queryset = self.queryset.filter(estado=estado)
        
        if len(categorias) > 1:
            category_query = Q()
            for cat in categorias:
                if cat.strip():
                    category_query |= Q(categorias__contains=cat.strip())
            queryset = queryset.filter(category_query)
        else:
            queryset = queryset.filter(categorias__contains=categoria)
            
        queryset = queryset.order_by('-fecha_publicacion')
        
        if limit and limit.isdigit():
            queryset = queryset[:int(limit)]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def agregar_editor(self, request, pk=None):
        noticia = self.get_object()
        editor_id = request.data.get('editor_id')
        
        if not editor_id:
            return Response({'error': 'Se requiere un ID de editor'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            editor = Trabajador.objects.get(pk=editor_id)
            noticia.editores_en_jefe.add(editor)
            return Response({'success': True})
        except Trabajador.DoesNotExist:
            return Response({'error': 'Editor no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def eliminar_editor(self, request, pk=None):
        noticia = self.get_object()
        editor_id = request.data.get('editor_id')
        
        if not editor_id:
            return Response({'error': 'Se requiere un ID de editor'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            editor = Trabajador.objects.get(pk=editor_id)
            noticia.editores_en_jefe.remove(editor)
            return Response({'success': True})
        except Trabajador.DoesNotExist:
            return Response({'error': 'Editor no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    def get_object(self):
        """Retrieve the object with support for pk or pk-slug format in the URL."""
        pk_value = self.kwargs.get(self.lookup_field)
        
        if pk_value and '-' in pk_value:
            pk_parts = pk_value.split('-', 1)
            pk = pk_parts[0]
        else:
            pk = pk_value
        
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset, pk=pk)
        
        self.check_object_permissions(self.request, obj)
        return obj
            
    @action(detail=False, methods=['post'])
    def upload_image(self, request):
        if 'image' not in request.FILES:
            return Response({'error': 'No image file found'}, status=status.HTTP_400_BAD_REQUEST)
            
        image = request.FILES['image']
        
        if not image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return Response({
                'error': 'Tipo de archivo no soportado. Por favor suba una imagen PNG, JPG, JPEG, GIF o WebP.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Verificar tamaño del archivo (ImgBB tiene un límite de 32MB)
        if image.size > 32 * 1024 * 1024:  # 32MB en bytes
            return Response({
                'error': 'El archivo es demasiado grande. El tamaño máximo es 32MB.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
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
User = get_user_model()

# Vista para el registro de usuarios
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


def redirect_to_home(request):
    return redirect('/home/')

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("Usuario no autenticado.")
        
        # Intentar obtener el perfil del usuario
        try:
            # Primero buscamos en UserProfile
            return UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            # Si no existe, verificamos si es un trabajador
            try:
                trabajador = Trabajador.objects.get(user=user)
                # Si es un trabajador, creamos un UserProfile asociado
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
                # Si no es un trabajador, creamos un perfil vacío
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
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vista para el inicio de sesión de usuarios
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Add debugging to see what's being received
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

class AdminViewSet(viewsets.ModelViewSet):
    queryset = BASE_QUERYSET.filter(is_staff=True)
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        # Add logic for admin dashboard data
        total_users = User.objects.count()
        total_noticias = Noticia.objects.count()
        # Add more statistics as needed
        return Response({
            'total_users': total_users,
            'total_noticias': total_noticias,
            # Add more data as needed
        })
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
    trabajador = request.user.trabajador  # Obtener el trabajador asociado al usuario
    
    # Obtener los datos enviados en la solicitud
    nombre = request.data.get('nombre')
    apellido = request.data.get('apellido')
    foto_perfil_url = request.data.get('foto_perfil')  # URL de la imagen
    foto_perfil_file = request.FILES.get('foto_perfil_local')  # Imagen local

    # Actualizar los campos básicos si están presentes
    if nombre:
        trabajador.nombre = nombre
    if apellido:
        trabajador.apellido = apellido

    # Manejo de la imagen de perfil
    if foto_perfil_file:
        # Si se envía una imagen local, se guarda en el servidor
        try:
            file_name = default_storage.save(f'perfil/{foto_perfil_file.name}', ContentFile(foto_perfil_file.read()))
            trabajador.foto_perfil_local = file_name
            trabajador.foto_perfil = None  # Limpiar el campo de URL si se sube una imagen local
        except Exception as e:
            return Response({'error': f'Error uploading file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif foto_perfil_url:
        # Si se envía una URL de la imagen, actualizamos el campo
        trabajador.foto_perfil = foto_perfil_url
        trabajador.foto_perfil_local = None  # Limpiar el campo de archivo local si se proporciona una URL

    # Guardar los cambios en el perfil del trabajador
    trabajador.save()

    # Devolver una respuesta con los datos actualizados del trabajador
    return Response({
        'nombre': trabajador.nombre,
        'apellido': trabajador.apellido,
        'foto_perfil': trabajador.get_foto_perfil(),  # Método que devuelve la URL o el archivo local
    }, status=status.HTTP_200_OK)


#para las reacciones de las noticias:


# views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Noticia, ReaccionNoticia
from .serializers import ReaccionNoticiaSerializer

@api_view(['GET', 'POST', 'DELETE'])
def reacciones_noticia(request, id):
    try:
        noticia = Noticia.objects.get(pk=id)
    except Noticia.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Cualquier usuario puede ver el conteo
        return Response(noticia.get_conteo_reacciones())

    # Para POST y DELETE requerimos autenticación
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Debes iniciar sesión para realizar esta acción'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == 'POST':
        tipo_reaccion = request.data.get('tipo_reaccion')
        if not tipo_reaccion:
            return Response(
                {'error': 'tipo_reaccion es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        reaccion, created = ReaccionNoticia.objects.update_or_create(
            noticia=noticia,
            usuario=request.user,
            defaults={'tipo_reaccion': tipo_reaccion}
        )
        
        serializer = ReaccionNoticiaSerializer(reaccion)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    elif request.method == 'DELETE':
        ReaccionNoticia.objects.filter(
            noticia=noticia,
            usuario=request.user
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mi_reaccion(request, id):
    try:
        noticia = Noticia.objects.get(pk=id)
        reaccion = ReaccionNoticia.objects.get(
            noticia=noticia,
            usuario=request.user
        )
        serializer = ReaccionNoticiaSerializer(reaccion)
        return Response(serializer.data)
    except Noticia.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    except ReaccionNoticia.DoesNotExist:
        return Response({'tipo_reaccion': None})
    

# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import PasswordResetToken
from .serializers import RequestPasswordResetSerializer, VerifyTokenSerializer, ResetPasswordSerializer
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

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
    

@action(detail=False, methods=['get'])
def home_data(self, request):
    """
    Endpoint optimizado que retorna todos los datos necesarios para la home en una sola consulta
    """
    from django.db.models import Prefetch
    
    # Base queryset optimizado con select_related y prefetch_related
    base_queryset = self.queryset.select_related(
        'autor', 'estado'
    ).prefetch_related(
        Prefetch('editores_en_jefe', queryset=Trabajador.objects.only('nombre', 'apellido'))
    ).filter(estado=3).only(
        'id', 'nombre_noticia', 'fecha_publicacion', 'slug', 'contenido', 
        'imagen_1', 'categorias', 'contador_visitas', 'contador_visitas_total',
        'mostrar_creditos', 'autor__nombre', 'autor__apellido'
    )
    
    # Obtener datos en paralelo usando una sola consulta base
    all_news = list(base_queryset.order_by('-fecha_publicacion')[:100])  # Cache las primeras 100
    
    # Filtrar y organizar los datos en memoria (más rápido que múltiples consultas)
    featured = all_news[:12]
    recent = all_news[:5]
    most_viewed = sorted(all_news, key=lambda x: x.contador_visitas_total, reverse=True)[:5]
    
    # Categorizar noticias en memoria
    categories = {
        'locales': [],
        'policiales': [],
        'politica y economia': [],
        'provinciales': [],
        'nacionales': [],
        'deportes': [],
        'familia': [],
        'internacionales': [],
        'interes general': []
    }
    
    # Distribuir noticias por categorías (más eficiente que consultas separadas)
    for news in all_news:
        if news.categorias:
            news_categories = [cat.strip() for cat in news.categorias.split(',')]
            for category in categories.keys():
                if category in news_categories and len(categories[category]) < 7:
                    categories[category].append(news)
                    break
    
    # Serializar datos de forma optimizada
    def serialize_news(news_item):
        return {
            'id': news_item.id,
            'nombre_noticia': news_item.nombre_noticia,
            'fecha_publicacion': news_item.fecha_publicacion,
            'slug': news_item.slug,
            'contenido': news_item.contenido,
            'imagen_1': news_item.imagen_1,
            'categorias': news_item.categorias,
            'contador_visitas': news_item.contador_visitas,
            'contador_visitas_total': news_item.contador_visitas_total,
            'mostrar_creditos': news_item.mostrar_creditos,
            'autor__nombre': news_item.autor.nombre if news_item.autor else None,
            'autor__apellido': news_item.autor.apellido if news_item.autor else None,
        }
    
    # Construir respuesta optimizada
    response_data = {
        'featured': [serialize_news(item) for item in featured],
        'recent': [serialize_news(item) for item in recent],
        'most_viewed': [serialize_news(item) for item in most_viewed],
        'sections': {
            category: [serialize_news(item) for item in news_list]
            for category, news_list in categories.items()
        }
    }
    
    return Response(response_data)
