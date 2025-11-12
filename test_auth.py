# Este archivo es solo para probar que la autenticación funciona.
from slide_generator import SlideGenerator

print("--- Iniciando prueba de autenticación ---")

try:
    # 1. Intentamos crear una instancia de la clase
    # Esto DEBERÍA activar el flujo de autenticación
    # y abrir tu navegador.
    gen = SlideGenerator()

    if gen.creds:
        print("\n--- ¡Prueba exitosa! ---")
        print(f"Autenticación completada para: {gen.creds.client_id}")
        print("¡Ya podemos conectarnos a las APIs de Google!")
        print(f"Se ha creado/actualizado el archivo 'token.json'.")
    else:
        print("\n--- Prueba fallida ---")
        print("El objeto SlideGenerator no pudo autenticarse.")

except Exception as e:
    print(f"\n--- Ocurrió un error grave durante la prueba ---")
    print(f"Error: {e}")