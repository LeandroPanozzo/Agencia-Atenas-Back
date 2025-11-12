from django.apps import AppConfig


class DiariobackConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'diarioback'
    
    def ready(self):
        """
        Se ejecuta cuando la aplicación está lista.
        Crea las subcategorías base automáticamente.
        """
        try:
            from .models import SubcategoriaServicio
            SubcategoriaServicio.crear_subcategorias_base()
        except Exception as e:
            print(f"⚠️ Error al crear subcategorías base: {e}")