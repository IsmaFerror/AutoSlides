import fitz  # PyMuPDF
import sys

class PDFProcessor:
    """
    Clase dedicada a manejar la lógica de extracción de texto
    de archivos PDF.
    """
    
    def __init__(self):
        # Podríamos inicializar configuraciones aquí si fuera necesario
        pass

    def extract_text(self, pdf_path: str) -> str:
        """
        Abre un archivo PDF y extrae todo el texto de sus páginas.
        
        Args:
            pdf_path: La ruta al archivo PDF.

        Returns:
            Un string que contiene todo el texto extraído, o un string
            vacío si ocurre un error.
        """
        print(f"Iniciando extracción de texto desde: {pdf_path}")
        full_text = ""
        try:
            # Abrir el documento PDF
            with fitz.open(pdf_path) as doc:
                print(f"El documento tiene {len(doc)} páginas.")
                # Iterar sobre cada página
                for i, page in enumerate(doc):
                    # Extraer texto de la página
                    text = page.get_text()
                    if text:
                        full_text += text + "\n" # Añadir un salto de línea entre páginas
                
            print(f"Extracción completada. Total de caracteres: {len(full_text)}")
            
            # Opcional: Limpieza simple del texto
            full_text = ' '.join(full_text.split()) # Normalizar espacios en blanco
            
            return full_text

        except fitz.errors.EmptyFileError:
            print(f"Error: El archivo PDF en '{pdf_path}' está vacío.", file=sys.stderr)
            return ""
        except fitz.errors.FileDataError:
             print(f"Error: El archivo PDF en '{pdf_path}' está dañado o mal formado.", file=sys.stderr)
             return ""
        except Exception as e:
            # Capturar cualquier otro error inesperado
            print(f"Error inesperado al procesar PDF: {e}", file=sys.stderr)
            return ""