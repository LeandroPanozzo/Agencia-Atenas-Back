from django.db import models
from django.contrib.auth.models import User
import requests
import os
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from datetime import timedelta
import requests
import time
import os
import base64
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError

def validate_positive(value):
    if value <= 0:
        raise ValidationError('El valor debe ser positivo.')


class Rol(models.Model):
    nombre_rol = models.CharField(max_length=50)
    puede_publicar = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    puede_eliminar = models.BooleanField(default=False)
    puede_asignar_roles = models.BooleanField(default=False)
    puede_dejar_comentarios = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre_rol


import os

import os


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=True, blank=True)  # Cambio aquí
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    foto_perfil = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    descripcion_usuario = models.TextField(blank=True, null=True)
    es_trabajador = models.BooleanField(default=False)

class Trabajador(models.Model):
    DEFAULT_FOTO_PERFIL_URL = 'https://i.ibb.co/default-profile.png'  # URL por defecto de ImgBB
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    id = models.AutoField(primary_key=True)
    correo = models.EmailField(unique=False)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    foto_perfil = models.URLField(blank=True, null=True)
    foto_perfil_local = models.ImageField(upload_to='perfil/', blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.ForeignKey('Rol', on_delete=models.CASCADE, related_name='trabajadores', null=False)

    @property
    def descripcion_usuario(self):
        if self.user_profile:
            return self.user_profile.descripcion_usuario
        return None

    @descripcion_usuario.setter
    def descripcion_usuario(self, value):
        if self.user_profile:
            self.user_profile.descripcion_usuario = value
            self.user_profile.save()

    def save(self, *args, **kwargs):
        # Obtener la instancia anterior si existe
        old_instance = None
        if self.pk:  # Solo si ya existe una instancia guardada previamente
            try:
                old_instance = Trabajador.objects.get(pk=self.pk)
            except Trabajador.DoesNotExist:
                pass

        # Crear un nuevo UserProfile si no existe
        if not self.user_profile:
            self.user_profile = UserProfile.objects.create(
                nombre=self.nombre,
                apellido=self.apellido
            )

        # Manejar la imagen de perfil (local o URL)
        self._handle_image('foto_perfil', 'foto_perfil_local')

        # Si no hay imagen local ni URL, asignar la imagen por defecto
        if not self.foto_perfil and not self.foto_perfil_local:
            self.foto_perfil = self.DEFAULT_FOTO_PERFIL_URL

        # Llamar a la versión original del método `save`
        super().save(*args, **kwargs)

        # Nota: ImgBB no permite eliminar imágenes vía API pública
        # por lo que comentamos la eliminación automática
        # if old_instance:
        #     self._delete_old_image(old_instance, 'foto_perfil')

    def _handle_image(self, image_field, image_local_field):
        image_local = getattr(self, image_local_field)
        image_url = getattr(self, image_field)

        # Si es una imagen local, subirla a ImgBB
        if image_local and os.path.exists(image_local.path):
            uploaded_image_url = upload_to_imgbb(image_local.path)
            if uploaded_image_url:
                setattr(self, image_field, uploaded_image_url)
            else:
                # Si falla la subida, usar la URL por defecto
                setattr(self, image_field, self.DEFAULT_FOTO_PERFIL_URL)
        elif image_url:
            # Si hay una URL proporcionada, la usamos
            setattr(self, image_field, image_url)
        else:
            # Si no hay imagen ni URL, usar el valor por defecto
            setattr(self, image_field, self.DEFAULT_FOTO_PERFIL_URL)

    def _delete_old_image(self, old_instance, field_name):
        """
        Método mantenido por compatibilidad pero ImgBB no soporta eliminación
        """
        old_image_url = getattr(old_instance, field_name)
        new_image_url = getattr(self, field_name)
        if old_image_url and old_image_url != new_image_url:
            print(f"Nota: No se puede eliminar automáticamente la imagen anterior de ImgBB: {old_image_url}")
            # delete_from_imgbb(old_image_url)  # Comentado porque no funciona

    def get_foto_perfil(self):
        return self.foto_perfil_local.url if self.foto_perfil_local else self.foto_perfil or self.DEFAULT_FOTO_PERFIL_URL

    def __str__(self):
        return f'{self.nombre} {self.apellido}'



import requests
import time
import os
from django.core.files.uploadedfile import InMemoryUploadedFile

IMGBB_API_KEY = 'a315981b1bce71916fb736816e14d90a'
IMGBB_UPLOAD_URL = 'https://api.imgbb.com/1/upload'

def upload_to_imgbb(image):
    """
    Sube una imagen a ImgBB y devuelve la URL
    
    Args:
        image: Puede ser un objeto InMemoryUploadedFile, una ruta a un archivo,
               o un archivo abierto en modo binario
    
    Returns:
        str: URL de la imagen en ImgBB, o None si falló la subida
    """
    try:
        # Prepara los datos según el tipo de entrada
        if isinstance(image, InMemoryUploadedFile):
            # Si es un archivo subido en memoria (desde un formulario)
            image_data = image.read()
        elif isinstance(image, str) and os.path.isfile(image):
            # Si es una ruta a un archivo
            with open(image, 'rb') as image_file:
                image_data = image_file.read()
        elif hasattr(image, 'path') and os.path.isfile(image.path):
            # Si es un campo ImageField de Django
            with open(image.path, 'rb') as image_file:
                image_data = image_file.read()
        else:
            # Si es un archivo ya abierto o cualquier otro objeto que pueda ser leído
            image_data = image.read() if hasattr(image, 'read') else image
        
        # Codificar la imagen en base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Datos para la petición
        data = {
            'key': IMGBB_API_KEY,
            'image': image_base64,
            'expiration': 0  # 0 significa que nunca expira
        }
        
        # Intentar subir la imagen a ImgBB
        response = requests.post(IMGBB_UPLOAD_URL, data=data)
        
        # Manejar límites de peticiones
        if response.status_code == 429:  # Too Many Requests
            print("Error 429: Demasiadas solicitudes, esperando antes de reintentar...")
            time.sleep(60)  # Esperar 60 segundos antes de reintentar
            return upload_to_imgbb(image)  # Reintentar la carga
        
        # Verificar respuesta
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                return response_data['data']['url']
            else:
                print(f"Error al subir imagen a ImgBB: {response_data.get('error', {}).get('message', 'Error desconocido')}")
        else:
            print(f"Error HTTP {response.status_code} al subir imagen a ImgBB")
            print(f"Respuesta: {response.text}")
        
    except Exception as e:
        print(f"Excepción al subir imagen a ImgBB: {str(e)}")
    
    return None

def delete_from_imgbb(image_url):
    """
    Elimina una imagen de ImgBB usando su URL
    
    Args:
        image_url: URL de la imagen en ImgBB
    
    Returns:
        bool: True si se eliminó correctamente, False en caso contrario
    
    Nota: ImgBB no proporciona una API pública para eliminar imágenes.
    Esta función está aquí por compatibilidad pero no hará nada.
    """
    print(f"Advertencia: ImgBB no soporta eliminación de imágenes vía API pública")
    print(f"La imagen {image_url} no se puede eliminar automáticamente")
    return False

# Función alternativa para obtener información de la imagen
def get_imgbb_image_info(image_url):
    """
    Obtiene información de una imagen de ImgBB (si es posible)
    
    Args:
        image_url: URL de la imagen en ImgBB
    
    Returns:
        dict: Información de la imagen o None si no se puede obtener
    """
    try:
        # Extraer el ID de la imagen de la URL
        # Las URLs de ImgBB suelen tener el formato: https://i.ibb.co/xxxxxx/image.ext
        if 'ibb.co' in image_url:
            parts = image_url.split('/')
            if len(parts) >= 4:
                image_id = parts[4]  # El ID está en la 5ta posición
                
                # ImgBB no tiene API pública para obtener info, pero podemos intentar
                # hacer una petición HEAD para verificar si existe
                response = requests.head(image_url, timeout=10)
                if response.status_code == 200:
                    return {
                        'url': image_url,
                        'exists': True,
                        'content_type': response.headers.get('content-type', 'unknown')
                    }
        
        return None
        
    except Exception as e:
        print(f"Error al obtener información de la imagen ImgBB: {str(e)}")
        return None

class NoticiaVisita(models.Model):
    noticia = models.ForeignKey('Noticia', on_delete=models.CASCADE, related_name='visitas')
    fecha = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['noticia']),
        ]

from django.utils.text import slugify

class Noticia(models.Model):
    # Categorías simplificadas - solo categorías principales, sin subcategorías
    CATEGORIAS = [
        ('locales', 'Locales'),
        ('policiales', 'Policiales'),
        ('politica y economia', 'Politica y Economia'),
        ('provinciales', 'Provinciales'),
        ('nacionales', 'Nacionales'),
        ('deportes', 'Deportes'),
        ('familia', 'Familia'),
        ('internacionales', 'Internacionales'),
        ('interes general', 'Interes General'),
    ]

    # Ya no necesitas FLAT_CATEGORIAS porque no hay subcategorías
    FLAT_CATEGORIAS = [cat[0] for cat in CATEGORIAS]

    # Helper method to validate categories
    def validate_categorias(value):
        """Standalone validator function for categorias field"""
        if not value:
            return ''
        categories = value.split(',')
        categories = [cat.strip() for cat in categories if cat.strip()]
        invalid_cats = [cat for cat in categories if cat not in Noticia.FLAT_CATEGORIAS]
        if invalid_cats:
            raise ValidationError(f'Invalid categories: {", ".join(invalid_cats)}')
        return ','.join(categories)

    # Add the categorias field with the fixed validator
    categorias = models.TextField(
        validators=[validate_categorias],
        blank=True,
        null=True
    )

    # Other fields...
    autor = models.ForeignKey('Trabajador', on_delete=models.CASCADE, related_name='noticias', null=False)
    editores_en_jefe = models.ManyToManyField(
        'Trabajador', 
        related_name='noticias_supervisadas',
        blank=True,
        verbose_name="Editores en jefe"
    )
    nombre_noticia = models.CharField(max_length=500)
    fecha_publicacion = models.DateField()
    url = models.URLField(max_length=200, blank=True, null=True)
    # Modificar la definición del slug para permitir slugs más largos (300 caracteres)
    slug = models.SlugField(max_length=300, unique=True, blank=True, editable=False)
    # CONTADORES DE VISITAS - NUEVOS CAMPOS
    contador_visitas = models.PositiveIntegerField(default=0, help_text="Contador semanal que se reinicia")
    contador_visitas_total = models.PositiveIntegerField(default=0, help_text="Contador permanente total")
    ultima_actualizacion_contador = models.DateTimeField(default=timezone.now)
    ultima_actualizacion_contador = models.DateTimeField(default=timezone.now)
    Palabras_clave = models.CharField(max_length=200)
    imagen_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_1 = models.URLField(blank=True, null=True)
    imagen_1_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_2 = models.URLField(blank=True, null=True)
    imagen_2_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_3 = models.URLField(blank=True, null=True)
    imagen_3_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_4 = models.URLField(blank=True, null=True)
    imagen_4_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_5 = models.URLField(blank=True, null=True)
    imagen_5_local = models.ImageField(upload_to='images/', blank=True, null=True)
    imagen_6 = models.URLField(blank=True, null=True)
    imagen_6_local = models.ImageField(upload_to='images/', blank=True, null=True)
    estado = models.ForeignKey('EstadoPublicacion', on_delete=models.SET_NULL, null=True)
    solo_para_subscriptores = models.BooleanField(default=False)
    contenido = models.TextField(default='default content')
    subtitulo = models.TextField(default='default content')
    tiene_comentarios = models.BooleanField(default=False)
    mostrar_creditos = models.BooleanField(
        default=True, 
        help_text="Si está marcado, se mostrarán los datos del autor y editores de la noticia"
    )
    def save(self, *args, **kwargs):
        # Validate categorias before saving
        if self.categorias:
            self.categorias = Noticia.validate_categorias(self.categorias)
        
        # Verificar si el objeto existe y si el título ha cambiado
        if self.pk:
            try:
                old_instance = Noticia.objects.get(pk=self.pk)
                if old_instance.nombre_noticia != self.nombre_noticia:
                    # El título ha cambiado, actualizar el slug
                    # Ya no truncamos el título a 100 caracteres
                    self.slug = slugify(self.nombre_noticia)
                    original_slug = self.slug
                    count = 1
                    while Noticia.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                        self.slug = f"{original_slug}-{count}"
                        count += 1
            except Noticia.DoesNotExist:
                pass
        else:
            # Es un objeto nuevo, generar el slug
            # Ya no truncamos el título a 100 caracteres
            self.slug = slugify(self.nombre_noticia)
            original_slug = self.slug
            count = 1
            while Noticia.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1

        # Guarda primero para obtener un ID si es objeto nuevo
        super().save(*args, **kwargs)
        
        # Procesar imágenes y subir a Imgur
        images_updated = self._process_images(old_instance if 'old_instance' in locals() else None)
        
        # Solo guardar nuevamente si se actualizaron las imágenes
        if images_updated:
            super().save()
    
    def _process_images(self, old_instance=None):
        """Procesa todas las imágenes, sube a ImgBB y actualiza URLs"""
        images_updated = False
        
        # Procesar imágenes adicionales (1-6)
        for i in range(1, 7):
            local_field_name = f'imagen_{i}_local'
            url_field_name = f'imagen_{i}'
            
            local_field = getattr(self, local_field_name)
            if local_field and hasattr(local_field, 'file'):
                # Subir la imagen a ImgBB
                imgbb_url = upload_to_imgbb(local_field)
                if imgbb_url:
                    # Si la subida fue exitosa, actualizar la URL
                    setattr(self, url_field_name, imgbb_url)
                    # Limpiar el campo local después de subir
                    setattr(self, local_field_name, None)
                    images_updated = True
                    
                    # Para depuración
                    print(f"Imagen {i} subida a ImgBB: {imgbb_url}")
                else:
                    print(f"Error al subir imagen {i} a ImgBB")
        
        # Nota: No eliminamos imágenes antiguas porque ImgBB no lo permite
        # if old_instance:
        #     self._delete_old_images(old_instance)
        
        return images_updated
    
    def _delete_old_images(self, old_instance):
        """
        Método mantenido por compatibilidad pero ImgBB no soporta eliminación
        """
        fields_to_check = [f'imagen_{i}' for i in range(1, 7)]
        
        for field_name in fields_to_check:
            old_url = getattr(old_instance, field_name)
            new_url = getattr(self, field_name)
            
            # Si la URL ha cambiado y la antigua URL existe, mostrar mensaje
            if old_url and old_url != new_url and 'ibb.co' in old_url:
                print(f"Nota: No se puede eliminar automáticamente la imagen anterior de ImgBB: {old_url}")
                # delete_from_imgbb(old_url)  # Comentado porque no funciona

    
    def get_categorias(self):
        return self.categorias.split(',') if self.categorias else []

    def __str__(self):
        return f'{self.nombre_noticia} - {self.categorias}'

    def __str__(self):
        return f'{self.nombre_noticia} - {self.estado}'

    def get_absolute_url(self):
        return f'/noticias/{self.pk}-{self.slug}/'

    def get_image_urls(self):
        """Retorna una lista de todas las URLs de imágenes disponibles."""
        image_urls = []
       
        for i in range(1, 7):
            image_field = getattr(self, f'imagen_{i}')
            if image_field:
                image_urls.append(image_field)
        return image_urls

    def get_conteo_reacciones(self):
        return {
            'interesa': self.reacciones.filter(tipo_reaccion='interesa').count(),
            'divierte': self.reacciones.filter(tipo_reaccion='divierte').count(),
            'entristece': self.reacciones.filter(tipo_reaccion='entristece').count(),
            'enoja': self.reacciones.filter(tipo_reaccion='enoja').count(),
        }

    def incrementar_visitas(self, ip_address=None):
        from datetime import timedelta
        from django.utils import timezone
        
        # Verifica si ha pasado una semana desde la última actualización
        if timezone.now() - self.ultima_actualizacion_contador > timedelta(days=7):
            self.contador_visitas = 0
            self.ultima_actualizacion_contador = timezone.now()
            self.save()

        # NUEVO: Evitar incrementos duplicados por IP en un período corto
        if ip_address:
            # Verificar si esta IP ya visitó en los últimos 5 minutos
            hace_5_minutos = timezone.now() - timedelta(minutes=5)
            visita_reciente = NoticiaVisita.objects.filter(
                noticia=self,
                ip_address=ip_address,
                fecha__gte=hace_5_minutos
            ).exists()
            
            if visita_reciente:
                # No incrementar si ya visitó recientemente
                return False

        # Registra la visita
        NoticiaVisita.objects.create(
            noticia=self,
            ip_address=ip_address
        )
        
        # Incrementa ambos contadores
        self.contador_visitas += 1
        self.contador_visitas_total += 1
        self.save(update_fields=['contador_visitas', 'contador_visitas_total'])
        
        return True

    # Agrega una propiedad para obtener las visitas de la última semana
    @property
    def visitas_ultima_semana(self):
        hace_una_semana = timezone.now() - timedelta(days=7)
        return self.visitas.filter(fecha__gte=hace_una_semana).count()

    class Meta:
        ordering = ['-fecha_publicacion']  # Ordenamiento por defecto
        indexes = [
            models.Index(fields=['estado', '-fecha_publicacion']),  # Para consultas principales
            models.Index(fields=['estado', '-contador_visitas']),   # Para más vistas
            models.Index(fields=['estado', '-contador_visitas_total']),  # Para más leídas
            models.Index(fields=['estado', 'categorias']),          # Para filtros por categoría
            models.Index(fields=['fecha_publicacion']),             # Para ordenamiento por fecha
            models.Index(fields=['slug']),                          # Para búsqueda por slug
        ]

    @staticmethod
    def validate_categorias(value):
        """Standalone validator function for categorias field"""
        if not value:
            return ''
        categories = value.split(',')
        categories = [cat.strip() for cat in categories if cat.strip()]
        invalid_cats = [cat for cat in categories if cat not in Noticia.FLAT_CATEGORIAS]
        if invalid_cats:
            raise ValidationError(f'Invalid categories: {", ".join(invalid_cats)}')
        return ','.join(categories)

    
class Comentario(models.Model):
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    respuesta = models.TextField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.autor:
            try:
                trabajador = Trabajador.objects.get(user=self.autor)
                if not trabajador.rol.puede_dejar_comentarios:
                    raise ValueError("No tienes habilitada la opción de comentar.")
            except Trabajador.DoesNotExist:
                raise ValueError("El autor no tiene un trabajador asociado.")
        super().save(*args, **kwargs)


class EstadoPublicacion(models.Model):
    BORRADOR = 'borrador'
    EN_PAPELERA = 'en_papelera'
    PUBLICADO = 'publicado'
    LISTO_PARA_EDITAR = 'listo_para_editar'

    ESTADO_CHOICES = [
        (BORRADOR, 'Borrador'),
        (EN_PAPELERA, 'En Papelera'),
        (PUBLICADO, 'Publicado'),
        (LISTO_PARA_EDITAR, 'Listo para editar'),
    ]

    nombre_estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=BORRADOR,
    )

    def __str__(self):
        return self.get_nombre_estado_display()



class Imagen(models.Model):
    nombre_imagen = models.CharField(max_length=100)
    imagen = models.URLField(null=True, blank=True)  # URL de la imagen en ImgBB
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='imagenes')

    def save(self, *args, **kwargs):
        # Verifica si imagen es una URL o una ruta local
        if self.imagen and not self.imagen.startswith(('http://', 'https://')):
            # Si es una ruta local, sube la imagen a ImgBB
            uploaded_url = upload_to_imgbb(self.imagen)
            if uploaded_url:
                self.imagen = uploaded_url
            else:
                print(f"Error al subir imagen a ImgBB: {self.imagen}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_imagen


class Usuario(models.Model):
    correo = models.EmailField(unique=True)
    nombre_usuario = models.CharField(max_length=100)
    contraseña = models.CharField(max_length=128)
    foto_perfil = models.URLField()  # URL de la foto de perfil en Imgur
    esta_subscrito = models.BooleanField(default=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre_usuario

class Publicidad(models.Model):
    tipo_anuncio = models.CharField(max_length=50)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    url_destino = models.URLField()
    impresiones = models.IntegerField()
    clics = models.IntegerField()
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='publicidades')

    def __str__(self):
        return f'{self.tipo_anuncio} - {self.fecha_inicio} a {self.fecha_fin}'

# models.py
from django.db import models
from django.contrib.auth.models import User

class ReaccionNoticia(models.Model):
    TIPOS_REACCION = [
        ('interesa', 'Me interesa'),
        ('divierte', 'Me divierte'),
        ('entristece', 'Me entristece'),
        ('enoja', 'Me enoja'),
    ]
    
    noticia = models.ForeignKey('Noticia', on_delete=models.CASCADE, related_name='reacciones')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo_reaccion = models.CharField(max_length=20, choices=TIPOS_REACCION)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['noticia', 'usuario']  # Un usuario solo puede tener una reacción por noticia

# models.py
from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Generar token simple si no existe
        if not self.token:
            self.token = self.generate_token()
        
        # El token expira después de 24 horas
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
            
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at
    
    @staticmethod
    def generate_token():
        # Generar token numérico de 6 dígitos
        digits = string.digits
        token = ''.join(random.choice(digits) for _ in range(6))
        
        # Verificar que no exista ya
        while PasswordResetToken.objects.filter(token=token).exists():
            token = ''.join(random.choice(digits) for _ in range(6))
            
        return token

