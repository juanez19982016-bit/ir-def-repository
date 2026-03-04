import os
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(200, 50, 50)
        self.cell(0, 10, 'TONEHUB PRO 2.0 - EL ARSENAL DEFINITIVO', border=False, align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 16)
        self.set_fill_color(30, 30, 30)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, title, fill=True, align='L', new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('helvetica', '', 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln()

    def add_bullet(self, text):
        self.set_font('helvetica', '', 11)
        self.set_text_color(0, 0, 0)
        # We use a simple dash since special bullet chars might break without proper encoding setup
        self.multi_cell(0, 6, f"  - {text}", new_x="LMARGIN", new_y="NEXT")

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# PORTADA
pdf.set_font('helvetica', 'B', 24)
pdf.set_text_color(20, 20, 20)
pdf.cell(0, 20, 'MANUAL OFICIAL Y CATALOGO', align='C', new_x="LMARGIN", new_y="NEXT")
pdf.set_font('helvetica', 'I', 14)
pdf.cell(0, 10, 'La coleccion de 16,605 archivos para llevar tu tono a nivel de estudio', align='C', new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)

# SECTION 1
pdf.chapter_title('1. BIENVENIDO A TONEHUB PRO 2.0')
pdf.chapter_body(
    "Felicidades por adquirir el paquete de simulacion de guitarra y bajo mas completo, masivo y "
    "ordenado de habla hispana.\n\n"
    "Con un peso de 2.57 GB y mas de 16,600 archivos cuidadosamente separados "
    "por marca y plataforma, tienes en tus manos acceso a literalmente cientos de miles de dolares "
    "en amplificadores, gabinetes, microfonos de estudio y pedales boutique reales."
)

# SECTION 2
pdf.chapter_title('2. CONTENIDO DETALLADO DE LA BOVEDA')
pdf.chapter_body("Tu Google Drive esta organizado en las siguientes carpetas principales para tu maxima comodidad:")

pdf.add_bullet("00_EMPIEZA_AQUI: La sub-carpeta con los '50 Imprescindibles' y este manual.")
pdf.add_bullet("01_GABINETES_IRs_GUITARRA (10,711 archivos): Impulse Responses (IRs) ordenados por marca (Marshall, Mesa Boogie, Fender, EVH, Bogner, etc.).")
pdf.add_bullet("02_AMPLIFICADORES_NAM (792 archivos): Cabezales reales clonados mediante Neural Amp Modeler.")
pdf.add_bullet("03_PEDALES_BOUTIQUE_NAM (702 archivos): Overdrives, Fuzzes y distorsiones premium (Klon Centaur, TS9, Rat).")
pdf.add_bullet("04_PRESETS_MULTI_EFECTOS (3,066 archivos): Listos para Helix, Fractal, Boss, TONEX, Ampero y mas.")
pdf.add_bullet("05_BAJO_Y_ACUSTICA (+150 archivos): Bajos Ampeg, pedales Darkglass y capturas de guitarras acusticas de altisima gama.")
pdf.add_bullet("06_REVERBS_DE_ESTUDIO (1,145 archivos): Iglesias, salas y estadios reales para crear espacios vivos en tus grabaciones.")
pdf.ln(5)

# SECTION 3
pdf.chapter_title('3. COMO USAR ESTE MATERIAL')

pdf.set_font('helvetica', 'B', 12)
pdf.cell(0, 8, 'A. Como usar los Impulse Responses (Archivos .WAV)', new_x="LMARGIN", new_y="NEXT")
pdf.chapter_body(
    "Los IRs son fotos acusticas de un gabinete real microfoneado. Para usarlos en tu DAW:\n"
    "1. Inserta un simulador de amplificador (sin cabina activada) o un cabezal NAM.\n"
    "2. Agrega despues un 'IR Loader' (como Pulse, NadIR, o la opcion de custom IR de tu plugin).\n"
    "3. Carga el archivo .wav del IR que mas te guste de la Carpeta 01."
)

pdf.set_font('helvetica', 'B', 12)
pdf.cell(0, 8, 'B. Como usar Neural Amp Modeler (Archivos .NAM)', new_x="LMARGIN", new_y="NEXT")
pdf.chapter_body(
    "Descarga el plugin gratuito 'Neural Amp Modeler' desde la web oficial.\n"
    "1. En el bloque 'Amp', carga cualquier archivo .nam de la Carpeta 02.\n"
    "2. En el bloque 'Pedal' (si aplica), carga un Overdrive de la Carpeta 03 para empujarlo.\n"
    "3. Asegurate de cargar un IR en el mismo plugin NAM o detras de el en la cadena."
)

pdf.set_font('helvetica', 'B', 12)
pdf.cell(0, 8, 'C. Como usar los Presets en tu Hardware', new_x="LMARGIN", new_y="NEXT")
pdf.chapter_body(
    "Si tienes una Helix, Hotone Ampero, Mooer, etc., usa el Software/Editor oficial de tu pedalera.\n"
    "Simplemente importa el archivo (Ej: .hlx para Line6) desde 'File -> Import' o arrastralo directo a un slot vacio. "
    "Recuerda que si el preset usa un IR personalizado, debras cargarlo tambien en tu dispositivo."
)

# SECTION 4
pdf.add_page()
pdf.chapter_title('4. CONSEJOS DE MEZCLA (STUDIO SECRETS)')
pdf.chapter_body("Usa estas tecnicas profesionales que usan los ingenieros de estudio legendarios para que tus guitarras destaquen en la mezcla:")

pdf.add_bullet("Cortes de Frecuencia (EQ): Haz un 'High-Pass Filter' (corte de graves) alrededor de los 80Hz a 100Hz en la guitarra. Esto le deja el espacio libre al Bajo y al Bombo de la bateria para que la mezcla no suene 'sucia'.")
pdf.add_bullet("El 'Anti-Abeja': Pon un 'Low-Pass Filter' (corte de agudos) cerca de los 8kHz a 10kHz. Esto elimina ese ruido digital aspero que a todos nos molesta.")
pdf.add_bullet("Mezcla de Microfonos: ¿No te decides en un IR de guitarra? Usa DOS loaders de IR en paralelo. En uno carga un microfono dinamico (ej. SM57) para el ataque y los medios, y en el otro un microfono de cinta (ej. R121) para el cuerpo. Mezclalos al 50%. ¡Asi es como se graba en la vida real!")
pdf.add_bullet("Overdrive NAM al rescate: Si un amplificador NAM suena un poco flojo para metal moderno, agregale el NAM del 'TS9' o el 'Horizon Precision Drive' justo antes con el nivel alto y el Drive en 0. Apretara los graves magicamente.")

# OUTRO
pdf.ln(15)
pdf.set_font('helvetica', 'B', 14)
pdf.set_text_color(200, 50, 50)
pdf.cell(0, 10, '¡A VOLAR CABEZAS CON TU NUEVO TONO!', align='C', new_x="LMARGIN", new_y="NEXT")
pdf.set_text_color(0, 0, 0)

pdf.output("ToneHub_Pro_Manual_y_Catalogo.pdf")
print("PDF Generado exitosamente.")
