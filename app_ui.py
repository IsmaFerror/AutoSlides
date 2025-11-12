import customtkinter as ctk
# tkinterdnd2-universal es la biblioteca que permite "arrastrar y soltar"
from tkinterdnd2 import DND_FILES, TkinterDnD
import tkinter as tk
from tkinter import filedialog
import os
import threading  # ¡Importante para no congelar la UI!
import webbrowser # Para abrir la presentación en el navegador

# Importamos nuestras clases de lógica
from pdf_processor import PDFProcessor
from slide_generator import SlideGenerator

# --- Nuestra paleta de colores personalizada ---
COLOR_PRINCIPAL_OSCURO = "#0B0B0B" # Casi negro para el fondo
COLOR_SECUNDARIO_OSCURO = "#1A1A1A" # Un poco más claro para widgets
COLOR_BORDE = "#2A2A2A"
COLOR_TEXTO = "#E0E0E0"
COLOR_ACENTO_MORADO = "#8E44AD"        # Morado principal
COLOR_ACENTO_MORADO_HOVER = "#9B59B6" # Morado más claro al pasar el ratón

# Para que CustomTkinter funcione con TkinterDnD, necesitamos esta clase "envoltorio".
# Fuente: https://github.com/TomSchimansky/CustomTkinter/wiki/Drag-and-Drop
class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

# --- ESTA ES LA LÍNEA CORREGIDA (Línea 29) ---
class AppUI(CTkDnD):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- Configuración de la Ventana Principal ---
        self.title("AutoSlides")
        self.geometry("700x500")
        self.configure(fg_color=COLOR_PRINCIPAL_OSCURO)
        self.minsize(600, 450)

        # Hacemos que el frame principal se expanda
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Inicialización de Clases de Lógica ---
        # Ahora esto es súper rápido, no se autentica
        self.pdf_processor = PDFProcessor()
        self.slide_generator = SlideGenerator()
        
        self.processing_thread = None
        self.archivo_pdf = None

        # --- Creación de Widgets ---
        
        # Frame principal que centra todo
        self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_PRINCIPAL_OSCURO)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. Título
        self.title_label = ctk.CTkLabel(self.main_frame, text="AutoSlides", 
                                        font=ctk.CTkFont(size=36, weight="bold"),
                                        text_color=COLOR_TEXTO)
        self.title_label.grid(row=0, column=0, pady=(0, 10))

        # 2. Subtítulo
        self.subtitle_label = ctk.CTkLabel(self.main_frame, 
                                           text="Arrastra un PDF para convertirlo en una presentación",
                                           font=ctk.CTkFont(size=16),
                                           text_color=COLOR_TEXTO)
        self.subtitle_label.grid(row=1, column=0, pady=(0, 25))

        # 3. Zona de Drag and Drop
        self.drop_zone = ctk.CTkFrame(self.main_frame, 
                                      fg_color=COLOR_SECUNDARIO_OSCURO,
                                      border_color=COLOR_BORDE,
                                      border_width=2,
                                      corner_radius=10)
        self.drop_zone.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        
        self.drop_zone.grid_rowconfigure(0, weight=1)
        self.drop_zone.grid_columnconfigure(0, weight=1)

        # Contenido de la zona de drop (centrado)
        self.drop_content_frame = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        self.drop_content_frame.place(relx=0.5, rely=0.5, anchor="center")

        # (Icono simple usando texto/emoji)
        self.drop_icon = ctk.CTkLabel(self.drop_content_frame, text="📄", 
                                      font=ctk.CTkFont(size=50),
                                      text_color=COLOR_TEXTO)
        self.drop_icon.pack()

        self.drop_label = ctk.CTkLabel(self.drop_content_frame, 
                                       text="Arrastra y suelta tu archivo PDF aquí",
                                       font=ctk.CTkFont(size=14),
                                       text_color=COLOR_TEXTO)
        self.drop_label.pack(pady=5)
        
        # 4. Botón de Examinar (alternativa al drag-drop)
        self.browse_button = ctk.CTkButton(
            self.main_frame,
            text="o Examina tu equipo...",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent", # Botón "fantasma"
            border_color=COLOR_ACENTO_MORADO,
            text_color=COLOR_ACENTO_MORADO,
            hover_color=COLOR_SECUNDARIO_OSCURO, # Sombra morada al pasar
            border_width=2,
            command=self.on_browse_click
        )
        self.browse_button.grid(row=3, column=0, pady=(0, 20), ipadx=10, ipady=5)

        # 5. Botón de Generar (inicialmente deshabilitado)
        self.generate_button = ctk.CTkButton(
            self.main_frame,
            text="Generar Presentación",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLOR_ACENTO_MORADO,
            text_color="#FFFFFF",
            hover_color=COLOR_ACENTO_MORADO_HOVER,
            corner_radius=8,
            state="disabled", # Deshabilitado hasta que se cargue un PDF
            command=self.iniciar_procesamiento
        )
        self.generate_button.grid(row=4, column=0, pady=(0, 20), ipady=10, ipadx=20)
        
        # 6. Barra de Estado (fuera del main_frame, pegada abajo)
        self.status_bar = ctk.CTkLabel(self, text="  Esperando archivo...", 
                                       font=ctk.CTkFont(size=12),
                                       text_color=COLOR_TEXTO,
                                       fg_color=COLOR_SECUNDARIO_OSCURO,
                                       height=30,
                                       anchor="w") # Texto alineado a la izquierda
        self.status_bar.grid(row=1, column=0, sticky="sew")


        # --- Configuración de Drag and Drop ---
        # Habilitamos la zona de drop para recibir archivos
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self.on_drop)
        # Habilitamos la ventana entera también (por si fallan)
        self.drop_target_register(DND_FILES) 
        self.dnd_bind('<<Drop>>', self.on_drop)

    # --- Métodos de la Interfaz ---

    def on_browse_click(self):
        """Maneja el clic en el botón 'Examinar'."""
        if self.processing_thread and self.processing_thread.is_alive():
            return # No hacer nada si está procesando

        path = filedialog.askopenfilename(
            title="Selecciona un archivo PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if path:
            self.manejar_archivo_seleccionado(path)

    def on_drop(self, event):
        """Maneja el evento de soltar un archivo."""
        if self.processing_thread and self.processing_thread.is_alive():
            return # No hacer nada si está procesando

        # El evento.data contiene una lista de rutas de archivos
        # Nos quedamos solo con el primer archivo que sea un PDF
        try:
            # Limpiamos las llaves {} que a veces añade Windows
            archivos = self.tk.splitlist(event.data.replace("{", "").replace("}", ""))
            pdf_path = None
            for f in archivos:
                if f.lower().endswith('.pdf'):
                    pdf_path = f
                    break
            
            if pdf_path:
                self.manejar_archivo_seleccionado(pdf_path)
            else:
                self.actualizar_estado("Error: El archivo no es un PDF.", error=True)
        except Exception as e:
            self.actualizar_estado(f"Error al soltar archivo: {e}", error=True)

    def manejar_archivo_seleccionado(self, path):
        """Actualiza la UI una vez que se selecciona un PDF."""
        self.archivo_pdf = path
        filename = os.path.basename(path)
        self.drop_label.configure(text=f"Archivo: {filename}")
        self.drop_icon.configure(text="✅")
        self.generate_button.configure(state="normal") # Habilitar botón
        self.actualizar_estado(f"Archivo '{filename}' cargado. Listo para generar.")

    def actualizar_estado(self, mensaje, error=False):
        """Actualiza el texto y color de la barra de estado."""
        # Usamos 'after' para asegurarnos de que se actualiza desde el hilo principal
        def do_update():
            self.status_bar.configure(text=f"  {mensaje}")
            if error:
                self.status_bar.configure(text_color="tomato") # Rojo para errores
            else:
                self.status_bar.configure(text_color=COLOR_TEXTO)
        
        self.after(0, do_update)

    def bloquear_ui(self, bloqueado=True):
        """Bloquea o desbloquea los botones durante el procesamiento."""
        def do_update():
            estado = "disabled" if bloqueado else "normal"
            # El botón de generar siempre se deshabilita al procesar
            self.generate_button.configure(
                state="disabled", 
                text="Generando..." if bloqueado else "Generar Presentación"
            )
            
            # El botón de examinar solo se reactiva si NO hay un archivo ya cargado
            if not bloqueado and not self.archivo_pdf:
                self.browse_button.configure(state="normal")
            elif bloqueado:
                self.browse_button.configure(state="disabled")
            else:
                self.browse_button.configure(state="normal")
        
        self.after(0, do_update)


    def iniciar_procesamiento(self):
        """Inicia el hilo de procesamiento para no bloquear la UI."""
        if not self.archivo_pdf:
            self.actualizar_estado("Error: No hay ningún archivo PDF seleccionado.", error=True)
            return
        
        # Bloquear la UI
        self.bloquear_ui(bloqueado=True)

        # Creamos un hilo para ejecutar el trabajo pesado
        # Esto evita que la aplicación se "congele"
        # 'daemon=True' hace que el hilo se cierre si cerramos la app
        self.processing_thread = threading.Thread(target=self.proceso_completo, daemon=True)
        self.processing_thread.start()

    def proceso_completo(self):
        """
        El proceso real de conversión.
        ¡Se ejecuta en un hilo separado!
        """
        try:
            # --- Paso 1: Extraer Texto ---
            self.actualizar_estado("Paso 1/5: Extrayendo texto del PDF...")
            texto_pdf = self.pdf_processor.extract_text(self.archivo_pdf)
            if not texto_pdf or texto_pdf.isspace():
                self.actualizar_estado("Error: No se pudo extraer texto del PDF. ¿Está vacío o es una imagen?", error=True)
                self.bloquear_ui(bloqueado=False)
                return

            # --- Paso 2: Autenticar con Google ---
            # Esto puede abrir un navegador si es la primera vez
            self.actualizar_estado("Paso 2/5: Autenticando con Google...")
            if not self.slide_generator.authenticate():
                # El error ya se imprimió en la consola
                self.actualizar_estado(f"Error de autenticación. Revisa la terminal.", error=True)
                self.bloquear_ui(bloqueado=False)
                return

            # --- Paso 3: Generar Contenido con IA ---
            self.actualizar_estado("Paso 3/5: Generando contenido con IA (Gemini)... (Esto puede tardar)")
            contenido_json = self.slide_generator.get_presentation_content(texto_pdf)
            if not contenido_json:
                self.actualizar_estado("Error: La API de IA no devolvió contenido.", error=True)
                self.bloquear_ui(bloqueado=False)
                return

            # --- Paso 4: Crear la Presentación ---
            self.actualizar_estado("Paso 4/5: Creando presentación en Google Slides...")
            presentacion = self.slide_generator.create_presentation(contenido_json)
            if not presentacion:
                self.actualizar_estado("Error: No se pudo crear la presentación en Google Slides.", error=True)
                self.bloquear_ui(bloqueado=False)
                return
            
            url_presentacion = presentacion.get('presentationUrl')
            
            # --- Paso 5: ¡Éxito! ---
            self.actualizar_estado(f"¡Listo! Abriendo presentación...")
            print(f"Presentación disponible en: {url_presentacion}")
            
            # Abrir el enlace en el navegador
            webbrowser.open(url_presentacion)

            # Resetear la UI para el próximo archivo
            self.archivo_pdf = None
            self.after(0, lambda: self.drop_label.configure(text="Arrastra y suelta tu archivo PDF aquí"))
            self.after(0, lambda: self.drop_icon.configure(text="📄"))
            self.bloquear_ui(bloqueado=False)
            self.after(0, lambda: self.generate_button.configure(state="disabled")) # Deshabilitado

        except Exception as e:
            # Captura cualquier error inesperado
            self.actualizar_estado(f"Error en el proceso: {e}", error=True)
            print(f"Error en proceso_completo: {e}")
            import traceback
            traceback.print_exc() # Imprime el error detallado en consola
            self.bloquear_ui(bloqueado=False)