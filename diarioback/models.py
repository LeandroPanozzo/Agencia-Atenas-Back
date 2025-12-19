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


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=True, blank=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    foto_perfil = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    descripcion_usuario = models.TextField(blank=True, null=True)
    es_trabajador = models.BooleanField(default=False)


class Trabajador(models.Model):
    DEFAULT_FOTO_PERFIL_URL = 'https://i.ibb.co/default-profile.png'
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    id = models.AutoField(primary_key=True)
    correo = models.EmailField(unique=False)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    foto_perfil = models.URLField(blank=True, null=True)
    foto_perfil_local = models.ImageField(upload_to='perfil/', blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # ELIMINADO: rol = models.ForeignKey('Rol', ...)

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
        old_instance = None
        if self.pk:
            try:
                old_instance = Trabajador.objects.get(pk=self.pk)
            except Trabajador.DoesNotExist:
                pass

        if not self.user_profile:
            self.user_profile = UserProfile.objects.create(
                nombre=self.nombre,
                apellido=self.apellido
            )

        self._handle_image('foto_perfil', 'foto_perfil_local')

        if not self.foto_perfil and not self.foto_perfil_local:
            self.foto_perfil = self.DEFAULT_FOTO_PERFIL_URL

        super().save(*args, **kwargs)

    def _handle_image(self, image_field, image_local_field):
        image_local = getattr(self, image_local_field)
        image_url = getattr(self, image_field)

        if image_local and os.path.exists(image_local.path):
            uploaded_image_url = upload_to_imgbb(image_local.path)
            if uploaded_image_url:
                setattr(self, image_field, uploaded_image_url)
            else:
                setattr(self, image_field, self.DEFAULT_FOTO_PERFIL_URL)
        elif image_url:
            setattr(self, image_field, image_url)
        else:
            setattr(self, image_field, self.DEFAULT_FOTO_PERFIL_URL)

    def _delete_old_image(self, old_instance, field_name):
        old_image_url = getattr(old_instance, field_name)
        new_image_url = getattr(self, field_name)
        if old_image_url and old_image_url != new_image_url:
            print(f"Nota: No se puede eliminar automáticamente la imagen anterior de ImgBB: {old_image_url}")

    def get_foto_perfil(self):
        return self.foto_perfil_local.url if self.foto_perfil_local else self.foto_perfil or self.DEFAULT_FOTO_PERFIL_URL

    def __str__(self):
        return f'{self.nombre} {self.apellido}'


IMGBB_API_KEY = 'a315981b1bce71916fb736816e14d90a'
IMGBB_UPLOAD_URL = 'https://api.imgbb.com/1/upload'

def upload_to_imgbb(image):
    try:
        print("📤 Iniciando upload_to_imgbb...")
        
        # Manejar diferentes tipos de entrada
        if isinstance(image, InMemoryUploadedFile):
            image_data = image.read()
            print("📤 Tipo: InMemoryUploadedFile")
        elif isinstance(image, str) and os.path.isfile(image):
            with open(image, 'rb') as image_file:
                image_data = image_file.read()
            print("📤 Tipo: File path")
        elif hasattr(image, 'path') and os.path.isfile(image.path):
            with open(image.path, 'rb') as image_file:
                image_data = image_file.read()
            print("📤 Tipo: Django File with path")
        else:
            image_data = image.read() if hasattr(image, 'read') else image
            print("📤 Tipo: Unknown/Other")
        
        print(f"📤 Tamaño datos: {len(image_data)} bytes")
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        print(f"📤 Base64 length: {len(image_base64)}")
        
        data = {
            'key': IMGBB_API_KEY,
            'image': image_base64,
            'expiration': 0
        }
        
        print("📤 Enviando a ImgBB API...")
        response = requests.post(IMGBB_UPLOAD_URL, data=data, timeout=30)
        
        print(f"📤 Respuesta ImgBB: {response.status_code}")
        
        if response.status_code == 429:
            print("⚠️ Error 429: Demasiadas solicitudes, esperando antes de reintentar...")
            time.sleep(60)
            return upload_to_imgbb(image)
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"📤 ImgBB response data: {response_data}")
            
            if response_data.get('success'):
                url = response_data['data']['url']
                print(f"✅ URL obtenida: {url}")
                return url
            else:
                error_msg = response_data.get('error', {}).get('message', 'Error desconocido')
                print(f"❌ Error ImgBB: {error_msg}")
        else:
            print(f"❌ Error HTTP {response.status_code} al subir imagen a ImgBB")
            print(f"❌ Respuesta: {response.text}")
        
    except Exception as e:
        print(f"❌ Excepción en upload_to_imgbb: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return None

def delete_from_imgbb(image_url):
    print(f"Advertencia: ImgBB no soporta eliminación de imágenes vía API pública")
    print(f"La imagen {image_url} no se puede eliminar automáticamente")
    return False

def get_imgbb_image_info(image_url):
    try:
        if 'ibb.co' in image_url:
            parts = image_url.split('/')
            if len(parts) >= 4:
                image_id = parts[4]
                
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


from django.utils.text import slugify

# En models.py - Actualiza la clase Noticia

class Noticia(models.Model):
    autor = models.ForeignKey(
        'Trabajador', 
        on_delete=models.CASCADE, 
        related_name='noticias', 
        null=False,
        db_index=True  # ÍNDICE para filtros rápidos
    )
    editores_en_jefe = models.ManyToManyField(
        'Trabajador', 
        related_name='noticias_supervisadas',
        blank=True,
        verbose_name="Editores en jefe"
    )
    nombre_noticia = models.CharField(max_length=500, db_index=True)  # ÍNDICE
    fecha_publicacion = models.DateField(db_index=True)  # ÍNDICE
    url = models.URLField(max_length=200, blank=True, null=True)
    slug = models.SlugField(max_length=300, unique=True, blank=True, editable=False)
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
    estado = models.ForeignKey(
        'EstadoPublicacion', 
        on_delete=models.SET_NULL, 
        null=True,
        db_index=True  # ÍNDICE para filtros rápidos
    )
    solo_para_subscriptores = models.BooleanField(default=False)
    contenido = models.TextField(default='default content')
    subtitulo = models.TextField(default='default content')
    mostrar_creditos = models.BooleanField(
        default=True, 
        help_text="Si está marcado, se mostrarán los datos del autor y editores de la noticia"
    )

    class Meta:
        ordering = ['-fecha_publicacion']
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
        
        # OPTIMIZACIÓN: Índices compuestos para consultas comunes
        indexes = [
            # Índice para filtros de estado + fecha (consulta más común)
            models.Index(fields=['estado', '-fecha_publicacion'], name='noticia_estado_fecha_idx'),
            # Índice para filtros de autor + fecha
            models.Index(fields=['autor', '-fecha_publicacion'], name='noticia_autor_fecha_idx'),
            # Índice para búsquedas por título
            models.Index(fields=['nombre_noticia'], name='noticia_titulo_idx'),
            # Índice compuesto para estado publicado + fecha
            models.Index(fields=['estado', '-fecha_publicacion', 'mostrar_creditos'], name='noticia_pub_idx'),
        ]

    def save(self, *args, **kwargs):
        # OPTIMIZACIÓN: Evitar consultas innecesarias
        is_new = self._state.adding
        
        if not is_new:
            try:
                old_instance = Noticia.objects.only('nombre_noticia', 'slug').get(pk=self.pk)
                if old_instance.nombre_noticia != self.nombre_noticia:
                    self.slug = slugify(self.nombre_noticia)
                    original_slug = self.slug
                    count = 1
                    while Noticia.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                        self.slug = f"{original_slug}-{count}"
                        count += 1
            except Noticia.DoesNotExist:
                pass
        else:
            self.slug = slugify(self.nombre_noticia)
            original_slug = self.slug
            count = 1
            while Noticia.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1

        super().save(*args, **kwargs)
        
        # Procesar imágenes después de guardar
        if is_new or any(getattr(self, f'imagen_{i}_local') for i in range(1, 7)):
            images_updated = self._process_images()
            if images_updated:
                # OPTIMIZACIÓN: Guardar solo campos de imagen
                update_fields = [f'imagen_{i}' for i in range(1, 7)] + [f'imagen_{i}_local' for i in range(1, 7)]
                super().save(update_fields=update_fields)
    
    def _process_images(self):
        """Procesar imágenes de forma optimizada"""
        images_updated = False
        
        for i in range(1, 7):
            local_field_name = f'imagen_{i}_local'
            url_field_name = f'imagen_{i}'
            
            local_field = getattr(self, local_field_name)
            if local_field and hasattr(local_field, 'file'):
                imgbb_url = upload_to_imgbb(local_field)
                if imgbb_url:
                    setattr(self, url_field_name, imgbb_url)
                    setattr(self, local_field_name, None)
                    images_updated = True
        
        return images_updated

    def __str__(self):
        return f'{self.nombre_noticia} - {self.estado}'

    def get_absolute_url(self):
        return f'/noticias/{self.pk}-{self.slug}/'

    def get_image_urls(self):
        """Método optimizado para obtener URLs de imágenes"""
        return [getattr(self, f'imagen_{i}') for i in range(1, 7) if getattr(self, f'imagen_{i}')]


class EstadoPublicacion(models.Model):
    """
    Estados fijos para las publicaciones.
    IDs fijos:
    1 = Borrador
    2 = En Papelera  
    3 = Publicado
    4 = Listo para editar
    """
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
    
    ID_BORRADOR = 1
    ID_EN_PAPELERA = 2
    ID_PUBLICADO = 3
    ID_LISTO_PARA_EDITAR = 4
    
    ESTADO_MAP = {
        1: BORRADOR,
        2: EN_PAPELERA,
        3: PUBLICADO,
        4: LISTO_PARA_EDITAR,
    }

    nombre_estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=BORRADOR,
    )

    def __str__(self):
        return self.get_nombre_estado_display()
    
    @classmethod
    def obtener_o_crear_estado(cls, estado_id):
        if estado_id not in cls.ESTADO_MAP:
            estado_id = cls.ID_BORRADOR
        
        estado_obj, created = cls.objects.get_or_create(
            id=estado_id,
            defaults={'nombre_estado': cls.ESTADO_MAP[estado_id]}
        )
        
        if created:
            print(f"✅ Estado {estado_id} creado automáticamente: {estado_obj.nombre_estado}")
        
        return estado_obj


class Imagen(models.Model):
    nombre_imagen = models.CharField(max_length=100)
    imagen = models.URLField(null=True, blank=True)
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='imagenes')

    def save(self, *args, **kwargs):
        if self.imagen and not self.imagen.startswith(('http://', 'https://')):
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
    foto_perfil = models.URLField()
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


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
            
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at
    
    @staticmethod
    def generate_token():
        import random
        import string
        
        digits = string.digits
        token = ''.join(random.choice(digits) for _ in range(6))
        
        while PasswordResetToken.objects.filter(token=token).exists():
            token = ''.join(random.choice(digits) for _ in range(6))
            
        return token


# En models.py - Actualiza la clase SubcategoriaServicio

class SubcategoriaServicio(models.Model):
    """
    Subcategorías fijas para los servicios.
    IDs fijos actualizados con los 5 nuevos servicios:
    1 = Estrategias y reportes de impacto
    2 = Asuntos corporativos y vinculación institucional
    3 = Comunicación estratégica y reputación
    4 = Análisis y datos
    5 = Informes técnicos y posicionamiento temático
    """
    ESTRATEGIAS_IMPACTO = 'estrategias_impacto'
    ASUNTOS_CORPORATIVOS = 'asuntos_corporativos'
    COMUNICACION_ESTRATEGICA = 'comunicacion_estrategica'
    ANALISIS_DATOS = 'analisis_datos'
    INFORMES_TECNICOS = 'informes_tecnicos'
    
    SUBCATEGORIA_CHOICES = [
        (ESTRATEGIAS_IMPACTO, 'Estrategias y reportes de impacto'),
        (ASUNTOS_CORPORATIVOS, 'Asuntos corporativos y vinculación institucional'),
        (COMUNICACION_ESTRATEGICA, 'Comunicación estratégica y reputación'),
        (ANALISIS_DATOS, 'Análisis y datos'),
        (INFORMES_TECNICOS, 'Informes técnicos y posicionamiento temático'),
    ]
    
    ID_ESTRATEGIAS = 1
    ID_ASUNTOS = 2
    ID_COMUNICACION = 3
    ID_ANALISIS = 4
    ID_INFORMES = 5
    
    SUBCATEGORIA_MAP = {
        ID_ESTRATEGIAS: ESTRATEGIAS_IMPACTO,
        ID_ASUNTOS: ASUNTOS_CORPORATIVOS,
        ID_COMUNICACION: COMUNICACION_ESTRATEGICA,
        ID_ANALISIS: ANALISIS_DATOS,
        ID_INFORMES: INFORMES_TECNICOS,
    }

    nombre = models.CharField(
        max_length=50,
        choices=SUBCATEGORIA_CHOICES,
        unique=True,
        default=ESTRATEGIAS_IMPACTO
    )
    
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción detallada del servicio")
    icono = models.CharField(max_length=50, blank=True, null=True, help_text="Nombre del ícono (ej: fa-chart-line)")
    
    class Meta:
        verbose_name = 'Categoría de Servicio'
        verbose_name_plural = 'Categorías de Servicios'
    
    def __str__(self):
        return self.get_nombre_display()
    
    @classmethod
    def obtener_o_crear_subcategoria(cls, subcategoria_id):
        if subcategoria_id not in cls.SUBCATEGORIA_MAP:
            subcategoria_id = cls.ID_ESTRATEGIAS
        
        subcategoria_obj, created = cls.objects.get_or_create(
            id=subcategoria_id,
            defaults={'nombre': cls.SUBCATEGORIA_MAP[subcategoria_id]}
        )
        
        if created:
            print(f"✅ Categoría {subcategoria_id} creada automáticamente: {subcategoria_obj.nombre}")
        
        return subcategoria_obj
    
    @classmethod
    def get_estrategias_impacto(cls):
        return cls.obtener_o_crear_subcategoria(cls.ID_ESTRATEGIAS)
    
    @classmethod
    def get_asuntos_corporativos(cls):
        return cls.obtener_o_crear_subcategoria(cls.ID_ASUNTOS)
    
    @classmethod
    def get_comunicacion_estrategica(cls):
        return cls.obtener_o_crear_subcategoria(cls.ID_COMUNICACION)
    
    @classmethod
    def get_analisis_datos(cls):
        return cls.obtener_o_crear_subcategoria(cls.ID_ANALISIS)
    
    @classmethod
    def get_informes_tecnicos(cls):
        return cls.obtener_o_crear_subcategoria(cls.ID_INFORMES)
    
    @classmethod
    def crear_subcategorias_base(cls):
        """Crear todas las categorías base al migrar"""
        descripciones = {
            cls.ID_ESTRATEGIAS: "Planificación estratégica de comunicación e impacto social, ambiental y corporativo. Elaboración de informes, memorias de sostenibilidad y libros blancos con enfoque narrativo y visual.",
            cls.ID_ASUNTOS: "Estrategias de relacionamiento y posicionamiento institucional frente al sector público, la sociedad civil y los grupos de interés.",
            cls.ID_COMUNICACION: "Comunicación estratégica y manejo de reputación: construcción, fortalecimiento y gestión de una imagen positiva ante la opinión pública.",
            cls.ID_ANALISIS: "Estudios de mercado, análisis sectorial y benchmark comunicacional. Diseño de indicadores de comunicación e impacto.",
            cls.ID_INFORMES: "Elaboración de informes técnicos y estudios aplicados sobre temáticas de interés público, regulatorio o sectorial."
        }
        
        iconos = {
            cls.ID_ESTRATEGIAS: "fa-chart-line",
            cls.ID_ASUNTOS: "fa-handshake",
            cls.ID_COMUNICACION: "fa-bullhorn",
            cls.ID_ANALISIS: "fa-chart-bar",
            cls.ID_INFORMES: "fa-file-alt"
        }
        
        for subcategoria_id, nombre in cls.SUBCATEGORIA_MAP.items():
            subcategoria_obj, created = cls.objects.get_or_create(
                id=subcategoria_id,
                defaults={
                    'nombre': nombre,
                    'descripcion': descripciones.get(subcategoria_id, ''),
                    'icono': iconos.get(subcategoria_id, '')
                }
            )
            
            if created:
                print(f"✅ Categoría {subcategoria_id} creada: {subcategoria_obj.nombre}")
            else:
                # Actualizar descripción e icono si ya existían
                update_fields = []
                if not subcategoria_obj.descripcion and descripciones.get(subcategoria_id):
                    subcategoria_obj.descripcion = descripciones[subcategoria_id]
                    update_fields.append('descripcion')
                if not subcategoria_obj.icono and iconos.get(subcategoria_id):
                    subcategoria_obj.icono = iconos[subcategoria_id]
                    update_fields.append('icono')
                
                if update_fields:
                    subcategoria_obj.save(update_fields=update_fields)
                    print(f"🔄 Categoría {subcategoria_id} actualizada: {subcategoria_obj.nombre}")

class Servicio(models.Model):
    titulo = models.CharField(max_length=200)
    imagen = models.URLField(blank=True, null=True)
    imagen_local = models.ImageField(upload_to='servicios/', blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    palabras_clave = models.CharField(max_length=200, blank=True, null=True)
    
    subcategoria = models.ForeignKey(
        'SubcategoriaServicio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicios',
        verbose_name='Subcategoría',
        # OPTIMIZACIÓN: db_index para queries más rápidas
        db_index=True
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # OPTIMIZACIÓN: db_index en campo activo para filtros rápidos
    activo = models.BooleanField(default=True, db_index=True)
    slug = models.SlugField(max_length=250, unique=True, blank=True, editable=False)

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['-fecha_creacion']
        
        # OPTIMIZACIÓN: Índices compuestos para consultas comunes
        indexes = [
            # Índice para filtros de activo + subcategoría (consulta más común)
            models.Index(fields=['activo', 'subcategoria'], name='servicio_activo_sub_idx'),
            # Índice para ordenamiento por fecha
            models.Index(fields=['-fecha_creacion'], name='servicio_fecha_idx'),
            # Índice para búsquedas por slug
            models.Index(fields=['slug'], name='servicio_slug_idx'),
        ]

    def save(self, *args, **kwargs):
        """Save optimizado"""
        if not self.subcategoria_id:
            self.subcategoria = SubcategoriaServicio.get_consultoria_estrategica()
        
        if not self.slug or self.pk:
            self.slug = slugify(self.titulo)
            original_slug = self.slug
            count = 1
            while Servicio.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1

        super().save(*args, **kwargs)

        # OPTIMIZACIÓN: Procesar imagen solo si es necesario
        if self.imagen_local and hasattr(self.imagen_local, 'file'):
            imgbb_url = upload_to_imgbb(self.imagen_local)
            if imgbb_url:
                self.imagen = imgbb_url
                self.imagen_local = None
                # Guardar solo campos específicos
                super().save(update_fields=['imagen', 'imagen_local'])

    def get_absolute_url(self):
        return f'/servicios/{self.pk}-{self.slug}/'

    def __str__(self):
        return self.titulo
    

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    fecha_suscripcion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    token_confirmacion = models.CharField(max_length=100, unique=True, blank=True, null=True)
    confirmado = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Suscriptor Newsletter'
        verbose_name_plural = 'Suscriptores Newsletter'
        ordering = ['-fecha_suscripcion']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.token_confirmacion:
            import secrets
            self.token_confirmacion = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps

# En models.py - Actualiza la señal post_migrate

@receiver(post_migrate)
def crear_subcategorias_base(sender, **kwargs):
    if sender.name == 'diarioback':  # Reemplaza 'tu_app' con el nombre de tu aplicación
        try:
            SubcategoriaServicio = apps.get_model('diarioback', 'SubcategoriaServicio')
            SubcategoriaServicio.crear_subcategorias_base()
            print("🎯 Categorías de servicios creadas/verificadas automáticamente")
        except Exception as e:
            print(f"⚠️ Error al crear categorías base: {e}")

# En models.py - Actualiza la clase Contacto

class Contacto(models.Model):
    """
    Modelo optimizado para mensajes de contacto
    """
    nombre = models.CharField(max_length=200)
    email = models.EmailField()
    asunto = models.CharField(max_length=300)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True, db_index=True)  # ÍNDICE
    leido = models.BooleanField(default=False, db_index=True)  # ÍNDICE
    respondido = models.BooleanField(default=False, db_index=True)  # ÍNDICE
    
    class Meta:
        verbose_name = 'Mensaje de Contacto'
        verbose_name_plural = 'Mensajes de Contacto'
        ordering = ['-fecha_envio']
        
        # OPTIMIZACIÓN: Índices compuestos para consultas comunes
        indexes = [
            # Índice para filtros de leído + fecha
            models.Index(fields=['leido', '-fecha_envio'], name='contacto_leido_fecha_idx'),
            # Índice para filtros de respondido + fecha
            models.Index(fields=['respondido', '-fecha_envio'], name='contacto_resp_fecha_idx'),
            # Índice compuesto para filtros combinados
            models.Index(fields=['leido', 'respondido', '-fecha_envio'], name='contacto_estado_idx'),
        ]
    
    def __str__(self):
        return f"{self.nombre} - {self.asunto} ({self.fecha_envio.strftime('%d/%m/%Y')})"
    
    def marcar_como_leido(self):
        """Marca el mensaje como leído - OPTIMIZADO"""
        # Usar update es más rápido
        Contacto.objects.filter(pk=self.pk).update(leido=True)
        self.leido = True
    
    def marcar_como_respondido(self):
        """Marca el mensaje como respondido - OPTIMIZADO"""
        Contacto.objects.filter(pk=self.pk).update(respondido=True)
        self.respondido = True