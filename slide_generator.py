# --- Importaciones necesarias ---
import os.path
import json
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- NUEVAS LÍNEAS PARA LEER EL .env ---
from dotenv import load_dotenv
import os
load_dotenv() # Esto carga las variables del archivo .env

# --- Configuración Clave ---

# 1. EL PROJECT_ID DE GOOGLE CLOUD
TU_PROJECT_ID = os.getenv("TU_PROJECT_ID")

# 2. Permisos que solicitaremos al usuario
# Estos son los scopes correctos
SCOPES = ["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/cloud-platform"]

# 3. Archivos de credenciales
CREDENTIALS_FILE = "credentials.json"  # El JSON que descargaste de Google
TOKEN_FILE = "token.json"  # Este archivo se CREARÁ automáticamente

# 4. Configuración de la IA
# ¡¡LA SOLUCIÓN QUE TÚ ENCONTRASTE!!
# Región "global" y modelo "gemini-2.5-pro"
API_ENDPOINT = f"https://aiplatform.googleapis.com/v1/projects/{TU_PROJECT_ID}/locations/global/publishers/google/models/gemini-2.5-pro:generateContent"


class SlideGenerator:
    """
    Clase que maneja la autenticación y generación de slides.
    """

    def __init__(self):
        """
        El constructor ahora es 'ligero'. No se autentica al iniciar.
        """
        self.creds = None
        self.slides_service = None
        self.auth_headers = None
        print("SlideGenerator inicializado (sin autenticar).")

    def authenticate(self):
        """
        Maneja el flujo de autenticación OAuth 2.0 bajo demanda.
        Crea 'token.json' si no existe.
        Devuelve True si la autenticación es exitosa, False si no.
        """
        # Si ya tenemos credenciales válidas, no hacemos nada
        if self.creds and self.creds.valid:
            # Re-construir servicios si no existen (necesario si la app sigue abierta)
            if not self.auth_headers:
                self.auth_headers = {
                    "Authorization": f"Bearer {self.creds.token}",
                    "Content-Type": "application/json"
                }
            if not self.slides_service:
                 self.slides_service = build("slides", "v1", credentials=self.creds)
            return True
            
        print("Iniciando autenticación...")
        try:
            # El archivo token.json almacena los tokens de acceso y actualización.
            if os.path.exists(TOKEN_FILE):
                self.creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            
            # Si no hay credenciales (válidas) disponibles, deja que el usuario inicie sesión.
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        print("Refrescando token de acceso...")
                        self.creds.refresh(Request())
                    except Exception as e:
                        print(f"Error al refrescar el token: {e}")
                        self.creds = self._run_oauth_flow() # Forzar flujo nuevo
                else:
                    print("Iniciando flujo de autenticación por primera vez...")
                    self.creds = self._run_oauth_flow()
                
                # Guarda las credenciales para la próxima ejecución
                with open(TOKEN_FILE, "w") as token:
                    token.write(self.creds.to_json())
                    print(f"Token guardado en {TOKEN_FILE}")

            if not self.creds:
                 print("Error: No se pudieron obtener las credenciales.")
                 return False

            # --- Construir los servicios DESPUÉS de autenticar ---
            print("Construyendo servicios de Google...")
            # 1. El servicio para la API de Google Slides
            self.slides_service = build("slides", "v1", credentials=self.creds)
            
            # 2. La cabecera (header) para la API de Gemini
            self.auth_headers = {
                "Authorization": f"Bearer {self.creds.token}",
                "Content-Type": "application/json"
            }
            print("Autenticación exitosa. Servicios listos.")
            return True
            
        except HttpError as err:
            print(f"Error al construir los servicios de Google: {err}")
            return False
        except Exception as e:
            print(f"Error inesperado durante la autenticación: {e}")
            return False

    def _run_oauth_flow(self):
        """
        Ejecuta el flujo de OAuth de aplicación de escritorio.
        Abrirá una pestaña en el navegador.
        """
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"Error: No se encuentra el archivo {CREDENTIALS_FILE}")
            print("Por favor, sigue la Fase 2 de la guía para descargarlo.")
            return None
            
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        # Esto abrirá el navegador y pedirá al usuario que inicie sesión
        # y conceda permisos.
        creds = flow.run_local_server(port=0, prompt='consent')
        return creds

    def get_presentation_content(self, pdf_text):
        """
        Envía el texto extraído del PDF a la API de Gemini (Vertex AI).
        """
        if not self.auth_headers or TU_PROJECT_ID is None:
            print("Error: El PROJECT_ID no está configurado (revisa tu .env) o la autenticación falló.")
            return None

        # --- El "Prompt" para la IA ---
        # Esta es la parte más importante. Le decimos a la IA CÓMO
        # queremos la respuesta. Le pedimos formato JSON.
        prompt = f"""
        Eres un asistente experto en crear presentaciones profesionales.
        He extraído el siguiente texto de un documento PDF.
        Por favor, analiza el texto y genera un resumen optimizado para Google Slides.

        Tu respuesta DEBE ser únicamente un objeto JSON válido, con la siguiente estructura:
        {{
          "titulo_presentacion": "Un título conciso y profesional para la presentación",
          "puntos_clave": [
            {{
              "titulo_diapositiva": "Título del Punto Clave 1",
              "contenido_diapositiva": "Un párrafo (3-4 frases) explicando el punto clave 1."
            }},
            {{
              "titulo_diapositiva": "Título del Punto Clave 2",
              "contenido_diapositiva": "Un párrafo (3-4 frases) explicando el punto clave 2."
            }},
            {{
              "titulo_diapositiva": "Título del Punto Clave 3",
              "contenido_diapositiva": "Un párrafo (3-4 frases) explicando el punto clave 3."
            }}
          ]
        }}

        Asegúrate de que el JSON esté perfectamente formateado. No incluyas "```json" ni nada antes o después.
        Genera entre 3 y 5 puntos clave, dependiendo del contenido.

        --- TEXTO DEL PDF ---
        {pdf_text[:8000]}
        --- FIN DEL TEXTO ---
        """

        # Preparamos el "payload" para la API de Gemini
        payload = {
            "contents": [
                # Añadimos "role": "user" para el modelo gemini-2.5-pro
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "responseMimeType": "application/json", # ¡Le pedimos JSON directamente!
                "temperature": 0.5,
                # Aumentamos el límite de tokens para que la IA no se corte
                "maxOutputTokens": 8192
            }
        }

        print("Enviando texto a la IA para análisis (Vertex AI)...")
        
        try:
            # Hacemos la llamada POST a la API de Vertex AI
            response = requests.post(API_ENDPOINT, headers=self.auth_headers, json=payload, timeout=90)
            
            # Manejar errores de la API
            if response.status_code != 200:
                print(f"Error de la API de IA (Código: {response.status_code}): {response.text}")
                return None

            response_json = response.json()
            
            # Extraer el contenido JSON generado
            # La estructura de respuesta de Gemini es un poco anidada
            if "candidates" in response_json and len(response_json["candidates"]) > 0:
                generated_content = response_json["candidates"][0]["content"]["parts"][0]["text"]
                
                # Convertir la *cadena* JSON generada en un *objeto* Python
                print("Análisis de IA recibido. Decodificando JSON...")
                return json.loads(generated_content)
            else:
                print("La respuesta de la IA no tuvo el formato esperado.")
                print(response_json)
                return None

        except requests.exceptions.RequestException as e:
            print(f"Error de conexión al llamar a la API de IA: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error al decodificar la respuesta JSON de la IA: {e}")
            print(f"Respuesta recibida: {generated_content}")
            return None
        except Exception as e:
            print(f"Error inesperado en _get_ai_summary: {e}")
            return None


    def create_presentation(self, ai_data):
        """
        Usa la API de Google Slides para crear la presentación
        basada en los datos estructurados de la IA.
        """
        if not self.slides_service:
            print("Error: El servicio de Google Slides no está inicializado.")
            return None

        try:
            # 1. Crear la presentación en blanco
            print(f"Creando nueva presentación titulada: {ai_data['titulo_presentacion']}")
            presentation = self.slides_service.presentations().create(
                body={"title": ai_data["titulo_presentacion"]}
            ).execute()

            presentation_id = presentation.get("presentationId")
            presentation_url = presentation.get("presentationUrl")
            print(f"Presentación creada con ID: {presentation_id}")

            # 2. Preparar la lista de "requests" para la API
            # La API de Slides funciona por lotes (batch)
            requests_batch = []

            # 3. Crear la diapositiva de Título
            title_slide_id = "title_slide_01"
            requests_batch.append({
                "createSlide": {
                    "objectId": title_slide_id,
                    "slideLayoutReference": {
                        "predefinedLayout": "TITLE_SLIDE"
                    },
                    # --- ¡¡AQUÍ ESTÁ LA CORRECCIÓN!! ---
                    # El layout TITLE_SLIDE requiere mapear AMBOS placeholders
                    # (el título y el subtítulo) aunque no usemos el subtítulo.
                    "placeholderIdMappings": [
                        {"layoutPlaceholder": {"type": "CENTERED_TITLE"}, "objectId": "title_slide_title"},
                        {"layoutPlaceholder": {"type": "SUBTITLE"}, "objectId": "title_slide_subtitle"}
                    ]
                }
            })
            # Insertar el texto del título
            requests_batch.append({
                "insertText": {
                    "objectId": "title_slide_title",
                    "text": ai_data["titulo_presentacion"]
                }
            })
            # (No insertamos texto en "title_slide_subtitle", pero ya está mapeado)

            # 4. Iterar y crear las diapositivas de Puntos Clave
            slide_count = 1
            for punto in ai_data["puntos_clave"]:
                slide_id = f"content_slide_{slide_count:02d}"
                title_placeholder_id = f"title_placeholder_{slide_count:02d}"
                body_placeholder_id = f"body_placeholder_{slide_count:02d}"
                
                # Crear la diapositiva (layout "TITLE_AND_BODY")
                requests_batch.append({
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {
                            "predefinedLayout": "TITLE_AND_BODY"
                        },
                        "placeholderIdMappings": [
                            {"layoutPlaceholder": {"type": "TITLE"}, "objectId": title_placeholder_id},
                            {"layoutPlaceholder": {"type": "BODY"}, "objectId": body_placeholder_id},
                        ]
                    }
                })
                # Insertar el título de la diapositiva
                requests_batch.append({
                    "insertText": {
                        "objectId": title_placeholder_id,
                        "text": punto["titulo_diapositiva"]
                    }
                })
                # Insertar el contenido de la diapositiva
                requests_batch.append({
                    "insertText": {
                        "objectId": body_placeholder_id,
                        "text": punto["contenido_diapositiva"]
                    }
                })
                slide_count += 1
            
            # 5. Borrar la diapositiva en blanco inicial (creada por defecto)
            # La primera diapositiva por defecto se llama 'p'
            requests_batch.append({
                "deleteObject": {
                    "objectId": "p" 
                }
            })

            # 6. Ejecutar todas las peticiones en un solo lote
            print(f"Enviando {len(requests_batch)} peticiones en lote a Google Slides...")
            self.slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": requests_batch}
            ).execute()

            print("¡Presentación creada exitosamente!")
            # Devolvemos el objeto 'presentation' completo
            return presentation

        except HttpError as err:
            print(f"Error al crear las diapositivas (HttpError): {err}")
            return None
        except Exception as e:
            print(f"Error inesperado en _create_slides: {e}")
            return None

# --- Fin de la clase SlideGenerator ---