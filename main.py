import app_ui
import customtkinter as ctk

# Configuración inicial de la apariencia
# Modos: "System" (default), "Dark", "Light"
ctk.set_appearance_mode("Dark")
# Temas de color: "blue" (default), "dark-blue", "green"
# Usamos 'blue' como base, pero nuestros colores morados
# definidos en app_ui.py sobreescribirán los botones.
ctk.set_default_color_theme("blue")


if __name__ == "__main__":
    try:
        # Instanciamos nuestra clase principal de la interfaz
        app = app_ui.AppUI()
        app.mainloop()
    except ImportError as e:
        print(f"Error: Faltan dependencias. ¿Ejecutaste 'pip install -r requirements.txt'?\nDetalle: {e}")
    except Exception as e:
        print(f"Se produjo un error inesperado al iniciar la aplicación: {e}")