import os
import unicodedata
from datetime import datetime, timedelta
import customtkinter as ctk
from tkcalendar import Calendar
from tkinter import messagebox
from tkinter import filedialog
from PIL import Image, ImageTk, ImageEnhance
from tkinterdnd2 import DND_FILES, TkinterDnD
import tkinter.font as tkFont
import tkinter as tk
import time
import sys
import json
import pygame  # Importar pygame para reproducir sonidos
import shutil


# Importaciones para generar PDFs
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Inicializar pygame para reproducir sonidos
pygame.mixer.init()

print(f"SAPSE - Iniciando sistema...")

# Configuración del tema de customtkinter
ctk.set_appearance_mode("dark")  # Modos: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Temas: "blue" (standard), "green", "dark-blue"

# Funciones para cargar fuentes personalizadas
def load_custom_font(size=14, weight="normal"):
    return ctk.CTkFont(family="Square721Web", size=size, weight=weight)

def load_custom_font_for_title(size=18, weight="normal"):
    return ctk.CTkFont(family="Square721 Ex BT", size=size, weight=weight)

def toggle_fullscreen(event=None):
    is_fullscreen = root.attributes("-fullscreen") # Obtiene el estado actual de pantalla completa y lo invierte
    root.attributes("-fullscreen", not is_fullscreen)

# Funciones principales
def fade_image():
    global img_ctk, img_label, alpha, fade_direction

    # Crear una copia de la imagen original
    img_copy = img.copy()
    
    # Ajustar la transparencia de la imagen
    alpha = max(0.0, min(alpha, 1.0))  # Asegura que alpha esté en el rango [0, 1]
    img_copy.putalpha(int(alpha * 255))  # Ajustar la transparencia en el rango [0, 255]
    
    # Convertir la imagen a formato CTkImage
    img_ctk = ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=(904, 110))
    img_label.configure(image=img_ctk)
    
    # Actualizar la imagen en el Label
    img_label.update_idletasks()
    
    # Actualizar el valor de alpha
    alpha += fade_direction * 0.02  # Ajusta la cantidad del cambio por paso
    
    # Cambiar la dirección del desvanecimiento si se alcanza el límite
    if alpha >= 1.0 or alpha <= 0.0:
        fade_direction *= -1
    
    # Repetir el proceso después de 50 ms para un efecto más suave
    root.after(50, fade_image)


def cargar_mapeo_nombres(archivo_mapeo):
    """Carga el mapeo de DNI a nombres desde el archivo 00_Mapeo_Nomina.txt"""
    mapeo = {}
    try:
        with open(archivo_mapeo, 'r', encoding='utf-8') as f:
            for linea in f:
                partes = linea.strip().split(',', 1)
                if len(partes) == 2:
                    dni, nombre = partes
                    mapeo[dni.strip()] = nombre.strip()
    except FileNotFoundError:
        print(f"Error: Archivo {archivo_mapeo} no encontrado.")
    except Exception as e:
        print(f"Error al procesar el archivo de mapeo: {e}")
    return mapeo


def normalizar_cadena(cadena):
    """Normaliza la cadena eliminando acentos y convirtiendo a minúsculas"""
    cadena = cadena.lower()
    cadena = unicodedata.normalize('NFD', cadena)
    cadena = ''.join(c for c in cadena if unicodedata.category(c) != 'Mn')
    return cadena

def buscar_coincidencias_avanzadas(entrada, nombre_completo):
    """
    Busca coincidencias avanzadas entre la entrada y el nombre completo.
    Permite búsquedas parciales de múltiples palabras.
    
    Args:
        entrada (str): Texto de búsqueda normalizado
        nombre_completo (str): Nombre completo normalizado
    
    Returns:
        bool: True si hay coincidencia, False en caso contrario
    """
    # Si la entrada está completa en el nombre, es una coincidencia directa
    if entrada in nombre_completo:
        return True
    
    # Dividir la entrada en palabras individuales
    palabras_entrada = entrada.split()
    
    # Si solo hay una palabra, verificar si es una abreviatura o inicio de alguna palabra
    if len(palabras_entrada) == 1 and len(palabras_entrada[0]) >= 2:
        palabra = palabras_entrada[0]
        # Verificar si la palabra es el inicio de alguna palabra en el nombre
        for palabra_nombre in nombre_completo.split():
            if palabra_nombre.startswith(palabra) and len(palabra) >= 2:
                return True
        return False
    
    # Si no hay palabras válidas, no hay coincidencia
    palabras_validas = [p for p in palabras_entrada if len(p) >= 2]
    if not palabras_validas:
        return False
    
    # Dividir el nombre completo en palabras
    palabras_nombre = nombre_completo.split()
    
    # Verificar si todas las palabras de la entrada están en el nombre
    # y si están en el mismo orden relativo
    coincidencias = 0
    ultimo_indice = -1
    
    for palabra_entrada in palabras_validas:
        encontrada = False
        for i, palabra_nombre in enumerate(palabras_nombre):
            # Verificar coincidencias exactas o inicios de palabra (para abreviaturas)
            if palabra_nombre == palabra_entrada or palabra_nombre.startswith(palabra_entrada):
                if i > ultimo_indice:  # Mantener el orden relativo
                    ultimo_indice = i
                    encontrada = True
                    coincidencias += 1
                    break
        
        if not encontrada:
            # Verificar coincidencias parciales más flexibles
            for i, palabra_nombre in enumerate(palabras_nombre):
                # Si la palabra de entrada está contenida en la palabra del nombre
                if palabra_entrada in palabra_nombre and len(palabra_entrada) >= 2:
                    if i > ultimo_indice:  # Mantener el orden relativo
                        ultimo_indice = i
                        encontrada = True
                        coincidencias += 1
                        break
            
            # Si aún no se encuentra, verificar iniciales (primera letra)
            if not encontrada and len(palabra_entrada) == 1:
                for i, palabra_nombre in enumerate(palabras_nombre):
                    if palabra_nombre.startswith(palabra_entrada):
                        if i > ultimo_indice:  # Mantener el orden relativo
                            ultimo_indice = i
                            encontrada = True
                            coincidencias += 1
                            break
            
            # Si después de todas las verificaciones no se encuentra, fallamos
            if not encontrada:
                return False
    
    # Para búsquedas de múltiples palabras, requerimos que todas coincidan
    # Para búsquedas de una sola palabra, ya verificamos arriba
    return coincidencias == len(palabras_validas) and coincidencias > 0

from datetime import datetime, timedelta

def procesar_coincidencias(archivo_coincidencias, archivo_mapeo, archivo_salida, fecha_filtro=None):
    # Cargar el mapeo de nombres
    mapeo_dni_a_nombre = cargar_mapeo_nombres(archivo_mapeo)
    print(f"SAPSE - Cargando mapeo...")

    # Diccionario para almacenar entradas y salidas por fecha Y por DNI
    registros_por_dia_y_dni = {}

    # Leer el archivo de coincidencias
    with open(archivo_coincidencias, 'r', encoding='utf-8') as f:
        lineas = f.readlines()
        print(f"SAPSE - Cargando Coincidencias...")

    # Procesar cada línea del archivo de coincidencias
    for linea in lineas:
        datos = linea.strip().split('\t')
        dni = datos[0]
        fecha_hora_str = datos[1]

        # Convertir la fecha y hora a objeto datetime
        fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M:%S")
        fecha = fecha_hora.date()
        
        # **Aplicar filtro de fecha**
        if fecha_filtro and fecha != fecha_filtro:
            continue  

        # Si el DNI no existe en esa fecha, inicializarlo
        if fecha not in registros_por_dia_y_dni:
            registros_por_dia_y_dni[fecha] = {}

        if dni not in registros_por_dia_y_dni[fecha]:
            registros_por_dia_y_dni[fecha][dni] = []

        # Agregar la entrada al listado del DNI en esa fecha
        registros_por_dia_y_dni[fecha][dni].append(fecha_hora)

    # Abrir el archivo de salida para escribir el resultado
    with open(archivo_salida, 'w', encoding='utf-8') as f_salida:
        for fecha, dnis in registros_por_dia_y_dni.items():
            for dni, registros in dnis.items():
                # Ordenar los horarios en la fecha para el DNI
                registros.sort()

                # Obtener la entrada más temprana y la salida más tardía
                hora_entrada = registros[0]
                hora_salida = registros[-1]

                nombre = mapeo_dni_a_nombre.get(dni, "Nombre Desconocido")

                # Verificar si solo hay un registro (entrada sin salida)
                if len(registros) == 1:
                    f_salida.write(f"{nombre} - Fecha: {fecha} - Horario Entrada: {hora_entrada.time()} (Sin salida registrada!)\n\n")
                # Verificar si hay registros duplicados (muy cercanos en tiempo)
                elif len(registros) > 1 and hora_salida - hora_entrada < timedelta(minutes=10):
                    f_salida.write(f"{nombre} - Fecha: {fecha} - ¡Posible duplicación de fichaje! Entrada duplicada a las: {hora_entrada.time()} o salida duplicada a las: {hora_salida.time()}\n\n")
                else:
                    # Determinar si es retiro anticipado o excedido
                    retiro_anticipado = hora_salida - hora_entrada < timedelta(hours=7, minutes=50)
                    retiro_excedido = hora_salida - hora_entrada > timedelta(hours=8, minutes=30)

                    salida_str = f"{nombre} - Fecha: {fecha} - Horario Entrada: {hora_entrada.time()}\n"
                    salida_str += f"{nombre} - Fecha: {fecha} - Horario Salida: {hora_salida.time()}"

                    if retiro_anticipado:
                        salida_str += " (Retiro Anticipado)"
                    elif retiro_excedido:
                        salida_str += " (Retiro Excedido)"
                    
                    salida_str += "\n\n"
                    f_salida.write(salida_str)

    print(f"SAPSE - Procesamiento completado. Archivo temporal guardado en '{archivo_salida}'.")


# Funciones de la GUI
def toggle_calendar():
    global calendar_visible
    if calendar_visible:
        date_frame.pack_forget()  # Ocultar el calendario
        toggle_calendar_button.configure(text="Mostrar Calendario", text_color="#cacaca")
        calendar_visible = False
    else:
        # Asegurar que el calendario se muestre en la posición correcta (arriba)
        # Primero olvidamos el empaquetado actual si existe
        date_frame.pack_forget()
        
        # Luego lo empaquetamos en la posición correcta, antes del frame de búsqueda y resultados
        date_frame.pack(side="top", padx=0, pady=0, anchor="n", before=button_frame)
        toggle_calendar_button.configure(text="Ocultar Calendario", text_color="#cacaca")
        calendar_visible = True
    
    # Guardar la configuración después de cambiar el estado
    guardar_configuracion()

# Variable global para evitar múltiples mensajes de error
mensaje_error_mostrado = False
ultimo_tiempo_error = 0  # Para controlar el tiempo entre mensajes de error

def buscar_datos(event=None):
    global mensaje_error_mostrado, ultimo_tiempo_error
    
    print("Función buscar_datos activada")  # Mensaje de depuración
    
    # Verificar si ya se mostró un mensaje de error recientemente (dentro de 1 segundo)
    tiempo_actual = int(time.time() * 1000)
    if mensaje_error_mostrado or (tiempo_actual - ultimo_tiempo_error < 1000):
        print("Ya se mostró un mensaje de error recientemente, ignorando evento adicional")
        return
    
    # Reproducir sonido de búsqueda
    try:
        pygame.mixer.music.load("snd/search.mp3")
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Error al reproducir el sonido: {str(e)}")
    
    entrada = entry.get().strip()
    
    # Obtener la estación seleccionada
    estacion_seleccionada = selected_station.get()
    print(f"Estación seleccionada: {estacion_seleccionada}")  # Depuración

    if not estacion_seleccionada or estacion_seleccionada == "Sin datos":
        messagebox.showerror("Error", "Seleccione una estación antes de buscar.")
        return
    
    ruta_estacion = os.path.join("dats", estacion_seleccionada)
    
    if not os.path.exists(ruta_estacion) or not os.path.isdir(ruta_estacion):
        messagebox.showerror("Error", f"No se encontró la carpeta de la estación: {estacion_seleccionada}")
        return
    
    # Limpiar el texto predeterminado si está presente
    if entrada == "Escriba DNI/Nombre/Apellido del componente...":
        # Enfocar el campo de entrada para que el usuario pueda escribir
        entry.focus_set()
        entry.delete(0, "end")
        try:
            mensaje_error_mostrado = True
            ultimo_tiempo_error = tiempo_actual
            messagebox.showinfo("Información", "Por favor, ingrese un DNI o nombre para realizar la búsqueda.")
        finally:
            # Restablecer la bandera después de mostrar el mensaje
            root.after(1000, lambda: setattr(sys.modules[__name__], 'mensaje_error_mostrado', False))
        return
    
    if not entrada:
        # Enfocar el campo de entrada para que el usuario pueda escribir
        entry.focus_set()
        try:
            mensaje_error_mostrado = True
            ultimo_tiempo_error = tiempo_actual
            messagebox.showerror("Error", "No escribió ningún DNI o nombre.")
        finally:
            # Restablecer la bandera después de mostrar el mensaje
            root.after(1000, lambda: setattr(sys.modules[__name__], 'mensaje_error_mostrado', False))
        return
    
    print(f"Buscando datos para: {entrada}")  # Mensaje de depuración
    
    # Verificar si el calendario está visible para aplicar filtro de fecha
    fecha_filtro = None
    if calendar_visible:
        fecha_seleccionada = date_picker.get_date()  # Obtener la fecha seleccionada desde el calendario
        if not fecha_seleccionada:
            try:
                mensaje_error_mostrado = True
                ultimo_tiempo_error = tiempo_actual
                messagebox.showerror("Error", "Seleccione una fecha.")
            finally:
                # Restablecer la bandera después de mostrar el mensaje
                root.after(1000, lambda: setattr(sys.modules[__name__], 'mensaje_error_mostrado', False))
            return
        # Convertir la fecha al formato adecuado (sin la hora)
        fecha_filtro = datetime.strptime(fecha_seleccionada, "%m/%d/%Y").date()  # Ahora solo estamos usando la fecha
        print(f"Filtrando por fecha: {fecha_filtro}")  # Mensaje de depuración

    entrada_normalizada = normalizar_cadena(entrada)
    mapeo_dni_a_nombre = cargar_mapeo_nombres('00_Mapeo_Nomina.txt')
    dnis_a_filtrar = set()

    for dni, nombre in mapeo_dni_a_nombre.items():
        nombre_normalizado = normalizar_cadena(nombre)
        # Verificar coincidencia exacta con DNI
        if entrada_normalizada in dni.lower():
            dnis_a_filtrar.add(dni)
            continue
            
        # Verificar coincidencia exacta con el nombre
        if entrada_normalizada in nombre_normalizado:
            dnis_a_filtrar.add(dni)
            continue
            
        # Verificar coincidencias avanzadas (parciales, múltiples palabras)
        if buscar_coincidencias_avanzadas(entrada_normalizada, nombre_normalizado):
            dnis_a_filtrar.add(dni)

    if not dnis_a_filtrar:
        try:
            mensaje_error_mostrado = True
            ultimo_tiempo_error = tiempo_actual
            messagebox.showerror("Error", "No se encontraron coincidencias para el DNI o Nombre/Apellido proporcionado.")
        finally:
            # Restablecer la bandera después de mostrar el mensaje
            root.after(1000, lambda: setattr(sys.modules[__name__], 'mensaje_error_mostrado', False))
        return

    dat_files = [f for f in os.listdir(ruta_estacion) if f.endswith('.dat')]
    if not dat_files:
        try:
            mensaje_error_mostrado = True
            ultimo_tiempo_error = tiempo_actual
            messagebox.showerror("Error", f"No se detectaron archivos .dat en la carpeta de {estacion_seleccionada}.")
        finally:
            # Restablecer la bandera después de mostrar el mensaje
            root.after(1000, lambda: setattr(sys.modules[__name__], 'mensaje_error_mostrado', False))
        return

    archivo_datos_path = os.path.join(ruta_estacion, dat_files[0])
    with open(archivo_datos_path, 'r', encoding='utf-8') as archivo_datos, open("tmp/coincidencias.txt", 'w', encoding='utf-8') as coincidencias_file:
        for linea in archivo_datos:
            dni = linea.strip().split('\t')[0]
            if dni in dnis_a_filtrar:
                coincidencias_file.write(linea)

    archivo_mapeo = '00_Mapeo_Nomina.txt'
    archivo_salida = 'tmp/coincidencias_formateadas.txt'
    
    # Pasar la fecha de filtro al procesador (puede ser None si el calendario está oculto)
    procesar_coincidencias('tmp/coincidencias.txt', archivo_mapeo, archivo_salida, fecha_filtro)

    mostrar_resultados(archivo_salida)


def mostrar_resultados(archivo_salida):
    if not os.path.exists(archivo_salida):
        messagebox.showerror("Error", f"El archivo {archivo_salida} no existe.")
        return

    with open(archivo_salida, 'r', encoding='utf-8') as file:
        contenido = file.read()

    # Habilitar el campo de texto para poder modificarlo
    result_text.configure(state="normal")
    result_text._textbox.delete("1.0", "end")  # Limpiar el área de texto
    
    # Insertar el contenido con formato
    lineas = contenido.split('\n')
    for linea in lineas:
        # Verificar si contiene duplicación de fichaje
        if '¡Posible duplicación de fichaje!' in linea:
            # Dividir la línea en partes para aplicar formato
            partes = linea.split(' - ')
            nombre = partes[0]
            fecha = partes[1].replace('Fecha: ', '')
            mensaje_duplicacion = partes[2]
            
            result_text._textbox.insert("end", f"{nombre} - ", "nombre")
            result_text._textbox.insert("end", f"Fecha: {fecha} - ", "fecha")
            result_text._textbox.insert("end", f"{mensaje_duplicacion}\n", "duplicacion")
        # Verificar si contiene entrada
        elif 'Horario Entrada:' in linea and 'Horario Salida:' not in linea:
            # Verificar si es un caso de "Sin salida registrada"
            if '(Sin salida registrada!)' in linea:
                nombre, resto = linea.split(' - Fecha: ', 1)
                fecha, horario_entrada = resto.split(' - Horario Entrada: ', 1)
                # Eliminar el texto "(Sin salida registrada!)" del horario de entrada
                horario_entrada = horario_entrada.replace('(Sin salida registrada!)', '').strip()
                result_text._textbox.insert("end", f"{nombre} - ", "nombre")
                result_text._textbox.insert("end", f"Fecha: {fecha} - ", "fecha")
                result_text._textbox.insert("end", f"Horario Entrada: {horario_entrada} ", "entrada")
                # Aplicar correctamente el tag sin_salida
                result_text._textbox.insert("end", "(Sin salida registrada!)\n", "sin_salida")
            else:
                nombre, resto = linea.split(' - Fecha: ', 1)
                fecha, horario_entrada = resto.split(' - Horario Entrada: ', 1)
                result_text._textbox.insert("end", f"{nombre} - ", "nombre")
                result_text._textbox.insert("end", f"Fecha: {fecha} - ", "fecha")
                result_text._textbox.insert("end", f"Horario Entrada: {horario_entrada}\n", "entrada")
        # Verificar si contiene salida
        elif 'Horario Salida:' in linea:
            nombre, resto = linea.split(' - Fecha: ', 1)
            fecha, horario_salida = resto.split(' - Horario Salida: ', 1)
            result_text._textbox.insert("end", f"{nombre} - ", "nombre")
            result_text._textbox.insert("end", f"Fecha: {fecha} - ", "fecha")
            # Verificar etiquetas adicionales y aplicar el tag correspondiente
            if '(Retiro Excedido)' in horario_salida:
                horario_salida = horario_salida.replace('(Retiro Excedido)', '').strip()
                result_text._textbox.insert("end", f"Horario Salida: {horario_salida} ", "salida")
                result_text._textbox.insert("end", "(Retiro Excedido)\n", "retiro_excedido")
            elif '(Retiro Anticipado)' in horario_salida:
                horario_salida = horario_salida.replace('(Retiro Anticipado)', '').strip()
                result_text._textbox.insert("end", f"Horario Salida: {horario_salida} ", "salida")
                result_text._textbox.insert("end", "(Retiro Anticipado)\n", "retiro_anticipado")
            else:
                result_text._textbox.insert("end", f"Horario Salida: {horario_salida}\n", "salida")
        else:
            # Para líneas que no cumplen los anteriores criterios
            result_text._textbox.insert("end", linea + '\n')
    
    # Deshabilitar el campo de texto después de insertar el contenido
    result_text.configure(state="disabled")

def guardar_pdf():
    """Función para guardar los resultados en un archivo PDF"""
    # Verificar si hay resultados para guardar
    contenido = result_text._textbox.get("1.0", "end").strip()
    if not contenido or contenido == "Aca se mostrarán los resultados...":
        messagebox.showinfo("Información", "No hay resultados para guardar.")
        return
    
    # Generar nombre de archivo automáticamente con fecha y hora actual
    fecha_hora_actual = datetime.now().strftime("%d-%m-%Y - %H.%M.%S")
    nombre_archivo_sugerido = f"Biometricos - Reporte {fecha_hora_actual}"
    
    # Solicitar al usuario la ubicación para guardar el archivo
    archivo_pdf = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Archivos PDF", "*.pdf")],
        title="Guardar resultados como PDF",
        initialfile=nombre_archivo_sugerido
    )
    
    if not archivo_pdf:  # Si el usuario cancela la operación
        return
    
    try:
        # Crear el documento PDF
        doc = SimpleDocTemplate(
            archivo_pdf,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Estilos para el documento
        styles = getSampleStyleSheet()
        style_title = styles["Title"]
        style_heading = styles["Heading2"]
        style_normal = styles["Normal"]
        
        # Crear una lista para almacenar los elementos del PDF
        elements = []
        
        # Agregar la imagen del banner
        try:
            ruta_imagen = "img/Banner_Reporte.png"
            img = ReportLabImage(ruta_imagen, width=450, height=148)  # Ajustar tamaño manteniendo proporción
            img.hAlign = 'CENTER'  # Centrar la imagen
            elements.append(img)
            elements.append(Spacer(1, 0.25*inch))
        except Exception as e:
            print(f"Error al cargar la imagen: {str(e)}")
        
        # Agregar título
        elements.append(Paragraph("SAPSE - Reporte de Registros Biométricos", style_title))
        elements.append(Spacer(1, 0.25*inch))
        
        # Agregar fecha de generación
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        elements.append(Paragraph(f"Generado el: {fecha_actual}", style_normal))
        elements.append(Spacer(1, 0.25*inch))
        
        # Obtener el contenido del área de texto
        lineas = contenido.split('\n')
        
        # Procesar cada línea y formatearla para el PDF
        for linea in lineas:
            if linea.strip():  # Ignorar líneas vacías
                elements.append(Paragraph(linea, style_normal))
                elements.append(Spacer(1, 0.1*inch))
        
        # Construir el PDF
        doc.build(elements)
        
        messagebox.showinfo("Éxito", f"El archivo PDF se ha guardado correctamente en:\n{archivo_pdf}")
    
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al guardar el PDF:\n{str(e)}")

# Cargar nombres desde el JSON
def cargar_nombres_estaciones(ruta_json):
    try:
        with open(ruta_json, "r", encoding="utf-8") as file:
            data = json.load(file)
        return list(data.values())  # Extrae solo los nombres de estación
    except Exception as e:
        print(f"Error al cargar el JSON: {e}")
        return ["Error al cargar"]  # Opción por defecto en caso de error

# Ruta del archivo JSON
ruta_json = "mapbio/mapbio.json"

# Obtener lista de nombres de estaciones
opciones_estaciones = cargar_nombres_estaciones(ruta_json)

# Crear la ventana GUI con customtkinter
class TkinterDnDApp(ctk.CTk, TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

# Inicializar la ventana principal
root = TkinterDnDApp()
root.title("SAPSE - Biometrics V7.0")
root.attributes("-alpha", 0.980)
# Obtener el tamaño de la pantalla
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Establecer el tamaño de la ventana en un porcentaje del tamaño de la pantalla
width = int(screen_width * 0.8)  # 80% del ancho de la pantalla
height = int(screen_height * 0.8)  # 80% de la altura de la pantalla

# Establecer la geometría de la ventana
root.geometry(f"{width}x{height}+{int((screen_width - width) / 2)}+{int((screen_height - height) / 2)}")

root.bind("<F11>", toggle_fullscreen)

# Variable para rastrear el estado de la ventana
is_contracted = False

# Establecer el icono de la aplicación usando un archivo .ico
try:
    # Método para Windows
    root.iconbitmap("ico/biometrico.ico")
except:
    try:
        # Método alternativo usando PIL para compatibilidad multiplataforma
        img = Image.open("ico/biometrico.ico")
        icon = ImageTk.PhotoImage(img)
        root.iconphoto(True, icon)
    except:
        print("No se pudo cargar el icono")

# Crear un frame principal que ocupe toda la ventana con color de fondo #121212
main_frame = ctk.CTkFrame(root, fg_color="#121212", corner_radius=0)
main_frame.pack(fill="both", expand=True)

# Cargar y mostrar la imagen
img = Image.open("img/image.png")
img = img.resize((904, 110))  # Ajusta el tamaño según sea necesario
img = img.convert("RGBA")  # Convertir a RGBA para soporte de transparencia

# Usar CTkImage en lugar de ImageTk.PhotoImage
img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(904, 110))
img_label = ctk.CTkLabel(main_frame, image=img_ctk, text="", fg_color="#121212")
img_label.pack(padx=0, pady=15, fill="both")

# Parámetros del efecto de desvanecimiento
alpha = 0.0  # Nivel inicial de transparencia
fade_direction = 1  # 1 para aumentar la transparencia, -1 para disminuir

# Iniciar el efecto de desvanecimiento
fade_image()

def seleccionar_archivo():
    archivo = filedialog.askopenfilename(filetypes=[("Archivos de texto", "*.txt")])
    if archivo:
        entry.delete(0, "end")
        entry.insert(0, archivo)

def arrastrar_archivo(event):
    archivo = event.data
    archivo = archivo.strip("{}")
    if os.path.isfile(archivo) and archivo.endswith('.sapse'):
        # Leer el contenido del archivo y actualizar 00_Mapeo_Nomina.txt
        with open(archivo, 'r', encoding='utf-8') as archivo_arrastrado:
            with open('00_Mapeo_Nomina.txt', 'w', encoding='utf-8') as archivo_mapeo:
                archivo_mapeo.write(archivo_arrastrado.read())
        messagebox.showinfo("Éxito", "El mapeo se ha actualizado!")
        # Mostrar mensaje de éxito
        entry.delete(0, "end")
        entry.insert(0, 'Mapeo cargado con éxito!')

        # Esperar 2 segundos y luego mostrar el siguiente mensaje
        root.after(1000, mostrar_siguiente_mensaje)
    else:
        messagebox.showerror("Error", "Solo se permiten archivos con la extensión '.sapse'.")

def mostrar_siguiente_mensaje():
    entry.delete(0, "end")
    entry.insert(0, 'Escriba DNI/Nombre/Apellido del componente...')
    
def arrastrar_archivo_dat(event):
    archivo = event.data
    archivo = archivo.strip("{}")  # Limpiar ruta recibida

    if not os.path.isfile(archivo) or not archivo.endswith('.dat'):
        messagebox.showerror("Error", "Solo se permiten archivos con la extensión .dat.")
        return

    # Cargar el mapeo desde mapbio.json
    try:
        with open("mapbio/mapbio.json", "r", encoding="utf-8") as file:
            mapbio = json.load(file)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar mapbio.json: {e}")
        return

    nombre_archivo = os.path.basename(archivo)

    # Buscar la estación correspondiente en el mapeo
    estacion_destino = mapbio.get(nombre_archivo, None)
    
    if not estacion_destino:
        messagebox.showerror("Error", f"No se encontró una estación asociada a {nombre_archivo}.")
        return

    # Crear la carpeta si no existe
    ruta_destino = os.path.join("dats", estacion_destino)
    os.makedirs(ruta_destino, exist_ok=True)

    # Mover el archivo a su carpeta correspondiente
    destino_final = os.path.join(ruta_destino, nombre_archivo)
    try:
        shutil.move(archivo, destino_final)
        messagebox.showinfo("Éxito", f"Archivo {nombre_archivo} movido a {ruta_destino} correctamente!")
        
        # Actualizar la UI
        entry.delete(0, "end")
        entry.insert(0, 'Biométricos cargados con éxito! Ya puede buscar.')

        # Esperar 2 segundos y luego mostrar el siguiente mensaje
        root.after(1000, mostrar_siguiente_mensaje)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo mover el archivo: {e}")
  
# Crear un Frame para contener el Entry y el Canvas
frame = ctk.CTkFrame(main_frame, width=400, height=120, fg_color="#121212")  # THEME FRAME BUSCADOR
frame.pack_propagate(True)  # Evita que el Frame se redimensione automáticamente
frame.pack(fill="x", expand=False, padx=100, pady=0, anchor="n")  # Relleno y expansión con márgenes

# Crear un Canvas para arrastrar el archivo .dat (usando un frame de customtkinter)
canvas_dat_frame = ctk.CTkFrame(frame, width=100, height=100, corner_radius=0, fg_color="#121212")
canvas_dat_frame.pack(side="left", padx=40, pady=0)

# Cargar y redimensionar la imagen para el canvas_dat
imagen_dat = Image.open('img/dat.png')  # Cambia esta ruta a la ubicación de tu imagen
imagen_dat = imagen_dat.resize((80, 80), Image.LANCZOS)  # Ajusta el tamaño según sea necesario
imagen_dat_ctk = ctk.CTkImage(light_image=imagen_dat, dark_image=imagen_dat, size=(80, 80))

# Mostrar la imagen en un label dentro del frame
canvas_dat_label = ctk.CTkLabel(canvas_dat_frame, image=imagen_dat_ctk, text="")
canvas_dat_label.pack(expand=True, fill="both")

# Hacer que el frame acepte arrastre de archivos .dat
canvas_dat_frame.drop_target_register(DND_FILES)
canvas_dat_frame.dnd_bind('<<Drop>>', arrastrar_archivo_dat)

# Cargar y mostrar la primera imagen en el Frame
img1 = Image.open("img/user.png")
img1 = img1.resize((30, 30), Image.LANCZOS)
img1_ctk = ctk.CTkImage(light_image=img1, dark_image=img1, size=(30, 30))
img1_label = ctk.CTkLabel(frame, image=img1_ctk, text="")
img1_label.pack(side="left", padx=5, pady=0, expand=True, anchor="e")

# Crear un Frame para mostrar la imagen de mapeo
canvas_frame = ctk.CTkFrame(frame, width=100, height=100, corner_radius=0, fg_color="#121212")
canvas_frame.pack(side="right", padx=50, pady=0)

# Cargar y redimensionar la imagen
imagen = Image.open('img/mapeo.png')  # Cambia esta ruta a la ubicación de tu imagen
imagen = imagen.resize((80, 80), Image.LANCZOS)
imagen_ctk = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(80, 80))

# Mostrar la imagen en un label dentro del frame
canvas_label = ctk.CTkLabel(canvas_frame, image=imagen_ctk, text="")
canvas_label.pack(expand=True, fill="both")

# Configurar el Frame con soporte para arrastrar y soltar
canvas_frame.drop_target_register(DND_FILES)
canvas_frame.dnd_bind('<<Drop>>', arrastrar_archivo)

# Agregar selector de fecha (mantenemos el widget Calendar de tkcalendar)
date_frame = ctk.CTkFrame(main_frame, fg_color="#121212")

# Variables para detectar doble clic en el calendario
ultimo_clic_calendario = 0
umbral_doble_clic = 500  # milisegundos

def on_calendar_selected(event):
    global ultimo_clic_calendario, mensaje_error_mostrado, ultimo_tiempo_error
    tiempo_actual = int(time.time() * 1000)
    
    # Verificar si es un doble clic (dos clics en menos de umbral_doble_clic milisegundos)
    if tiempo_actual - ultimo_clic_calendario < umbral_doble_clic:
        print("Doble clic detectado en el calendario")
        # Verificar si hay texto en el campo de entrada
        entrada = entry.get().strip()
        if entrada == "Escriba DNI/Nombre/Apellido del componente..." or not entrada:
            # Verificar si ya se mostró un mensaje de error recientemente
            if mensaje_error_mostrado or (tiempo_actual - ultimo_tiempo_error < 1000):
                print("Ya se mostró un mensaje de error recientemente, ignorando evento adicional")
                return
                
            try:
                mensaje_error_mostrado = True
                ultimo_tiempo_error = tiempo_actual
                messagebox.showinfo("Información", "Por favor, ingrese un DNI o nombre antes de realizar la búsqueda.")
            finally:
                # Restablecer la bandera después de mostrar el mensaje
                root.after(1000, lambda: setattr(sys.modules[__name__], 'mensaje_error_mostrado', False))
            return
        
        # Si hay texto en el campo de entrada, realizar la búsqueda
        print(f"Realizando búsqueda con entrada: {entrada}")
        buscar_datos()
    
    # Actualizar el tiempo del último clic
    ultimo_clic_calendario = tiempo_actual

date_picker = Calendar(date_frame,
                       selectmode='day', 
                       date_pattern='mm/dd/y',
                       locale='es_ES',  # Establecer idioma a español
                       background='#121212',           # Fondo oscuro para el calendario
                       foreground='#444444',           # Color de texto de los meses y años
                       normalbackground='#121212',      # Fondo oscuro para los días no seleccionados
                       normalforeground='#444444',      # Color de texto para los días no seleccionados
                       selectbackground='#202020',     # Color de selección
                       selectforeground='#64a7e6',      # Texto blanco para fecha seleccionada
                       font=('Segoe UI', 10, 'bold'),           # Fuente moderna
                       weekendforeground='#2d3a44',    # Texto para fines de semana
                       weekendbackground='#121212',    # Fondo para fines de semana
                       showweeknumbers=False,           # Mostrar números de semana
                       highlightthickness=0,           # Sin grosor extra en el borde
                       bordercolor='#121212',          # Color del borde
                       selectborderwidth=0,            # Borde fino para la fecha seleccionada
                       borderwidth=-0,                  # Grosor del borde de las celdas de los días
                       headersbackground='#121212',    # Fondo oscuro para encabezados de los días
                       headersforeground='#444444',    # Texto para los días de la semana
                       othermonthbackground='#121212', # Fondo gris oscuro para días de otros meses
                       othermonthforeground='#181818',
                       othermonthwebackground='#121212',
                       othermonthweforeground='#202020')

# Vincular el evento de selección del calendario
date_picker.bind("<<CalendarSelected>>", on_calendar_selected)

# Vincular el evento de doble clic a todos los widgets internos del calendario
def configurar_eventos_doble_clic():
    try:
        # Obtener el widget interno que contiene los días
        for child in date_picker.winfo_children():
            child.bind("<Double-1>", on_calendar_selected)
            print(f"Vinculando evento a: {child}")
            
            # Recursivamente para widgets anidados
            for subchild in child.winfo_children():
                subchild.bind("<Double-1>", on_calendar_selected)
                print(f"Vinculando evento a: {subchild}")
                
                # Un nivel más profundo para asegurarnos de capturar los días
                for grandchild in subchild.winfo_children():
                    grandchild.bind("<Double-1>", on_calendar_selected)
                    print(f"Vinculando evento a: {grandchild}")
                    
                    # Un nivel más para llegar a los días individuales
                    for great_grandchild in grandchild.winfo_children():
                        great_grandchild.bind("<Double-1>", on_calendar_selected)
                        print(f"Vinculando evento a: {great_grandchild}")
        
        # También vincular al evento CalendarSelected que se dispara cuando se selecciona una fecha
        date_picker.bind("<<CalendarSelected>>", lambda event: print("Fecha seleccionada"))
    except Exception as e:
        print(f"Error al configurar eventos de doble clic: {e}")

# Ejecutar después de que la interfaz esté completamente cargada
root.after(500, configurar_eventos_doble_clic)  # Aumentar el tiempo de espera para asegurarnos de que el calendario esté completamente cargado

date_picker.pack(pady=0)

# Configurar el evento para capturar Enter en el calendario
# Necesitamos acceder a los widgets internos del calendario para capturar eventos de teclado
def configurar_eventos_calendario():
    # Intentar capturar el evento Enter en todos los widgets internos del calendario
    for child in date_picker.winfo_children():
        child.bind("<Return>", buscar_datos)
        # Recursivamente para widgets anidados
        for subchild in child.winfo_children():
            subchild.bind("<Return>", buscar_datos)

# Función para vincular el evento Enter a toda la aplicación
def configurar_evento_enter_global():
    try:
        # Vincular el evento Enter solo a la ventana principal y al campo de entrada
        # Esto es suficiente para capturar el evento Enter en toda la aplicación
        root.bind("<Return>", buscar_datos)
        root.bind("<KP_Enter>", buscar_datos)  # Tecla Enter del teclado numérico
        entry.bind("<Return>", buscar_datos)
        
        print("Evento Enter vinculado a la ventana principal y al campo de entrada")
        
        # No es necesario vincular a todos los widgets, ya que el evento se propaga
        # desde la ventana principal a todos los widgets hijos
        
        print("Configuración de eventos Enter completada")
    except Exception as e:
        print(f"Error al configurar eventos Enter: {e}")

# Enfocar el campo de entrada al iniciar la aplicación
def enfocar_campo_entrada():
    entry.focus_set()
    print("Campo de entrada enfocado")

# Ejecutar después de que la interfaz esté completamente cargada
# Configurar los eventos primero
root.after(100, configurar_eventos_calendario)
root.after(200, configurar_evento_enter_global)
root.after(300, enfocar_campo_entrada)
# Aplicar el estado del calendario después de definir la función
root.after(50, lambda: aplicar_estado_calendario())

# Variable global para rastrear si el calendario está visible
calendar_visible = True

# Botón para alternar la visibilidad del calendario
toggle_calendar_button = ctk.CTkButton(
    main_frame,
    text="Ocultar Calendario",  # Texto inicial, se actualizará según la configuración
    command=toggle_calendar,
    fg_color="#202020",
    hover_color="#303030",
    text_color="#cacaca",
    font=load_custom_font_for_title(size=12),
    corner_radius=5,
    height=30
)
toggle_calendar_button.pack(pady=5, anchor="n")

# NO mostrar el calendario inicialmente, esperar a cargar la configuración
# date_frame.pack(side="top", padx=0, pady=0, anchor="n")  # Comentado para evitar el parpadeo

# Función para aplicar el estado del calendario según la configuración
def aplicar_estado_calendario():
    global calendar_visible
    
    # Cargar la configuración
    cargar_configuracion()
    
    # Aplicar el estado del calendario según la configuración
    if calendar_visible:
        # Mostrar el calendario
        date_frame.pack(side="top", padx=0, pady=0, anchor="n", before=button_frame)
        toggle_calendar_button.configure(text="Ocultar Calendario")
    else:
        # Ocultar el calendario
        date_frame.pack_forget()
        toggle_calendar_button.configure(text="Mostrar Calendario")
    
    print(f"Estado del calendario aplicado: {'visible' if calendar_visible else 'oculto'}")

# Ejecutar después de que la interfaz esté completamente cargada
# Ya se llamó a aplicar_estado_calendario antes, no es necesario llamarlo de nuevo

# Cuadro de búsqueda con customtkinter
entry = ctk.CTkEntry(frame, width=2000, height=40, font=load_custom_font_for_title(size=16, weight="bold"), text_color="#969696", fg_color="#202020", border_width=0, border_color="#121212")
entry.pack(side="right", padx=0, pady=0, expand=False, fill="x")
entry.insert(0, "Escriba DNI/Nombre/Apellido del componente...")  # Texto por defecto

# Función para limpiar el texto de entrada cuando el usuario empieza a escribir
def limpiar_texto_entrada(event):
    """Limpia el texto de entrada si es el texto predeterminado."""
    if entry.get() == "Escriba DNI/Nombre/Apellido del componente...":
        entry.delete(0, "end")

def restaurar_texto_entrada(event):
    """Restaura el texto predeterminado si el campo está vacío al perder el foco."""
    if entry.get() == "":
        entry.insert(0, "Escriba DNI/Nombre/Apellido del componente...")

# Asociar las funciones a los eventos de entrada y pérdida de foco
entry.bind("<FocusIn>", limpiar_texto_entrada)   # Limpia el texto al hacer foco
entry.bind("<FocusOut>", restaurar_texto_entrada)  # Restaura el texto al perder el foco
# Agregar evento para buscar al presionar Enter en el cuadro de búsqueda
entry.bind("<Return>", buscar_datos)

# Agregar evento para buscar al presionar Enter en el calendario
date_picker.bind("<Return>", buscar_datos)
# También podemos agregar el evento al frame del calendario para capturar el Enter cuando el calendario tiene el foco
date_frame.bind("<Return>", buscar_datos)

# Botón de búsqueda con customtkinter
button_frame = ctk.CTkFrame(main_frame, fg_color="#121212")
button_frame.pack(pady=5, anchor="n")

buscar_btn = ctk.CTkButton(button_frame, text="| BUSCAR |", command=buscar_datos, 
                           font=load_custom_font_for_title(size=14, weight="bold"),
                           fg_color="#242424", hover_color="#19232b", text_color="#cacaca", border_width=0, border_color="#121212", corner_radius=5, width=100, height=30)
buscar_btn.pack(pady=0, side="left", padx=5)

# Botón para guardar en PDF
guardar_pdf_btn = ctk.CTkButton(button_frame, text="| GUARDAR PDF |", command=guardar_pdf, 
                               font=load_custom_font_for_title(size=14, weight="bold"),
                               fg_color="#242424", hover_color="#19232b", text_color="#cacaca", border_width=0, border_color="#121212", corner_radius=5, width=120, height=30)
guardar_pdf_btn.pack(pady=0, side="left", padx=5)

# Frame contenedor para alinear los elementos
dat_selector_container = ctk.CTkFrame(main_frame, fg_color="transparent")  
dat_selector_container.pack(pady=0, padx=10, anchor="w")  # Ajusta a la izquierda

# Texto a la izquierda
dat_selector_text = ctk.CTkLabel(dat_selector_container, text=f"| Selección de estación:", 
                                 font=load_custom_font_for_title(size=15, weight="bold"), 
                                 text_color="#bababa", anchor="w")
dat_selector_text.pack(side="left", padx=(40, 10))  # Espacio a la derecha

# Frame a la derecha del texto
dat_selector_frame = ctk.CTkFrame(dat_selector_container, width=300, corner_radius=0, fg_color="#121212")  
dat_selector_frame.pack(side="left")  # Se alinea a la derecha del texto
# Variable para almacenar la selección
selected_station = ctk.StringVar(value=opciones_estaciones[0] if opciones_estaciones else "Sin estaciones cargadas", name="selected_station")

# Menú desplegable en lugar del texto fijo
dat_selector_dropdown = ctk.CTkOptionMenu(dat_selector_frame, 
                                          values=opciones_estaciones, 
                                          variable=selected_station, 
                                          font=load_custom_font_for_title(size=12, weight="bold"),
                                          fg_color="#181818",
                                          button_color="#242424",
                                          text_color="#92a4af",
                                          dropdown_fg_color="#2E2E2E",
                                          dropdown_text_color="#bababa",
                                          width=210)
dat_selector_dropdown.pack(pady=0, padx=10, anchor="w")

# Área de texto para mostrar los resultados
result_frame = ctk.CTkFrame(main_frame, fg_color="#121212", bg_color="#121212", width=400, height=320)
result_frame.pack(fill="both", expand=True, padx=40, pady=10)

result_text = ctk.CTkTextbox(result_frame, wrap="word", font=load_custom_font(size=15), 
                             text_color="#cacaca", corner_radius=10, fg_color="#202020", state="disabled")
result_text.pack(fill="both", expand=True)  # Ajuste dinámico

# Configurar los tags para los colores y estilos
result_text._textbox.tag_configure("default", foreground="#555555", font=load_custom_font(size=15, weight="normal").cget("family") + " 15 italic")
result_text._textbox.tag_configure("nombre", foreground="#86a8cf", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("fecha", foreground="#cacaca", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("entrada", foreground="#94d4ad", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("salida", foreground="#d49898", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("retiro_excedido", foreground="#77b0f2", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("sin_salida", foreground="#d36d6d", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("retiro_anticipado", foreground="#f0f277", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("duplicacion", foreground="#ebb86d", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")

# Configurar los tags para el efecto hover (cuando el mouse está sobre el texto)
result_text._textbox.tag_configure("hover_default", foreground="#777777", background="#2a2a2a", font=load_custom_font(size=15, weight="normal").cget("family") + " 15 italic")
result_text._textbox.tag_configure("hover_nombre", foreground="#a8c6e7", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("hover_fecha", foreground="#ffffff", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("hover_entrada", foreground="#b8ecc9", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("hover_salida", foreground="#edb6b6", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("hover_retiro_excedido", foreground="#a8d0ff", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("hover_sin_salida", foreground="#ff9797", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("hover_retiro_anticipado", foreground="#f7f7a9", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")
result_text._textbox.tag_configure("hover_duplicacion", foreground="#ffd699", background="#2a2a2a", font=load_custom_font(size=10, weight="bold").cget("family") + " 10 bold")

# Funciones para manejar el efecto hover
def on_text_enter(event, tag):
    """Función que se ejecuta cuando el mouse entra en un texto con una etiqueta específica"""
    # Obtener la posición del mouse
    index = result_text._textbox.index(f"@{event.x},{event.y}")
    # Verificar si el texto en esa posición tiene la etiqueta especificada
    if tag in result_text._textbox.tag_names(index):
        # Aplicar la etiqueta hover correspondiente
        start_index = result_text._textbox.index(f"{index} linestart")
        end_index = result_text._textbox.index(f"{index} lineend")
        result_text._textbox.tag_add(f"hover_{tag}", start_index, end_index)

def on_text_leave(event, tag):
    """Función que se ejecuta cuando el mouse sale de un texto con una etiqueta específica"""
    # Eliminar todas las etiquetas hover
    result_text._textbox.tag_remove(f"hover_{tag}", "1.0", "end")

# Vincular eventos de entrada y salida del mouse para cada etiqueta
for tag in ["default", "nombre", "fecha", "entrada", "salida", "retiro_excedido", "sin_salida", "retiro_anticipado", "duplicacion"]:
    result_text._textbox.tag_bind(tag, "<Enter>", lambda e, t=tag: on_text_enter(e, t))
    result_text._textbox.tag_bind(tag, "<Leave>", lambda e, t=tag: on_text_leave(e, t))

# Insertar texto por defecto en el área de texto
result_text.configure(state="normal")  # Habilitar para insertar texto
result_text._textbox.insert("1.0", "Aca se mostrarán los resultados...", "default")
result_text.configure(state="disabled")  # Deshabilitar después de insertar

# Función para limpiar el texto de resultados cuando el usuario hace clic en el área de texto
def limpiar_texto_resultado(event):
    if result_text._textbox.get("1.0", "end").strip() == "Aca se mostrarán los resultados...":
        result_text.configure(state="normal")  # Habilitar temporalmente para edición
        result_text._textbox.delete("1.0", "end")
        result_text.configure(state="disabled")  # Deshabilitar nuevamente

# Bind para limpiar el texto de resultados cuando el usuario hace clic en el área de texto
result_text._textbox.bind("<Button-1>", limpiar_texto_resultado)

# Crear un Label encima del Frame
label = ctk.CTkLabel(main_frame, text="S.A.P.S.E | Biometrics  V8.0 - 2025 (By SP Productions)", font=load_custom_font_for_title(size=11), text_color="#787878")
label.pack(pady=(0, 10))  # Agrega un margen superior y evita solapamiento con el Frame

# Función para manejar el cierre de la aplicación
def on_closing():
    # Guardar la configuración antes de cerrar
    guardar_configuracion()
    # Cerrar la aplicación
    root.destroy()

# Configurar el manejador de cierre de la ventana
root.protocol("WM_DELETE_WINDOW", on_closing)

# Asegurarse de que exista el directorio tmp
if not os.path.exists("tmp"):
    os.makedirs("tmp")

# Archivo de configuración para guardar el estado del calendario
CONFIG_FILE = "tmp/sapse_config.json"

# Función para guardar la configuración
def guardar_configuracion():
    try:
        config = {
            "calendar_visible": calendar_visible
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        print(f"Configuración guardada: calendario {'visible' if calendar_visible else 'oculto'}")
    except Exception as e:
        print(f"Error al guardar la configuración: {e}")

# Función para cargar la configuración
def cargar_configuracion():
    global calendar_visible
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                calendar_visible = config.get("calendar_visible", True)
                print(f"Configuración cargada: calendario {'visible' if calendar_visible else 'oculto'}")
        else:
            calendar_visible = True
            print("Archivo de configuración no encontrado, usando valores predeterminados")
    except Exception as e:
        calendar_visible = True
        print(f"Error al cargar la configuración: {e}")

# Iniciar la GUI
root.mainloop()
