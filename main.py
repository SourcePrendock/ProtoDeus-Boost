# =============================================================================
#  main.py — Aplicación Principal ProtoDeus Boost
#  Sistema de optimización y herramientas para Windows.
#  Autor: Prendock | Requiere: Python 3.11+, customtkinter, Pillow
# =============================================================================

import sys
import os
import ctypes
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import multiprocessing
import subprocess


# =============================================================================
#  CONTROL DE PERMISOS DE ADMINISTRADOR
# =============================================================================

def is_admin():
    """Verifica si el proceso actual tiene privilegios de administrador de Windows."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Si no hay privilegios de admin, relanza la aplicación con elevación UAC y termina."""
    if not is_admin():
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)


# =============================================================================
#  IMPORTACIÓN DE MÓDULOS INTERNOS
# =============================================================================

import info_pc   # Detección de hardware del sistema (CPU, RAM, GPU, disco, OS)
import optimizer # Acciones de optimización: limpieza, red, registro, SSD, etc.
import tools     # Herramientas: red, licencia, reparaciones de Windows, Teams, OneDrive


# =============================================================================
#  UTILIDADES DE RECURSOS (compatible con PyInstaller)
# =============================================================================

def resource_path(relative):
    """
    Devuelve la ruta absoluta al recurso indicado.
    Funciona tanto en modo desarrollo como empaquetado con PyInstaller (_MEIPASS).
    """
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


# =============================================================================
#  PALETA DE COLORES — SISTEMA DE DISEÑO GLOBAL
#  Todos los paneles y widgets usan estas constantes para mantener consistencia.
# =============================================================================

VIOLET      = "#7C3AED"   # Violeta principal — botones de acción primaria
VIOLET_DARK = "#5B21B6"   # Violeta oscuro — hover de botones primarios
VIOLET_MED  = "#6D28D9"   # Violeta medio — acentos secundarios
CYAN        = "#06B6D4"   # Cian — acciones de red / secundarias
CYAN_DARK   = "#0891B2"   # Cian oscuro — hover de botones secundarios
BG_MAIN     = "#0A0A0F"   # Fondo principal de la ventana
BG_PANEL    = "#111118"   # Fondo del panel lateral y headers
BG_CARD     = "#1A1A26"   # Fondo de tarjetas de contenido
BG_CARD2    = "#16161F"   # Fondo de elementos internos de tarjetas
TEXT_MAIN   = "#F8FAFC"   # Texto principal (blanco casi puro)
TEXT_MUTED  = "#94A3B8"   # Texto secundario / subtítulos
TEXT_DIM    = "#64748B"   # Texto muy tenue / etiquetas de sección
SUCCESS     = "#10B981"   # Verde éxito — confirmaciones
WARNING     = "#F59E0B"   # Amarillo advertencia — alertas
ERROR       = "#EF4444"   # Rojo error — fallos críticos
BORDER      = "#2D2D45"   # Color de bordes de tarjetas y separadores
ORANGE      = "#F97316"   # Naranja — acciones de arranque / urgentes


# =============================================================================
#  CLASE PRINCIPAL DE LA APLICACIÓN
# =============================================================================

class ProtoDeusBoostApp(ctk.CTk):
    """
    Ventana raíz de la aplicación. Gestiona:
    - Layout principal: sidebar de navegación + área de contenido
    - Cambio entre paneles (secciones)
    - Carga del ícono de la barra de tareas
    """

    def __init__(self):
        super().__init__()
        self.title("ProtoDeus Boost")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self.configure(fg_color=BG_MAIN)

        # Cargar ícono para la barra de tareas y ventana (si existe el .ico)
        ico_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(ico_path):
            self.iconbitmap(ico_path)

        self._current_section = None
        self._build_layout()
        self._show_section("info")

    # ── Construcción del layout general (sidebar + área de contenido) ──
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Panel lateral de navegación ──
        self.sidebar = ctk.CTkFrame(
            self, width=240, fg_color=BG_PANEL,
            corner_radius=0, border_width=1, border_color=BORDER
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Logo y nombre de la aplicación en el sidebar
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 8), sticky="ew")
        ctk.CTkLabel(logo_frame, text="⚡", font=("Segoe UI", 32), text_color=VIOLET).pack(side="left", padx=(0, 8))
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="PROTODEUS",   font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="BOOST",       font=("Segoe UI", 11, "bold"), text_color=VIOLET).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="By Prendock", font=("Segoe UI", 9, "italic"), text_color=TEXT_DIM).pack(anchor="w")

        # Separador y etiqueta del menú
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 16))
        ctk.CTkLabel(self.sidebar, text="MENÚ PRINCIPAL", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(
            row=2, column=0, padx=20, pady=(0, 8), sticky="w"
        )

        # Botones de navegación — cada uno lleva a un panel distinto
        self._nav_buttons = {}
        nav_items = [
            ("info",      "🖥",  "Información PC"),
            ("optimizer", "⚡",  "Optimización"),
            ("tools",     "🔧",  "Herramientas"),
            ("winrepair", "🪟",  "Reparar Windows"),
            ("commands",  "💻",  "Comandos Útiles"),   # Nuevo panel de comandos
        ]
        for row_idx, (key, icon, label) in enumerate(nav_items, start=3):
            btn = self._make_nav_button(icon, label, key)
            btn.grid(row=row_idx, column=0, padx=12, pady=3, sticky="ew")
            self._nav_buttons[key] = btn

        # Separador inferior, versión y botón de salida
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=9, column=0, sticky="ew", padx=16, pady=12)
        ver_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ver_frame.grid(row=10, column=0, padx=20, pady=(0, 4), sticky="sw")
        ctk.CTkLabel(ver_frame, text="v1.3.0 | by Prendock", font=("Segoe UI", 9), text_color=TEXT_DIM).pack(anchor="w")
        ctk.CTkLabel(
            ver_frame, text="⚡ Software libre y open source\npara la comunidad — úsalo libremente",
            font=("Segoe UI", 8), text_color=VIOLET, justify="left", wraplength=200
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            self.sidebar, text="⏻  Salir", font=("Segoe UI", 13, "bold"),
            fg_color="#2D1B1B", hover_color="#5C1A1A", text_color="#FC8181",
            corner_radius=10, height=40, cursor="hand2", command=self._exit_app
        ).grid(row=11, column=0, padx=12, pady=(0, 20), sticky="ew")

        # ── Área de contenido principal (donde viven todos los paneles) ──
        self.content = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Crear todos los paneles y apilarlos — solo uno será visible a la vez
        self.panels = {
            "info":      InfoPanel(self.content),
            "optimizer": OptimizerPanel(self.content),
            "tools":     ToolsPanel(self.content),
            "winrepair": WindowsRepairPanel(self.content),
            "commands":  CommandsPanel(self.content),    # Nuevo panel de comandos
        }
        for p in self.panels.values():
            p.grid(row=0, column=0, sticky="nsew")

    # ── Crea un botón de navegación lateral ──
    def _make_nav_button(self, icon, label, key):
        return ctk.CTkButton(
            self.sidebar, text=f"  {icon}  {label}", font=("Segoe UI", 13),
            anchor="w", fg_color="transparent", hover_color=BG_CARD,
            text_color=TEXT_MUTED, corner_radius=10, height=44, cursor="hand2",
            command=lambda k=key: self._show_section(k),
        )

    # ── Cambia el panel visible y resalta el botón activo en el sidebar ──
    def _show_section(self, key):
        if self._current_section == key:
            return
        self._current_section = key
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=BG_CARD, text_color=TEXT_MAIN, border_width=1, border_color=VIOLET)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED, border_width=0)
        if hasattr(self, "panels") and key in self.panels:
            self.panels[key].tkraise()

    # ── Cierra completamente la aplicación ──
    def _exit_app(self):
        self.quit()
        self.destroy()
        sys.exit(0)


# =============================================================================
#  PANEL: INFORMACIÓN DEL SISTEMA
#  Muestra CPU, GPU, RAM, almacenamiento y SO detectados en tiempo real.
# =============================================================================

class InfoPanel(ctk.CTkFrame):
    """
    Panel que detecta y muestra el hardware del sistema en tarjetas organizadas.
    La carga de datos se hace en un hilo separado para no bloquear la UI.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_content()
        self._load_data()

    # ── Header fijo con título y subtítulo ──
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🖥  Información del Sistema", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Hardware detectado en tiempo real", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    # ── Área de scroll donde se renderizan las tarjetas de hardware ──
    def _build_content(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, corner_radius=0,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure((0, 1), weight=1)
        self.loading_label = ctk.CTkLabel(self.scroll, text="⏳ Cargando información del sistema...", font=("Segoe UI", 14), text_color=TEXT_MUTED)
        self.loading_label.grid(row=0, column=0, columnspan=2, pady=60)

    # ── Inicia la carga en hilo aparte para no congelar la UI ──
    def _load_data(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.loading_label = ctk.CTkLabel(self.scroll, text="⏳ Detectando hardware...", font=("Segoe UI", 14), text_color=TEXT_MUTED)
        self.loading_label.grid(row=0, column=0, columnspan=2, pady=60)
        threading.Thread(target=self._fetch_data, daemon=True).start()

    # ── Obtiene los datos de hardware (corre en hilo separado) ──
    def _fetch_data(self):
        data = info_pc.get_all_info()
        self.after(0, lambda: self._render_data(data))

    # ── Renderiza todas las tarjetas con los datos obtenidos ──
    def _render_data(self, data):
        for w in self.scroll.winfo_children():
            w.destroy()
        NI = "No identificado"

        # Tarjeta CPU
        cpu = data.get("cpu", {})
        cpu_card = self._make_card("🔲  PROCESADOR", row=0, col=0)
        self._fill_card(cpu_card, [
            ("Modelo",          cpu.get("nombre", NI)),
            ("Núcleos físicos", str(cpu.get("nucleos_fisicos", NI))),
            ("Hilos",           str(cpu.get("hilos", NI))),
            ("Frec. máxima",    f"{cpu.get('frecuencia_max_ghz', NI)} GHz"),
            ("Arquitectura",    cpu.get("arquitectura", NI)),
        ])

        # Tarjeta GPU
        gpus = data.get("gpu", [{}])
        gpu  = gpus[0] if gpus else {}
        gpu_card = self._make_card("🎮  TARJETA GRÁFICA", row=0, col=1)
        self._fill_card(gpu_card, [
            ("Modelo",     gpu.get("nombre", NI)),
            ("Driver",     gpu.get("driver_version", NI)),
            ("Resolución", gpu.get("resolucion", NI)),
            ("Refresco",   f"{gpu.get('refresh_hz', NI)} Hz"),
            ("Estado",     gpu.get("estado", NI)),
        ])

        # Tarjeta RAM con detalle de módulos físicos
        ram     = data.get("ram", {})
        ram_card = self._make_card("🧠  MEMORIA RAM", row=1, col=0)
        modulos = ram.get("modulos", [])
        rows_ram = [
            ("Total",         f"{ram.get('total_gb', NI)} GB"),
            ("En uso",        f"{ram.get('usada_gb', NI)} GB ({ram.get('porcentaje_uso','?')}%)"),
            ("Libre",         f"{ram.get('libre_gb', NI)} GB"),
            ("Tipo",          ram.get("tipo", NI)),
            ("Slots totales", str(ram.get("slots_totales", NI))),
            ("Slots en uso",  str(ram.get("slots_en_uso", NI))),
            ("Slots libres",  str(ram.get("slots_libres", NI))),
            ("Módulos",       f"{len(modulos)} módulo(s)" if modulos else NI),
        ]
        for m in modulos:
            rows_ram.append((f"  └ {m['slot']}", f"{m['capacidad_gb']} GB {m['tipo']} @ {m['velocidad_mhz']} MHz"))
        self._fill_card(ram_card, rows_ram)

        # Tarjeta de almacenamiento: discos físicos y particiones
        storage      = data.get("storage", {})
        storage_card = self._make_card("💾  ALMACENAMIENTO", row=1, col=1)
        rows_storage = []
        for disco in storage.get("discos_fisicos", []):
            rows_storage += [
                ("Modelo",    disco.get("modelo", NI)),
                ("Capacidad", f"{disco.get('capacidad_gb', NI)} GB"),
                ("Interfaz",  disco.get("interfaz", NI)),
                ("──────",    "──────"),
            ]
        for part in storage.get("particiones", []):
            rows_storage += [
                (f"Unidad {part['unidad']}", f"{part['total_gb']} GB total"),
                ("  Usado / Libre", f"{part['usado_gb']} / {part['libre_gb']} GB ({part['porcentaje']}%)"),
            ]
        if not rows_storage:
            rows_storage = [("", "No se detectaron unidades")]
        self._fill_card(storage_card, rows_storage)

        # Tarjeta del Sistema Operativo (ocupa ancho completo)
        os_info = data.get("os", {})
        os_card = self._make_card("🪟  SISTEMA OPERATIVO", row=2, col=0, colspan=2)
        self._fill_card(os_card, [
            ("Sistema",      os_info.get("nombre", NI)),
            ("Edición",      os_info.get("edicion", NI)),
            ("Versión",      os_info.get("version", NI)),
            ("Release",      os_info.get("release", NI)),
            ("Arquitectura", os_info.get("arquitectura", NI)),
        ])

    # ── Crea el frame de tarjeta con barra de color superior y título ──
    def _make_card(self, title, row, col, colspan=1):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        card.grid(row=row, column=col, columnspan=colspan, padx=14, pady=10, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(card, fg_color=VIOLET, height=3, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN, anchor="w").grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="w")
        return card

    # ── Rellena una tarjeta con filas clave-valor (o separadores) ──
    def _fill_card(self, card, rows):
        for i, (key, val) in enumerate(rows, start=2):
            if key == "──────":
                ctk.CTkFrame(card, height=1, fg_color=BORDER).grid(row=i, column=0, columnspan=2, sticky="ew", padx=12, pady=4)
                continue
            ctk.CTkLabel(card, text=key, font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w").grid(row=i, column=0, padx=(16, 8), pady=2, sticky="w")
            ctk.CTkLabel(card, text=str(val), font=("Segoe UI", 11, "bold"), text_color=TEXT_MAIN, anchor="w", wraplength=260).grid(row=i, column=1, padx=(0, 16), pady=2, sticky="w")


# =============================================================================
#  PANEL: OPTIMIZACIÓN DEL SISTEMA
#  Lista de acciones de limpieza y rendimiento ejecutadas en hilos separados.
# =============================================================================

class OptimizerPanel(ctk.CTkFrame):
    """
    Panel de optimización: presenta botones de acción (limpieza, red, SSD, etc.)
    y muestra el progreso y log de la acción en ejecución.
    Solo permite una acción a la vez (_running flag).
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._running = False
        self._build_header()
        self._build_content()

    # ── Header con título y descripción ──
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="⚡  Optimización del Sistema", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Herramientas de limpieza y rendimiento — requiere permisos de administrador", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    # ── Layout: botones a la izquierda, progreso y log a la derecha ──
    def _build_content(self):
        main = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        # Panel izquierdo: lista scrollable de botones de acción
        left = ctk.CTkScrollableFrame(
            main, fg_color=BG_PANEL, corner_radius=0, width=340,
            border_width=1, border_color=BORDER,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="ACCIONES DISPONIBLES", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(row=0, column=0, padx=20, pady=(20, 8), sticky="w")

        # Definición de acciones: (etiqueta, clave interna, función generadora, color)
        self._opt_buttons = {}
        actions = [
            ("🗑  Limpiar Temporales",        "temp",     optimizer.limpiar_temporales,        VIOLET),
            ("🧹  Limpieza Profunda",          "deep",     optimizer.limpieza_profunda,          VIOLET),
            ("🌐  Limpiar Navegadores",        "browsers", optimizer.limpiar_navegadores,        CYAN),
            ("🗂  Limpiar Registro",           "registry", optimizer.limpiar_registro,           CYAN),
            ("📡  Optimizar Red",              "net",      optimizer.optimizar_red,              CYAN),
            ("🎨  Optimizar Efectos Visuales", "visuals",  optimizer.optimizar_efectos_visuales, VIOLET),
            ("💿  Optimizar Disco (SSD)",      "ssd",      optimizer.optimizar_ssd,              VIOLET),
            ("🔧  Desfragmentar HDD",          "hdd",      optimizer.desfragmentar_hdd,          CYAN),
            ("🧠  Liberar RAM",                "ram",      optimizer.liberar_ram,                WARNING),
            ("↩  Restaurar SysMain",          "restore",  optimizer.restaurar_sysmain,          TEXT_DIM),
            ("🌐  Limpiar DNS Cache",          "dns",      optimizer.limpiar_dns,                CYAN),
        ]
        for i, (label, key, func, color) in enumerate(actions):
            btn = ctk.CTkButton(
                left, text=label, font=("Segoe UI", 12), anchor="w",
                fg_color=BG_CARD, hover_color=BG_CARD2, text_color=TEXT_MAIN,
                corner_radius=10, height=46, border_width=1, border_color=BORDER, cursor="hand2",
                command=lambda f=func, k=key, c=color: self._run_action(f, k, c)
            )
            btn.grid(row=i + 1, column=0, padx=12, pady=4, sticky="ew")
            self._opt_buttons[key] = btn

        # Panel derecho: barra de progreso + caja de log
        right = ctk.CTkFrame(main, fg_color=BG_MAIN, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Tarjeta de progreso (estado actual + barra + porcentaje)
        prog_card = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        prog_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        prog_card.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(prog_card, text="Selecciona una acción para comenzar", font=("Segoe UI", 13), text_color=TEXT_MUTED, anchor="w")
        self.status_label.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(prog_card, progress_color=VIOLET, fg_color=BG_CARD2, height=8, corner_radius=4)
        self.progress_bar.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")
        self.progress_bar.set(0)
        self.pct_label = ctk.CTkLabel(prog_card, text="0%", font=("Segoe UI", 11, "bold"), text_color=VIOLET)
        self.pct_label.grid(row=1, column=1, padx=(0, 16), pady=(0, 14))

        # Tarjeta de log de actividad (caja de texto con scroll)
        log_card = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        log_card.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)
        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        ctk.CTkLabel(log_hdr, text="📋  Registro de Actividad", font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkButton(log_hdr, text="Limpiar", width=70, height=26, fg_color=BG_CARD2, hover_color=BORDER, font=("Segoe UI", 10), corner_radius=6, cursor="hand2", command=self._clear_log).pack(side="right")
        self.log_box = ctk.CTkTextbox(log_card, fg_color=BG_CARD2, corner_radius=10, text_color=TEXT_MUTED, font=("Cascadia Code", 11), wrap="word", border_width=0)
        self.log_box.grid(row=1, column=0, padx=10, pady=(8, 10), sticky="nsew")
        self.log_box.configure(state="disabled")

    # ── Muestra confirmación y lanza la acción en hilo separado ──
    def _run_action(self, func, key, color):
        if self._running:
            return
        confirmaciones = {
            "temp":     ("Limpiar Archivos Temporales", "Se eliminarán todos los archivos temporales del sistema y del usuario.\n\n¿Deseas continuar?"),
            "deep":     ("Limpieza Profunda", "Se realizará una limpieza profunda del sistema incluyendo cachés y archivos residuales.\n\n¿Deseas continuar?"),
            "browsers": ("Limpiar Caché de Navegadores", "Se eliminará el caché de Chrome, Edge, Firefox, Brave y Opera.\nSe cerrarán sesiones locales en caché.\n\n¿Deseas continuar?"),
            "registry": ("Limpiar Registro de Windows", "Se ejecutará una limpieza del registro del sistema.\nSe recomienda crear un punto de restauración antes.\n\n¿Deseas continuar?"),
            "net":      ("Optimizar Red", "Se modificarán parámetros de red del sistema para mejorar el rendimiento.\n\n¿Deseas continuar?"),
            "visuals":  ("Optimizar Efectos Visuales", "Se reducirán las animaciones y efectos visuales de Windows para mejorar el rendimiento.\n\n¿Deseas continuar?"),
            "ssd":      ("Optimizar Disco SSD", "Se ejecutarán optimizaciones específicas para SSD (TRIM, desactivar defrag, etc.).\n\n¿Deseas continuar?"),
            "hdd":      ("Desfragmentar HDD", "Se desfragmentará el disco duro. Este proceso puede tardar varios minutos.\n\nNO ejecutar en SSD.\n\n¿Deseas continuar?"),
            "ram":      ("Liberar RAM", "Se forzará la liberación de memoria RAM inactiva.\nAlgunos procesos pueden tardar en reiniciarse.\n\n¿Deseas continuar?"),
            "restore":  ("Restaurar SysMain", "Se restaurará el servicio SysMain (Superfetch) a su estado predeterminado.\n\n¿Deseas continuar?"),
            "dns":      ("Limpiar Caché DNS", "Se eliminará la caché DNS del sistema. La navegación puede ser levemente más lenta unos minutos.\n\n¿Deseas continuar?"),
        }
        titulo, mensaje = confirmaciones.get(key, ("Confirmar acción", "¿Deseas ejecutar esta operación?"))
        if not messagebox.askyesno(f"⚠ {titulo}", mensaje, icon="warning"):
            return

        self._running = True
        for btn in self._opt_buttons.values():
            btn.configure(state="disabled")
        self.progress_bar.configure(progress_color=color)
        self.progress_bar.set(0)
        self._log(f"\n{'─'*50}\n▶ Iniciando: {key.upper()}\n{'─'*50}")

        # Hilo worker que ejecuta la función generadora y envía actualizaciones a la UI
        def worker():
            try:
                for msg, pct in func():
                    self.after(0, lambda m=msg, p=pct: self._update_progress(m, p))
            except Exception as e:
                self.after(0, lambda: self._log(f"❌ Error: {e}"))
            finally:
                self.after(0, self._finish_action)

        threading.Thread(target=worker, daemon=True).start()

    # ── Actualiza barra de progreso y log con el mensaje del worker ──
    def _update_progress(self, msg, pct):
        self.status_label.configure(text=msg)
        self.progress_bar.set(pct / 100)
        self.pct_label.configure(text=f"{pct}%")
        self._log(msg)

    # ── Restaura el estado de los botones al terminar ──
    def _finish_action(self):
        self._running = False
        for btn in self._opt_buttons.values():
            btn.configure(state="normal")
        self.status_label.configure(text="✅ Operación completada")

    # ── Agrega una línea al log de actividad ──
    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ── Limpia el log y resetea el estado visual ──
    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.status_label.configure(text="Selecciona una acción para comenzar")
        self.progress_bar.set(0)
        self.pct_label.configure(text="0%")


# =============================================================================
#  PANEL: HERRAMIENTAS DEL SISTEMA
#  Restablecimiento de red, detección de licencia, limpieza de Teams y OneDrive.
# =============================================================================

class ToolsPanel(ctk.CTkFrame):
    """
    Panel de herramientas específicas: restablecimiento de red, información
    de licencia de Windows, limpieza de Microsoft Teams y OneDrive.
    Cada herramienta tiene su propia tarjeta con progreso y log.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._running = False
        self._build_header()
        self._build_content()

    # ── Header con título y descripción ──
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🔧  Herramientas del Sistema", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Diagnóstico de red, licencias y limpieza profunda", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    # ── Construye las cuatro tarjetas de herramientas ──
    def _build_content(self):
        main = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN, corner_radius=0, scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        # ── Tarjeta 1: Restablecer Red ──
        net_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        net_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        net_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(net_card, height=3, fg_color=CYAN, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr_f = ctk.CTkFrame(net_card, fg_color="transparent")
        hdr_f.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")
        ctk.CTkLabel(hdr_f, text="📡  Restablecer Red", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.net_btn = ctk.CTkButton(hdr_f, text="Ejecutar Restablecimiento", width=200, height=36, fg_color=CYAN_DARK, hover_color=CYAN, font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2", command=self._run_net_reset)
        self.net_btn.pack(side="right")
        ctk.CTkLabel(net_card, text="Equivalente al restablecimiento de red de Windows 10/11.\nResetea Winsock, pila TCP/IP, DNS, firewall y renueva la IP.\n⚠ Se recomienda reiniciar el PC al finalizar.", font=("Segoe UI", 11), text_color=TEXT_MUTED, justify="left", anchor="w", wraplength=700).grid(row=2, column=0, columnspan=2, padx=16, pady=(6, 8), sticky="w")
        self.net_progress = ctk.CTkProgressBar(net_card, progress_color=CYAN, fg_color=BG_CARD2, height=6)
        self.net_progress.grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")
        self.net_progress.set(0)
        self.net_status = ctk.CTkLabel(net_card, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w")
        self.net_status.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")
        self.net_log = ctk.CTkTextbox(net_card, fg_color=BG_CARD2, corner_radius=8, text_color=TEXT_MUTED, font=("Cascadia Code", 10), height=120, wrap="word", border_width=0)
        self.net_log.grid(row=5, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="ew")
        self.net_log.configure(state="disabled")

        # ── Tarjeta 2: Información de Licencia Windows ──
        lic_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        lic_card.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew")
        lic_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(lic_card, height=3, fg_color=VIOLET, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr2_f = ctk.CTkFrame(lic_card, fg_color="transparent")
        hdr2_f.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")
        ctk.CTkLabel(hdr2_f, text="🔑  Información de Licencia Windows", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.lic_btn = ctk.CTkButton(hdr2_f, text="Detectar Licencia", width=180, height=36, fg_color=VIOLET, hover_color=VIOLET_DARK, font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2", command=self._detect_license)
        self.lic_btn.pack(side="right")
        ctk.CTkLabel(lic_card, text="Muestra la clave de Windows instalada, la clave BIOS/UEFI (OEM),\ny detecta el tipo de licencia: OEM, KMS Genérica, COA o Retail.", font=("Segoe UI", 11), text_color=TEXT_MUTED, justify="left", anchor="w", wraplength=700).grid(row=2, column=0, columnspan=2, padx=16, pady=(6, 12), sticky="w")
        self.lic_result = ctk.CTkFrame(lic_card, fg_color=BG_CARD2, corner_radius=10)
        self.lic_result.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="ew")
        self.lic_result.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.lic_result, text="Haz clic en 'Detectar Licencia' para comenzar", font=("Segoe UI", 12), text_color=TEXT_DIM).grid(row=0, column=0, columnspan=2, padx=20, pady=30)

        # ── Tarjeta 3: Limpiar Microsoft Teams ──
        teams_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        teams_card.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        teams_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(teams_card, height=3, fg_color=VIOLET, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr3_f = ctk.CTkFrame(teams_card, fg_color="transparent")
        hdr3_f.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")
        ctk.CTkLabel(hdr3_f, text="🗑  Limpiar Microsoft Teams", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.teams_btn = ctk.CTkButton(hdr3_f, text="Limpiar Teams", width=180, height=36, fg_color=VIOLET, hover_color=VIOLET_DARK, font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2", command=self._run_teams_reset)
        self.teams_btn.pack(side="right")
        ctk.CTkLabel(teams_card, text="Elimina registros, configuraciones, carpetas y cuentas iniciadas de Microsoft Teams para dejarlo como nuevo.", font=("Segoe UI", 11), text_color=TEXT_MUTED, justify="left", anchor="w", wraplength=700).grid(row=2, column=0, columnspan=2, padx=16, pady=(6, 12), sticky="w")
        self.teams_progress = ctk.CTkProgressBar(teams_card, progress_color=VIOLET, fg_color=BG_CARD2, height=6)
        self.teams_progress.grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")
        self.teams_progress.set(0)
        self.teams_status = ctk.CTkLabel(teams_card, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w")
        self.teams_status.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")
        self.teams_log = ctk.CTkTextbox(teams_card, fg_color=BG_CARD2, corner_radius=8, text_color=TEXT_MUTED, font=("Cascadia Code", 10), height=120, wrap="word", border_width=0)
        self.teams_log.grid(row=5, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="ew")
        self.teams_log.configure(state="disabled")

        # ── Tarjeta 4: Limpiar OneDrive ──
        od_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        od_card.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        od_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(od_card, height=3, fg_color=CYAN, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr4_f = ctk.CTkFrame(od_card, fg_color="transparent")
        hdr4_f.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")
        ctk.CTkLabel(hdr4_f, text="☁  Limpiar OneDrive", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.od_btn = ctk.CTkButton(hdr4_f, text="Limpiar OneDrive", width=180, height=36, fg_color=CYAN_DARK, hover_color=CYAN, font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2", command=self._run_onedrive_reset)
        self.od_btn.pack(side="right")
        ctk.CTkLabel(od_card, text="Elimina cuentas, carpetas de datos locales, registros y entradas de OneDrive para restaurarlo completamente.", font=("Segoe UI", 11), text_color=TEXT_MUTED, justify="left", anchor="w", wraplength=700).grid(row=2, column=0, columnspan=2, padx=16, pady=(6, 12), sticky="w")
        self.od_progress = ctk.CTkProgressBar(od_card, progress_color=CYAN, fg_color=BG_CARD2, height=6)
        self.od_progress.grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")
        self.od_progress.set(0)
        self.od_status = ctk.CTkLabel(od_card, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w")
        self.od_status.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")
        self.od_log = ctk.CTkTextbox(od_card, fg_color=BG_CARD2, corner_radius=8, text_color=TEXT_MUTED, font=("Cascadia Code", 10), height=120, wrap="word", border_width=0)
        self.od_log.grid(row=5, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="ew")
        self.od_log.configure(state="disabled")

    # ── Handlers de cada herramienta (restablecer red) ──
    def _run_net_reset(self):
        if self._running:
            return
        self._running = True
        self.net_btn.configure(state="disabled", text="⏳ Ejecutando...")
        self.net_log.configure(state="normal")
        self.net_log.delete("1.0", "end")
        self.net_log.configure(state="disabled")
        self.net_progress.set(0)
        self.net_status.configure(text="Iniciando restablecimiento de red...")

        def worker():
            try:
                for msg, pct in tools.restablecer_red():
                    self.after(0, lambda m=msg, p=pct: self._update_net(m, p))
            except Exception as e:
                self.after(0, lambda: self._net_log(f"❌ Error: {e}"))
            finally:
                self.after(0, self._finish_net)

        threading.Thread(target=worker, daemon=True).start()

    def _update_net(self, msg, pct):
        self.net_status.configure(text=msg)
        self.net_progress.set(pct / 100)
        self._net_log(msg)

    def _net_log(self, msg):
        self.net_log.configure(state="normal")
        self.net_log.insert("end", msg + "\n")
        self.net_log.see("end")
        self.net_log.configure(state="disabled")

    def _finish_net(self):
        self._running = False
        self.net_btn.configure(state="normal", text="Ejecutar Restablecimiento")

    # ── Handler de detección de licencia Windows ──
    def _detect_license(self):
        if self._running:
            return
        self._running = True
        self.lic_btn.configure(state="disabled", text="⏳ Detectando...")
        for w in self.lic_result.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.lic_result, text="⏳ Analizando licencia de Windows...", font=("Segoe UI", 12), text_color=TEXT_MUTED).grid(row=0, column=0, columnspan=2, padx=20, pady=30)

        def worker():
            data = tools.get_license_info()
            self.after(0, lambda: self._render_license(data))

        threading.Thread(target=worker, daemon=True).start()

    # ── Renderiza los datos de licencia en la tarjeta ──
    def _render_license(self, data):
        self._running = False
        self.lic_btn.configure(state="normal", text="Detectar Licencia")
        for w in self.lic_result.winfo_children():
            w.destroy()
        tipo = data.get("tipo", "Desconocido")
        tipo_lower = tipo.lower()
        badge_color = WARNING if "kms" in tipo_lower else CYAN if "oem" in tipo_lower else SUCCESS if "retail" in tipo_lower else VIOLET if "coa" in tipo_lower else TEXT_DIM
        badge_frame = ctk.CTkFrame(self.lic_result, fg_color=badge_color, corner_radius=8)
        badge_frame.grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 12), sticky="w")
        ctk.CTkLabel(badge_frame, text=f"  {tipo}  ", font=("Segoe UI", 13, "bold"), text_color="#000000").pack(padx=4, pady=4)
        desc = data.get("descripcion_tipo", "")
        if desc:
            ctk.CTkLabel(self.lic_result, text=desc, font=("Segoe UI", 11), text_color=TEXT_MUTED, wraplength=650, anchor="w", justify="left").grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")
        fields = [
            ("Licencia instalada",   data.get("clave_instalada", "No disponible")),
            ("Licencia BIOS/UEFI",   data.get("clave_bios", "No disponible")),
            ("Edición de Windows",   data.get("edicion", "Desconocida")),
            ("Estado de activación", data.get("estado_activacion", "Desconocido")),
            ("Nombre de licencia",   data.get("nombre_licencia", "No identificado")),
            ("Descripción",          data.get("descripcion", "No identificado")),
            ("Expiración",           data.get("expiracion", "No identificado")),
        ]
        for i, (key, val) in enumerate(fields):
            ctk.CTkLabel(self.lic_result, text=key + ":", font=("Segoe UI", 11), text_color=TEXT_DIM, anchor="w").grid(row=i + 2, column=0, padx=(16, 8), pady=3, sticky="w")
            is_key = "licencia" in key.lower() or "clave" in key.lower()
            font = ("Cascadia Code", 11, "bold") if is_key else ("Segoe UI", 11, "bold")
            val_color = CYAN if (is_key and val not in ["No disponible", "No identificado"]) else TEXT_MAIN
            ctk.CTkLabel(self.lic_result, text=str(val), font=font, text_color=val_color, anchor="w", wraplength=500).grid(row=i + 2, column=1, padx=(0, 16), pady=3, sticky="w")
        if data.get("error"):
            ctk.CTkLabel(self.lic_result, text=f"⚠ Nota: {data['error']}", font=("Segoe UI", 10), text_color=WARNING, wraplength=600, anchor="w").grid(row=len(fields) + 2, column=0, columnspan=2, padx=16, pady=(8, 16), sticky="w")
        else:
            ctk.CTkFrame(self.lic_result, height=16, fg_color="transparent").grid(row=len(fields) + 2, column=0)

    # ── Handler de limpieza de Teams ──
    def _run_teams_reset(self):
        if self._running:
            return
        self._running = True
        self.teams_btn.configure(state="disabled", text="⏳ Ejecutando...")
        self.teams_log.configure(state="normal")
        self.teams_log.delete("1.0", "end")
        self.teams_log.configure(state="disabled")
        self.teams_progress.set(0)
        self.teams_status.configure(text="Iniciando limpieza de Teams...")

        def worker():
            try:
                for msg, pct in tools.limpiar_teams():
                    self.after(0, lambda m=msg, p=pct: self._update_teams(m, p))
            except Exception as e:
                self.after(0, lambda: self._teams_log(f"❌ Error: {e}"))
            finally:
                self.after(0, self._finish_teams)

        threading.Thread(target=worker, daemon=True).start()

    def _update_teams(self, msg, pct):
        self.teams_status.configure(text=msg)
        self.teams_progress.set(pct / 100)
        self._teams_log(msg)

    def _teams_log(self, msg):
        self.teams_log.configure(state="normal")
        self.teams_log.insert("end", msg + "\n")
        self.teams_log.see("end")
        self.teams_log.configure(state="disabled")

    def _finish_teams(self):
        self._running = False
        self.teams_btn.configure(state="normal", text="Limpiar Teams")

    # ── Handler de limpieza de OneDrive ──
    def _run_onedrive_reset(self):
        if self._running:
            return
        self._running = True
        self.od_btn.configure(state="disabled", text="⏳ Ejecutando...")
        self.od_log.configure(state="normal")
        self.od_log.delete("1.0", "end")
        self.od_log.configure(state="disabled")
        self.od_progress.set(0)
        self.od_status.configure(text="Iniciando limpieza de OneDrive...")

        def worker():
            try:
                for msg, pct in tools.limpiar_onedrive():
                    self.after(0, lambda m=msg, p=pct: self._update_od(m, p))
            except Exception as e:
                self.after(0, lambda: self._od_log(f"❌ Error: {e}"))
            finally:
                self.after(0, self._finish_od)

        threading.Thread(target=worker, daemon=True).start()

    def _update_od(self, msg, pct):
        self.od_status.configure(text=msg)
        self.od_progress.set(pct / 100)
        self._od_log(msg)

    def _od_log(self, msg):
        self.od_log.configure(state="normal")
        self.od_log.insert("end", msg + "\n")
        self.od_log.see("end")
        self.od_log.configure(state="disabled")

    def _finish_od(self):
        self._running = False
        self.od_btn.configure(state="normal", text="Limpiar OneDrive")


# =============================================================================
#  PANEL: REPARAR WINDOWS
#  Lista de reparaciones del sistema con progreso y log de cada operación.
# =============================================================================

class WindowsRepairPanel(ctk.CTkFrame):
    """
    Panel de reparaciones de Windows. Muestra todas las reparaciones disponibles
    definidas en tools.REPARACIONES_WINDOWS, permite ejecutarlas con seguimiento
    de progreso en tiempo real y log detallado.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._running = False
        self._build_header()
        self._build_content()

    # ── Header con título y descripción ──
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🪟  Reparación de Windows", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Soluciones automáticas para errores comunes — ejecutadas como administrador", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    # ── Construye el panel izquierdo (lista de reparaciones) y derecho (progreso/log) ──
    def _build_content(self):
        main = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        # Panel izquierdo: tarjetas de reparación con botón Ejecutar
        left = ctk.CTkScrollableFrame(
            main, fg_color=BG_PANEL, corner_radius=0, width=380,
            border_width=1, border_color=BORDER,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="REPARACIONES DISPONIBLES", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(row=0, column=0, padx=20, pady=(20, 8), sticky="w")

        # Color asignado a cada botón de reparación
        self._repair_buttons = {}
        repair_colors = {
            "startup": ORANGE,   "lockscreen": CYAN,    "settings": ORANGE,
            "sfc":     SUCCESS,  "store":      CYAN,    "updates":  WARNING,
            "taskbar": VIOLET,   "audio":      CYAN,    "drivers":  VIOLET,
            "defender": SUCCESS, "startmenu":  CYAN,
        }

        for i, (key, repair) in enumerate(tools.REPARACIONES_WINDOWS.items()):
            color = repair_colors.get(key, VIOLET)
            est   = repair.get("tiempo_estimado", "")

            # Tarjeta de reparación: nombre, descripción, tiempo estimado y botón
            btn_frame = ctk.CTkFrame(left, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER)
            btn_frame.grid(row=i + 1, column=0, padx=12, pady=4, sticky="ew")
            btn_frame.grid_columnconfigure(0, weight=1)

            name_row = ctk.CTkFrame(btn_frame, fg_color="transparent")
            name_row.grid(row=0, column=0, padx=12, pady=(10, 0), sticky="ew")
            name_row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(name_row, text=repair["nombre"], font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN, anchor="w").grid(row=0, column=0, sticky="w")
            if est:
                ctk.CTkLabel(name_row, text=f"⏱ {est}", font=("Segoe UI", 9), text_color=TEXT_DIM, anchor="e").grid(row=0, column=1, padx=(8, 0), sticky="e")

            ctk.CTkLabel(btn_frame, text=repair["descripcion"], font=("Segoe UI", 10), text_color=TEXT_MUTED, anchor="w", wraplength=290, justify="left").grid(row=1, column=0, padx=12, pady=(2, 8), sticky="w")

            btn = ctk.CTkButton(
                btn_frame, text="Ejecutar", width=90, height=30,
                fg_color=color, hover_color=VIOLET_DARK if color == VIOLET else CYAN_DARK,
                font=("Segoe UI", 11, "bold"), corner_radius=8, cursor="hand2",
                command=lambda k=key: self._run_repair(k)
            )
            btn.grid(row=0, column=1, rowspan=2, padx=12, pady=8)
            self._repair_buttons[key] = btn

        # Panel derecho: progreso + log + nota de advertencia
        right = ctk.CTkFrame(main, fg_color=BG_MAIN, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Tarjeta de progreso de la reparación en curso
        prog_card = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        prog_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        prog_card.grid_columnconfigure(0, weight=1)
        self.repair_status = ctk.CTkLabel(prog_card, text="Selecciona una reparación para comenzar", font=("Segoe UI", 13), text_color=TEXT_MUTED, anchor="w")
        self.repair_status.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="ew")
        self.repair_progress = ctk.CTkProgressBar(prog_card, progress_color=VIOLET, fg_color=BG_CARD2, height=8, corner_radius=4)
        self.repair_progress.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")
        self.repair_progress.set(0)
        self.repair_pct = ctk.CTkLabel(prog_card, text="0%", font=("Segoe UI", 11, "bold"), text_color=VIOLET)
        self.repair_pct.grid(row=1, column=1, padx=(0, 16), pady=(0, 14))

        # Caja de log de la reparación
        log_card = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        log_card.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)
        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        ctk.CTkLabel(log_hdr, text="📋  Registro de Reparación", font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkButton(log_hdr, text="Limpiar", width=70, height=26, fg_color=BG_CARD2, hover_color=BORDER, font=("Segoe UI", 10), corner_radius=6, cursor="hand2", command=self._clear_log).pack(side="right")
        self.repair_log = ctk.CTkTextbox(log_card, fg_color=BG_CARD2, corner_radius=10, text_color=TEXT_MUTED, font=("Cascadia Code", 11), wrap="word", border_width=0)
        self.repair_log.grid(row=1, column=0, padx=10, pady=(8, 10), sticky="nsew")
        self.repair_log.configure(state="disabled")

        # Tarjeta de advertencia general
        warning_card = ctk.CTkFrame(right, fg_color="#1A1208", corner_radius=10, border_width=1, border_color=WARNING)
        warning_card.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(warning_card, text="⚠  Todas las reparaciones se ejecutan con permisos de administrador. Algunas pueden tardar varios minutos.", font=("Segoe UI", 11), text_color=WARNING, wraplength=600, justify="left", anchor="w").grid(padx=16, pady=10, sticky="w")

    # ── Inicia la reparación seleccionada en un hilo separado ──
    def _run_repair(self, key):
        if self._running:
            return
        self._running = True
        for btn in self._repair_buttons.values():
            btn.configure(state="disabled")
        repair = tools.REPARACIONES_WINDOWS.get(key, {})
        nombre = repair.get("nombre", key)
        est    = repair.get("tiempo_estimado", "desconocido")
        self.repair_progress.set(0)
        self._log(f"\n{'─'*50}\n▶ {nombre}\n⏱ Tiempo estimado: {est}\n{'─'*50}")

        def worker():
            try:
                for msg, pct in tools.reparar_windows(key):
                    self.after(0, lambda m=msg, p=pct: self._update(m, p))
            except Exception as e:
                self.after(0, lambda: self._log(f"❌ Error: {e}"))
            finally:
                self.after(0, self._finish)

        threading.Thread(target=worker, daemon=True).start()

    # ── Actualiza la barra de progreso y el log ──
    def _update(self, msg, pct):
        self.repair_status.configure(text=msg)
        self.repair_progress.set(pct / 100)
        self.repair_pct.configure(text=f"{pct}%")
        self._log(msg)

    # ── Restaura el estado de los botones al completar la reparación ──
    def _finish(self):
        self._running = False
        for btn in self._repair_buttons.values():
            btn.configure(state="normal")
        self.repair_status.configure(text="✅ Reparación completada")

    # ── Agrega una línea al log de reparación ──
    def _log(self, msg):
        self.repair_log.configure(state="normal")
        self.repair_log.insert("end", msg + "\n")
        self.repair_log.see("end")
        self.repair_log.configure(state="disabled")

    # ── Limpia el log y resetea la barra de progreso ──
    def _clear_log(self):
        self.repair_log.configure(state="normal")
        self.repair_log.delete("1.0", "end")
        self.repair_log.configure(state="disabled")
        self.repair_status.configure(text="Selecciona una reparación para comenzar")
        self.repair_progress.set(0)
        self.repair_pct.configure(text="0%")


# =============================================================================
#  PANEL: COMANDOS ÚTILES
#  Tres secciones: Windows 10, Windows 11 y Office.
#  Cada comando tiene un botón que lo ejecuta en PowerShell o CMD visibles.
#  - Windows 10 y 11: se ejecutan en PowerShell (ventana visible con resultado)
#  - Office: se ejecutan en CMD (ventana visible con resultado)
# =============================================================================

class CommandsPanel(ctk.CTkFrame):
    """
    Panel de comandos útiles clasificados por categoría.
    Al hacer clic en 'Ejecutar', abre PowerShell o CMD con la ventana visible
    para que el usuario pueda ver el comando escrito y su salida en tiempo real.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_content()

    # ── Header con título y descripción ──
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="💻  Comandos Útiles", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Comandos de diagnóstico para Windows 10, Windows 11 y Office", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    # ── Construye las tres tarjetas de categorías con sus comandos ──
    def _build_content(self):
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, corner_radius=0,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # ── Definición de comandos por categoría ──
        # Formato: (etiqueta_legible, comando, tipo)
        # tipo: "ps" = PowerShell (visible), "cmd" = CMD (visible)

        win10_commands = [
            ("Key BIOS (OA3)",          "wmic path softwarelicensingservice get OA3xOriginalProductKey",                   "ps"),
            ("Key Instalada (slmgr)",   "cscript c:/windows/system32/slmgr.vbs -dli",                                      "cmd"),
            ("Ver serial equipo",       "wmic bios get serialnumber",                                                       "ps"),
            ("Ver modelo equipo",       "wmic csproduct get name",                                                          "ps"),
            ("Ver serial procesador",   "wmic cpu get ProcessorId",                                                         "ps"),
            ("Ver MAC",                 "getmac",                                                                           "ps"),
        ]

        win11_commands = [
            ("Key BIOS (OA3)",          "(Get-WmiObject -Query 'SELECT * FROM SoftwareLicensingService').OA3xOriginalProductKey",  "ps"),
            ("Key Instalada (slmgr)",   "cscript c:/windows/system32/slmgr.vbs -dli",                                              "cmd"),
            ("Ver serial equipo",       "(Get-WmiObject -Class Win32_BIOS).SerialNumber",                                          "ps"),
            ("Ver serial procesador",   "Get-WmiObject -Class Win32_Processor | Select-Object ProcessorId",                        "ps"),
            ("Ver modelo equipo",       "Get-CimInstance -ClassName Win32_ComputerSystem",                                         "ps"),
            ("Ver MAC",                 "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress, InterfaceType", "ps"),
        ]

        office_commands = [
            ("Carpeta directa",          "cscript ospp.vbs /dstatus",                                                             "cmd"),
            ("2016-2025 Key x64",        'cscript "%ProgramFiles%\\Microsoft Office\\Office16\\ospp.vbs" /dstatus',               "cmd"),
            ("2016-2025 Key x86",        'cscript "%ProgramFiles(x86)%\\Microsoft Office\\Office16\\ospp.vbs" /dstatus',          "cmd"),
            ("2013 Key x64",             'cscript "%ProgramFiles%\\Microsoft Office\\Office15\\ospp.vbs" /dstatus',               "cmd"),
            ("2013 Key x86",             'cscript "%ProgramFiles(x86)%\\Microsoft Office\\Office15\\ospp.vbs" /dstatus',          "cmd"),
            ("2010 Key x64",             'cscript "%ProgramFiles%\\Microsoft Office\\Office14\\ospp.vbs" /dstatus',               "cmd"),
            ("2010 Key x86",             'cscript "%ProgramFiles(x86)%\\Microsoft Office\\Office14\\ospp.vbs" /dstatus',          "cmd"),
            ("Borrar Key 2016-2025 x64", 'cscript "%ProgramFiles%\\Microsoft Office\\Office16\\ospp.vbs" /unpkey:',               "cmd"),
            ("Borrar Key 2016-2025 x86", 'cscript "%ProgramFiles(x86)%\\Microsoft Office\\Office16\\ospp.vbs" /unpkey:',          "cmd"),
            ("Borrar claves 2013 x64",   'cscript "%ProgramFiles%\\Microsoft Office\\Office15\\ospp.vbs" /unpkey:',               "cmd"),
            ("Borrar claves 2013 x86",   'cscript "%ProgramFiles(x86)%\\Microsoft Office\\Office15\\ospp.vbs" /unpkey:',          "cmd"),
            ("Borrar claves 2010 x64",   'cscript "%ProgramFiles%\\Microsoft Office\\Office14\\ospp.vbs" /unpkey:',               "cmd"),
            ("Borrar claves 2010 x86",   'cscript "%ProgramFiles(x86)%\\Microsoft Office\\Office14\\ospp.vbs" /unpkey:',          "cmd"),
        ]

        inicio_rapido_commands = [
            ("Comprobar inicio rápido",  "Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power' -Name 'HiberbootEnabled'",  "ps"),
            ("Desactivar inicio rápido", "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power' -Name 'HiberbootEnabled' -Value 0", "ps"),
        ]

        # ── Renderizar cada categoría como una tarjeta ──
        categories = [
            ("🖥  Comandos Windows 10",   win10_commands,          CYAN),
            ("🪟  Comandos Windows 11",   win11_commands,          VIOLET),
            ("📦  Comandos Office",       office_commands,         ORANGE),
            ("⚡  Inicio Rápido",         inicio_rapido_commands,  WARNING),
        ]

        for row_idx, (cat_title, cmds, accent_color) in enumerate(categories):
            self._build_command_card(scroll, row_idx, cat_title, cmds, accent_color)

    # ── Construye una tarjeta de categoría con todos sus comandos ──
    def _build_command_card(self, parent, row, title, commands, accent_color):
        """
        Crea una tarjeta visual que agrupa comandos de una misma categoría.
        Cada fila tiene: etiqueta del comando + campo de texto con el comando + botón Ejecutar.
        """
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, padx=20, pady=(16 if row == 0 else 10, 10), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # Barra de color superior como acento visual de la categoría
        ctk.CTkFrame(card, height=3, fg_color=accent_color, corner_radius=2).grid(
            row=0, column=0, sticky="ew"
        )

        # Título de la categoría
        ctk.CTkLabel(
            card, text=title, font=("Segoe UI", 15, "bold"),
            text_color=TEXT_MAIN, anchor="w"
        ).grid(row=1, column=0, padx=18, pady=(14, 10), sticky="w")

        # Separador visual debajo del título
        ctk.CTkFrame(card, height=1, fg_color=BORDER, corner_radius=0).grid(
            row=2, column=0, sticky="ew", padx=14, pady=(0, 10)
        )

        # Filas de comandos: etiqueta | campo de texto (readonly) | botón Ejecutar
        for cmd_idx, (label, cmd, cmd_type) in enumerate(commands):
            row_frame = ctk.CTkFrame(card, fg_color="transparent")
            row_frame.grid(row=cmd_idx + 3, column=0, padx=14, pady=4, sticky="ew")
            row_frame.grid_columnconfigure(1, weight=1)

            # Etiqueta descriptiva del comando (nombre legible)
            ctk.CTkLabel(
                row_frame, text=label,
                font=("Segoe UI", 11, "bold"), text_color=TEXT_MUTED,
                anchor="w", width=200
            ).grid(row=0, column=0, padx=(0, 10), sticky="w")

            # Campo de texto readonly que muestra el comando exacto
            cmd_entry = ctk.CTkEntry(
                row_frame, font=("Cascadia Code", 10),
                fg_color=BG_CARD2, border_color=BORDER, text_color=TEXT_DIM,
                border_width=1, corner_radius=6, height=32
            )
            cmd_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
            cmd_entry.insert(0, cmd)
            cmd_entry.configure(state="disabled")  # Solo lectura, no editable

            # Botón Ejecutar: abre PowerShell o CMD en ventana visible según cmd_type
            exec_btn = ctk.CTkButton(
                row_frame,
                text="▶ Ejecutar",
                width=100, height=32,
                font=("Segoe UI", 10, "bold"),
                fg_color=accent_color,
                hover_color=VIOLET_DARK if accent_color in (VIOLET, ORANGE, WARNING) else CYAN_DARK,
                text_color=TEXT_MAIN if accent_color != WARNING else "#000000",
                corner_radius=7,
                cursor="hand2",
                command=lambda c=cmd, t=cmd_type: self._execute_command(c, t)
            )
            exec_btn.grid(row=0, column=2, sticky="e")

        # Espaciado inferior de la tarjeta
        ctk.CTkFrame(card, height=10, fg_color="transparent").grid(
            row=len(commands) + 3, column=0
        )

    # ── Ejecuta el comando en la ventana de PowerShell o CMD visible ──
    def _execute_command(self, cmd, cmd_type):
        """
        Abre el comando en una ventana de PowerShell o CMD visible para que el usuario
        vea tanto el comando que se ejecuta como su resultado completo.
        - cmd_type == 'ps'  → PowerShell con -NoExit (la ventana permanece abierta)
        - cmd_type == 'cmd' → CMD con /k (la ventana permanece abierta con el resultado)
        """
        try:
            if cmd_type == "ps":
                # PowerShell visible: escribe el comando y lo ejecuta, luego espera
                # -NoExit mantiene la ventana abierta después de ejecutar
                # Write-Host muestra el comando antes de ejecutarlo para mayor claridad
                ps_script = (
                    f"Write-Host '>> {cmd}' -ForegroundColor Cyan; "
                    f"Write-Host '' ; "
                    f"{cmd}"
                )
                subprocess.Popen(
                    ["powershell", "-NoExit", "-NoProfile", "-Command", ps_script],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # CMD visible: ejecuta el comando y mantiene la ventana abierta (/k)
                # 'echo' muestra el comando antes de ejecutarlo para mayor claridad
                cmd_script = f'echo. & echo ^>^> {cmd} & echo. & {cmd}'
                subprocess.Popen(
                    ["cmd", "/k", cmd_script],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
        except Exception as e:
            messagebox.showerror("Error al ejecutar comando", f"No se pudo abrir la consola:\n{e}")


# =============================================================================
#  PUNTO DE ENTRADA DE LA APLICACIÓN
# =============================================================================

if __name__ == "__main__":
    # Necesario para el correcto funcionamiento de multiprocessing en ejecutables PyInstaller
    multiprocessing.freeze_support()

    # Verificar y solicitar permisos de administrador si es necesario
    run_as_admin()

    # Configurar tema global de customtkinter (modo oscuro)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    # Crear y ejecutar la ventana principal
    app = ProtoDeusBoostApp()
    app.mainloop()
