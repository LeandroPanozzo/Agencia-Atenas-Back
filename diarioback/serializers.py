from rest_framework import serializers
from .models import NewsletterSubscriber, Servicio, SubcategoriaServicio, Trabajador, UserProfile, Usuario, upload_to_imgbb, Noticia, EstadoPublicacion, Imagen, Publicidad
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from rest_framework import generics
from django.urls import reverse

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo electrónico.")
        
        if Trabajador.objects.filter(correo=value).exists():
            raise serializers.ValidationError("Ya existe un trabajador con este correo electrónico.")
            
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(
            username=data.get('username'),
            password=data.get('password')
        )
        if user is None:
            raise serializers.ValidationError('Invalid credentials')
        return {'user': user}


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'


class EstadoPublicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoPublicacion
        fields = '__all__'


class ImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imagen
        fields = '__all__'


class PublicidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publicidad
        fields = '__all__'


class TrabajadorSerializer(serializers.ModelSerializer):
    foto_perfil_local = serializers.ImageField(write_only=True, required=False)
    foto_perfil = serializers.URLField(read_only=True)
    descripcion_usuario = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Trabajador
        fields = ['id', 'nombre', 'apellido', 'foto_perfil', 'foto_perfil_local', 'descripcion_usuario']

    def create(self, validated_data):
        foto_perfil_local = validated_data.pop('foto_perfil_local', None)
        trabajador = Trabajador.objects.create(**validated_data)

        if foto_perfil_local:
            imgbb_url = upload_to_imgbb(foto_perfil_local)
            if imgbb_url:
                trabajador.foto_perfil = imgbb_url
                trabajador.save()
            else:
                print("Error al subir imagen de perfil a ImgBB")

        return trabajador

    def update(self, instance, validated_data):
        foto_perfil_local = validated_data.pop('foto_perfil_local', None)

        for field in ['nombre', 'apellido']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if 'descripcion_usuario' in validated_data:
            instance.descripcion_usuario = validated_data['descripcion_usuario']

        if foto_perfil_local:
            imgbb_url = upload_to_imgbb(foto_perfil_local)
            if imgbb_url:
                instance.foto_perfil = imgbb_url
            else:
                print("Error al subir imagen de perfil a ImgBB")

        instance.save()
        return instance


from django.conf import settings

class UserProfileSerializer(serializers.ModelSerializer):
    foto_perfil_local = serializers.ImageField(write_only=True, required=False)
    foto_perfil = serializers.CharField(required=False, allow_blank=True)
    descripcion_usuario = serializers.CharField(required=False, allow_blank=True)
    es_trabajador = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'nombre', 'apellido', 'foto_perfil', 'foto_perfil_local', 'descripcion_usuario', 'es_trabajador']

    def validate_foto_perfil(self, value):
        if value and value.startswith(settings.MEDIA_URL):
            return value
        elif value and value.startswith('/'):
            return f"{settings.MEDIA_URL.rstrip('/')}{value}"
        elif value and value.startswith('http'):
            return value
        return value

    def update(self, instance, validated_data):
        foto_perfil_local = validated_data.pop('foto_perfil_local', None)
        
        if not instance.es_trabajador:
            foto_perfil = validated_data.get('foto_perfil', '')

            if foto_perfil_local:
                imgbb_url = upload_to_imgbb(foto_perfil_local)
                if imgbb_url:
                    instance.foto_perfil = imgbb_url
                else:
                    print("Error al subir imagen de perfil a ImgBB")

            return super().update(instance, validated_data)
        
        return super().update(instance, validated_data)


class NoticiaSerializer(serializers.ModelSerializer):
    autor = serializers.PrimaryKeyRelatedField(queryset=Trabajador.objects.all())
    editores_en_jefe = serializers.PrimaryKeyRelatedField(
        queryset=Trabajador.objects.all(),
        required=False,
        many=True
    )
    estado = serializers.PrimaryKeyRelatedField(queryset=EstadoPublicacion.objects.all())
    
    url = serializers.SerializerMethodField(read_only=True)
    slug = serializers.CharField(read_only=True)
    imagen_1 = serializers.URLField(allow_blank=True, required=False, allow_null=True)
    imagen_2 = serializers.URLField(allow_blank=True, required=False, allow_null=True)
    imagen_3 = serializers.URLField(allow_blank=True, required=False, allow_null=True)
    imagen_4 = serializers.URLField(allow_blank=True, required=False, allow_null=True)
    imagen_5 = serializers.URLField(allow_blank=True, required=False, allow_null=True)
    imagen_6 = serializers.URLField(allow_blank=True, required=False, allow_null=True)

    autorData = serializers.SerializerMethodField(read_only=True)
    editoresData = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Noticia
        fields = [
            'id', 'autor', 'editores_en_jefe', 'nombre_noticia', 'subtitulo', 
            'fecha_publicacion', 'Palabras_clave', 
            'imagen_1', 'imagen_2', 'imagen_3', 
            'imagen_4', 'imagen_5', 'imagen_6', 
            'estado', 'solo_para_subscriptores', 
            'contenido', 'mostrar_creditos',
            'autorData', 'editoresData', 'url', 'slug'
        ]

    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_autorData(self, obj):
        if not obj.mostrar_creditos:
            return None
        
        if hasattr(self.context.get('request'), 'query_params'):
            include_autor = self.context.get('request').query_params.get('include_autor')
            if include_autor and include_autor.lower() == 'true':
                if obj.autor:
                    return {
                        'id': obj.autor.id,
                        'nombre': obj.autor.nombre,
                        'apellido': obj.autor.apellido,
                        'cargo': getattr(obj.autor, 'cargo', None),
                    }
        return None
        
    def get_editoresData(self, obj):
        if not obj.mostrar_creditos:
            return None
        
        if hasattr(self.context.get('request'), 'query_params'):
            include_editor = self.context.get('request').query_params.get('include_editor')
            if include_editor and include_editor.lower() == 'true':
                return [{
                    'id': editor.id,
                    'nombre': editor.nombre,
                    'apellido': editor.apellido,
                    'cargo': getattr(editor, 'cargo', None),
                } for editor in obj.editores_en_jefe.all()]
        return None

    def validate(self, data):
        print("=== VALIDANDO DATOS ===")
        print("Datos recibidos:", data)
        
        if 'autor' in data:
            try:
                autor = Trabajador.objects.get(pk=data['autor'].id if hasattr(data['autor'], 'id') else data['autor'])
                print(f"Autor válido: {autor.nombre} {autor.apellido}")
            except Trabajador.DoesNotExist:
                raise serializers.ValidationError({'autor': 'El autor especificado no existe'})
        
        if 'estado' in data:
            try:
                estado = EstadoPublicacion.objects.get(pk=data['estado'].id if hasattr(data['estado'], 'id') else data['estado'])
                print(f"Estado válido: {estado.nombre_estado}")
            except EstadoPublicacion.DoesNotExist:
                raise serializers.ValidationError({'estado': 'El estado especificado no existe'})
        
        return data

    def create(self, validated_data):
        print("=== CREANDO NOTICIA ===")
        print("Validated data:", validated_data)
        
        editores_en_jefe = validated_data.pop('editores_en_jefe', [])
        
        noticia = Noticia.objects.create(**validated_data)
        print(f"Noticia creada con ID: {noticia.id}")
        
        if editores_en_jefe:
            noticia.editores_en_jefe.set(editores_en_jefe)
            print(f"Editores asignados: {len(editores_en_jefe)}")
        
        return noticia

    def update(self, instance, validated_data):
        print("=== ACTUALIZANDO NOTICIA ===")
        print("Validated data:", validated_data)
        
        editores = validated_data.pop('editores_en_jefe', None)

        fields_to_update = [
            'nombre_noticia', 'fecha_publicacion', 
            'Palabras_clave', 'subtitulo', 'solo_para_subscriptores', 
            'contenido', 'estado', 
            'autor', 'mostrar_creditos'
        ]
        for field in fields_to_update:
            if field in validated_data:
                setattr(instance, field, validated_data.get(field, getattr(instance, field)))

        for i in range(1, 7):
            field_name = f'imagen_{i}'
            if field_name in validated_data:
                setattr(instance, field_name, validated_data[field_name])
        
        if editores is not None:
            instance.editores_en_jefe.clear()
            instance.editores_en_jefe.add(*editores)
        
        instance.save()
        print(f"Noticia actualizada: ID {instance.id}")
        
        return instance


from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PasswordResetToken

User = get_user_model()

class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No existe un usuario con este correo electrónico.")
        return value


class VerifyTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=6)
    
    def validate_token(self, value):
        token_obj = PasswordResetToken.objects.filter(token=value).first()
        if not token_obj or not token_obj.is_valid():
            raise serializers.ValidationError("Token inválido o expirado.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=6)
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        
        token_obj = PasswordResetToken.objects.filter(token=data['token']).first()
        if not token_obj or not token_obj.is_valid():
            raise serializers.ValidationError("Token inválido o expirado.")
        
        return data
    

class SubcategoriaServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubcategoriaServicio
        fields = ['id', 'nombre']


class ServicioSerializer(serializers.ModelSerializer):
    imagen_local = serializers.ImageField(write_only=True, required=False)
    url = serializers.SerializerMethodField(read_only=True)
    slug = serializers.CharField(read_only=True)
    
    subcategoria = serializers.PrimaryKeyRelatedField(
        queryset=SubcategoriaServicio.objects.all(),
        required=False,
        allow_null=True
    )
    subcategoriaData = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Servicio
        fields = [
            'id',
            'titulo',
            'imagen',
            'imagen_local',
            'descripcion',
            'palabras_clave',
            'subcategoria',
            'subcategoriaData',
            'fecha_creacion',
            'fecha_actualizacion',
            'activo',
            'slug',
            'url'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion', 'slug', 'url']

    def get_url(self, obj):
        return obj.get_absolute_url()
    
    def get_subcategoriaData(self, obj):
        if obj.subcategoria:
            return {
                'id': obj.subcategoria.id,
                'nombre': obj.subcategoria.nombre,
                'display_nombre': obj.subcategoria.get_nombre_display()
            }
        return None

    def validate_subcategoria(self, value):
        if value is None:
            return SubcategoriaServicio.get_consultoria_estrategica()
        
        if isinstance(value, SubcategoriaServicio):
            return value
        
        if isinstance(value, int):
            try:
                return SubcategoriaServicio.obtener_o_crear_subcategoria(value)
            except Exception as e:
                raise serializers.ValidationError(f"Error al procesar subcategoría: {str(e)}")
        
        return value

    def create(self, validated_data):
        imagen_local = validated_data.pop('imagen_local', None)
        
        if 'subcategoria' not in validated_data or validated_data['subcategoria'] is None:
            validated_data['subcategoria'] = SubcategoriaServicio.get_consultoria_estrategica()
        
        servicio = Servicio.objects.create(**validated_data)
        
        if imagen_local:
            imgbb_url = upload_to_imgbb(imagen_local)
            if imgbb_url:
                servicio.imagen = imgbb_url
                servicio.save()
        
        return servicio

    def update(self, instance, validated_data):
        imagen_local = validated_data.pop('imagen_local', None)
        
        if 'subcategoria' in validated_data:
            subcategoria = validated_data['subcategoria']
            if isinstance(subcategoria, int):
                validated_data['subcategoria'] = SubcategoriaServicio.obtener_o_crear_subcategoria(subcategoria)
        
        for field in ['titulo', 'descripcion', 'palabras_clave', 'activo', 'subcategoria']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        if imagen_local:
            imgbb_url = upload_to_imgbb(imagen_local)
            if imgbb_url:
                instance.imagen = imgbb_url
        elif 'imagen' in validated_data:
            instance.imagen = validated_data['imagen']
        
        instance.save()
        return instance
    

class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'nombre', 'fecha_suscripcion', 'activo', 'confirmado']
        read_only_fields = ['fecha_suscripcion', 'confirmado']

# Agregar al final de serializers.py

from .models import Contacto

class ContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacto
        fields = [
            'id',
            'nombre',
            'email',
            'asunto',
            'mensaje',
            'fecha_envio',
            'leido',
            'respondido'
        ]
        read_only_fields = ['fecha_envio', 'leido', 'respondido']
    
    def validate_email(self, value):
        """Validar formato de email"""
        if not value or '@' not in value:
            raise serializers.ValidationError("Email inválido")
        return value
    
    def validate_mensaje(self, value):
        """Validar que el mensaje no esté vacío"""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("El mensaje debe tener al menos 10 caracteres")
        return value