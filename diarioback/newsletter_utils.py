from mailjet_rest import Client
from django.conf import settings
from django.utils.html import strip_tags

def send_mailjet_email(to_email, subject, html_content, from_email=None):
    """
    Envía un email usando Mailjet
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    mailjet = Client(
        auth=(settings.MAILJET_API_KEY, settings.MAILJET_SECRET_KEY),
        version='v3.1'
    )
    
    data = {
        'Messages': [
            {
                "From": {
                    "Email": from_email,
                    "Name": "Agencia Atenas"  # Cambia esto por el nombre de tu diario
                },
                "To": [
                    {
                        "Email": to_email,
                    }
                ],
                "Subject": subject,
                "HTMLPart": html_content,
                "TextPart": strip_tags(html_content),
            }
        ]
    }
    
    try:
        result = mailjet.send.create(data=data)
        return result.status_code == 200
    except Exception as e:
        print(f"Error enviando email a {to_email}: {e}")
        return False


def send_confirmation_email(subscriber):
    """
    Envía email de confirmación de suscripción
    """
    confirmation_link = f"http://localhost:5173/newsletter/confirmar/{subscriber.token_confirmacion}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
            <h1 style="color: #333; text-align: center;">¡Bienvenido a nuestro Newsletter!</h1>
            <p style="color: #666; font-size: 16px; line-height: 1.6;">
                Gracias por suscribirte a nuestro newsletter. Para confirmar tu suscripción, 
                haz clic en el siguiente botón:
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{confirmation_link}" 
                   style="background-color: #007bff; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Confirmar Suscripción
                </a>
            </div>
            <p style="color: #999; font-size: 14px;">
                Si no solicitaste esta suscripción, puedes ignorar este email.
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_mailjet_email(
        to_email=subscriber.email,
        subject="Confirma tu suscripción al Newsletter",
        html_content=html_content
    )


def send_newsletter_notification(noticia, subscribers):
    """
    Envía notificación de nueva noticia a todos los suscriptores
    
    Args:
        noticia: Instancia del modelo Noticia
        subscribers: QuerySet de NewsletterSubscriber
    
    Returns:
        int: Número de emails enviados exitosamente
    """
    noticia_url = f"http://localhost:5173/noticias/{noticia.pk}-{noticia.slug}"
    
    # Preparar el contenido del email
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
            {f'<img src="{noticia.imagen_1}" style="width: 100%; height: auto; max-height: 400px; object-fit: cover;" alt="{noticia.nombre_noticia}">' if noticia.imagen_1 else ''}
            
            <div style="padding: 30px;">
                <h1 style="color: #333; margin-bottom: 15px; font-size: 24px;">{noticia.nombre_noticia}</h1>
                <p style="color: #666; font-size: 18px; margin-bottom: 20px; line-height: 1.5;">{noticia.subtitulo}</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{noticia_url}" 
                       style="background-color: #007bff; color: white; padding: 15px 40px; 
                              text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Leer Noticia Completa
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center; line-height: 1.5;">
                    Recibiste este email porque estás suscrito a nuestro newsletter.
                    <br><br>
                    <a href="http://localhost:5173/newsletter/cancelar" style="color: #007bff; text-decoration: none;">
                        Cancelar suscripción
                    </a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    success_count = 0
    failed_emails = []
    
    # Enviar a cada suscriptor
    for subscriber in subscribers:
        try:
            if send_mailjet_email(
                to_email=subscriber.email,
                subject=f"Nueva publicación: {noticia.nombre_noticia}",
                html_content=html_content
            ):
                success_count += 1
                print(f"✅ Email enviado a: {subscriber.email}")
            else:
                failed_emails.append(subscriber.email)
                print(f"❌ Error al enviar a: {subscriber.email}")
        except Exception as e:
            failed_emails.append(subscriber.email)
            print(f"❌ Excepción al enviar a {subscriber.email}: {str(e)}")
    
    # Resumen final
    total = subscribers.count()
    print(f"\n📊 RESUMEN DE ENVÍO:")
    print(f"   Total suscriptores: {total}")
    print(f"   ✅ Exitosos: {success_count}")
    print(f"   ❌ Fallidos: {len(failed_emails)}")
    
    if failed_emails:
        print(f"   📧 Emails fallidos: {', '.join(failed_emails)}")
    
    return success_count

def send_custom_newsletter(asunto, contenido, subscribers, incluir_imagen=False, imagen_url=None):
    """
    Envía un correo personalizado a los suscriptores usando Mailjet
    
    Args:
        asunto: Asunto del email
        contenido: Contenido del mensaje (texto)
        subscribers: QuerySet de NewsletterSubscriber
        incluir_imagen: Boolean para incluir imagen
        imagen_url: URL de la imagen (opcional)
    
    Returns:
        int: Número de emails enviados exitosamente
    """
    # Preparar el contenido HTML del email
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
            {f'<img src="{imagen_url}" style="width: 100%; height: auto; max-height: 400px; object-fit: cover;" alt="Imagen del correo">' if incluir_imagen and imagen_url else ''}
            
            <div style="padding: 30px;">
                <h1 style="color: #333; margin-bottom: 20px; font-size: 24px;">{asunto}</h1>
                
                <div style="color: #666; font-size: 16px; line-height: 1.6; white-space: pre-wrap;">
                    {contenido}
                </div>
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center; line-height: 1.5;">
                    Recibiste este email porque estás suscrito a nuestro newsletter.
                    <br><br>
                    <a href="http://localhost:5173/newsletter/cancelar" style="color: #007bff; text-decoration: none;">
                        Cancelar suscripción
                    </a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    success_count = 0
    failed_emails = []
    
    # Enviar a cada suscriptor
    for subscriber in subscribers:
        try:
            if send_mailjet_email(
                to_email=subscriber.email,
                subject=asunto,
                html_content=html_content
            ):
                success_count += 1
                print(f"✅ Correo personalizado enviado a: {subscriber.email}")
            else:
                failed_emails.append(subscriber.email)
                print(f"❌ Error al enviar a: {subscriber.email}")
        except Exception as e:
            failed_emails.append(subscriber.email)
            print(f"❌ Excepción al enviar a {subscriber.email}: {str(e)}")
    
    # Resumen final
    total = subscribers.count()
    print(f"\n📊 RESUMEN DE ENVÍO DE CORREO PERSONALIZADO:")
    print(f"   Total suscriptores: {total}")
    print(f"   ✅ Exitosos: {success_count}")
    print(f"   ❌ Fallidos: {len(failed_emails)}")
    
    if failed_emails:
        print(f"   📧 Emails fallidos: {', '.join(failed_emails)}")
    
    return success_count