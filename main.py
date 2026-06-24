import sys
import os
import ctypes
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import multiprocessing

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    if not is_admin():
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)

import info_pc
import optimizer
import tools

def resource_path(relative):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)

VIOLET      = "#7C3AED"
VIOLET_DARK = "#5B21B6"
VIOLET_MED  = "#6D28D9"
CYAN        = "#06B6D4"
CYAN_DARK   = "#0891B2"
BG_MAIN     = "#0A0A0F"
BG_PANEL    = "#111118"
BG_CARD     = "#1A1A26"
BG_CARD2    = "#16161F"
TEXT_MAIN   = "#F8FAFC"
TEXT_MUTED  = "#94A3B8"
TEXT_DIM    = "#64748B"
SUCCESS     = "#10B981"
WARNING     = "#F59E0B"
ERROR       = "#EF4444"
BORDER      = "#2D2D45"
ORANGE      = "#F97316"


class ProtoDeusBoostApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ProtoDeus Boost")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self.configure(fg_color=BG_MAIN)
        ico_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(ico_path):
            self.iconbitmap(ico_path)
        self._current_section = None
        self._build_layout()
        self._show_section("info")

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self, width=240, fg_color=BG_PANEL,
            corner_radius=0, border_width=1, border_color=BORDER
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 8), sticky="ew")
        ctk.CTkLabel(logo_frame, text="⚡", font=("Segoe UI", 32), text_color=VIOLET).pack(side="left", padx=(0, 8))
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="PROTODEUS", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="BOOST", font=("Segoe UI", 11, "bold"), text_color=VIOLET).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="By Prendock", font=("Segoe UI", 9, "italic"), text_color=TEXT_DIM).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 16))
        ctk.CTkLabel(self.sidebar, text="MENÚ PRINCIPAL", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(
            row=2, column=0, padx=20, pady=(0, 8), sticky="w"
        )

        self._nav_buttons = {}
        nav_items = [
            ("info",     "🖥",  "Información PC"),
            ("optimizer","⚡",  "Optimización"),
            ("tools",    "🔧",  "Herramientas"),
            ("winrepair","🪟",  "Reparar Windows"),
            ("nettest",  "🌐",  "Test Internet"),
        ]
        for row_idx, (key, icon, label) in enumerate(nav_items, start=3):
            btn = self._make_nav_button(icon, label, key)
            btn.grid(row=row_idx, column=0, padx=12, pady=3, sticky="ew")
            self._nav_buttons[key] = btn

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=9, column=0, sticky="ew", padx=16, pady=12)
        ver_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ver_frame.grid(row=10, column=0, padx=20, pady=(0, 4), sticky="sw")
        ctk.CTkLabel(ver_frame, text="v1.0.0 | by Prendock", font=("Segoe UI", 9), text_color=TEXT_DIM).pack(anchor="w")
        ctk.CTkLabel(
            ver_frame,
            text="⚡ Software libre y open source\npara la comunidad — úsalo libremente",
            font=("Segoe UI", 8), text_color=VIOLET, justify="left", wraplength=200
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            self.sidebar, text="⏻  Salir", font=("Segoe UI", 13, "bold"),
            fg_color="#2D1B1B", hover_color="#5C1A1A", text_color="#FC8181",
            corner_radius=10, height=40, cursor="hand2", command=self._exit_app
        ).grid(row=11, column=0, padx=12, pady=(0, 20), sticky="ew")

        self.content = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.panels = {
            "info":      InfoPanel(self.content),
            "optimizer": OptimizerPanel(self.content),
            "tools":     ToolsPanel(self.content),
            "winrepair": WindowsRepairPanel(self.content),
            "nettest":   InternetTestPanel(self.content),
        }
        for p in self.panels.values():
            p.grid(row=0, column=0, sticky="nsew")

    def _make_nav_button(self, icon, label, key):
        return ctk.CTkButton(
            self.sidebar, text=f"  {icon}  {label}", font=("Segoe UI", 13),
            anchor="w", fg_color="transparent", hover_color=BG_CARD,
            text_color=TEXT_MUTED, corner_radius=10, height=44, cursor="hand2",
            command=lambda k=key: self._show_section(k),
        )

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

    def _exit_app(self):
        self.quit()
        self.destroy()
        sys.exit(0)


class InfoPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_content()
        self._load_data()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, border_width=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🖥  Información del Sistema", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Hardware detectado en tiempo real", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    def _build_content(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, corner_radius=0,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure((0, 1), weight=1)
        self.loading_label = ctk.CTkLabel(self.scroll, text="⏳ Cargando información del sistema...", font=("Segoe UI", 14), text_color=TEXT_MUTED)
        self.loading_label.grid(row=0, column=0, columnspan=2, pady=60)

    def _load_data(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.loading_label = ctk.CTkLabel(self.scroll, text="⏳ Detectando hardware...", font=("Segoe UI", 14), text_color=TEXT_MUTED)
        self.loading_label.grid(row=0, column=0, columnspan=2, pady=60)
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        data = info_pc.get_all_info()
        self.after(0, lambda: self._render_data(data))

    def _render_data(self, data):
        for w in self.scroll.winfo_children():
            w.destroy()

        NI = "No identificado"

        cpu = data.get("cpu", {})
        cpu_card = self._make_card("🔲  PROCESADOR", row=0, col=0)
        self._fill_card(cpu_card, [
            ("Modelo",          cpu.get("nombre", NI)),
            ("Núcleos físicos", str(cpu.get("nucleos_fisicos", NI))),
            ("Hilos",           str(cpu.get("hilos", NI))),
            ("Frec. máxima",    f"{cpu.get('frecuencia_max_ghz', NI)} GHz"),
            ("Arquitectura",    cpu.get("arquitectura", NI)),
        ])

        gpus = data.get("gpu", [{}])
        gpu = gpus[0] if gpus else {}
        gpu_card = self._make_card("🎮  TARJETA GRÁFICA", row=0, col=1)
        self._fill_card(gpu_card, [
            ("Modelo",     gpu.get("nombre", NI)),
            ("Driver",     gpu.get("driver_version", NI)),
            ("Resolución", gpu.get("resolucion", NI)),
            ("Refresco",   f"{gpu.get('refresh_hz', NI)} Hz"),
            ("Estado",     gpu.get("estado", NI)),
        ])

        ram = data.get("ram", {})
        ram_card = self._make_card("🧠  MEMORIA RAM", row=1, col=0)
        modulos = ram.get("modulos", [])
        mod_str = f"{len(modulos)} módulo(s)" if modulos else NI
        rows_ram = [
            ("Total",         f"{ram.get('total_gb', NI)} GB"),
            ("En uso",        f"{ram.get('usada_gb', NI)} GB ({ram.get('porcentaje_uso','?')}%)"),
            ("Libre",         f"{ram.get('libre_gb', NI)} GB"),
            ("Tipo",          ram.get("tipo", NI)),
            ("Slots totales", str(ram.get("slots_totales", NI))),
            ("Slots en uso",  str(ram.get("slots_en_uso", NI))),
            ("Slots libres",  str(ram.get("slots_libres", NI))),
            ("Módulos",       mod_str),
        ]
        if modulos:
            for m in modulos:
                rows_ram.append((f"  └ {m['slot']}", f"{m['capacidad_gb']} GB {m['tipo']} @ {m['velocidad_mhz']} MHz"))
        self._fill_card(ram_card, rows_ram)

        storage = data.get("storage", {})
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

        os_info = data.get("os", {})
        os_card = self._make_card("🪟  SISTEMA OPERATIVO", row=2, col=0, colspan=2)
        self._fill_card(os_card, [
            ("Sistema",      os_info.get("nombre", NI)),
            ("Edición",      os_info.get("edicion", NI)),
            ("Versión",      os_info.get("version", NI)),
            ("Release",      os_info.get("release", NI)),
            ("Arquitectura", os_info.get("arquitectura", NI)),
        ])

    def _make_card(self, title, row, col, colspan=1):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        card.grid(row=row, column=col, columnspan=colspan, padx=14, pady=10, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(card, fg_color=VIOLET, height=3, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 10))
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN, anchor="w").grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="w")
        return card

    def _fill_card(self, card, rows):
        for i, (key, val) in enumerate(rows, start=2):
            if key == "──────":
                ctk.CTkFrame(card, height=1, fg_color=BORDER).grid(row=i, column=0, columnspan=2, sticky="ew", padx=12, pady=4)
                continue
            ctk.CTkLabel(card, text=key, font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w").grid(row=i, column=0, padx=(16, 8), pady=2, sticky="w")
            ctk.CTkLabel(card, text=str(val), font=("Segoe UI", 11, "bold"), text_color=TEXT_MAIN, anchor="w", wraplength=260).grid(row=i, column=1, padx=(0, 16), pady=2, sticky="w")


class OptimizerPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._running = False
        self._build_header()
        self._build_content()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="⚡  Optimización del Sistema", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Herramientas de limpieza y rendimiento — requiere permisos de administrador", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    def _build_content(self):
        main = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(
            main, fg_color=BG_PANEL, corner_radius=0, width=340,
            border_width=1, border_color=BORDER,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="ACCIONES DISPONIBLES", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(row=0, column=0, padx=20, pady=(20, 8), sticky="w")

        self._opt_buttons = {}
        actions = [
            ("🗑  Limpiar Temporales",         "temp",     optimizer.limpiar_temporales,         VIOLET),
            ("🧹  Limpieza Profunda",           "deep",     optimizer.limpieza_profunda,           VIOLET),
            ("🌐  Limpiar Navegadores",         "browsers", optimizer.limpiar_navegadores,         CYAN),
            ("🗂  Limpiar Registro",            "registry", optimizer.limpiar_registro,            CYAN),
            ("📡  Optimizar Red",               "net",      optimizer.optimizar_red,               CYAN),
            ("🎨  Optimizar Efectos Visuales",  "visuals",  optimizer.optimizar_efectos_visuales,  VIOLET),
            ("💿  Optimizar Disco (SSD)",       "ssd",      optimizer.optimizar_ssd,               VIOLET),
            ("🔧  Desfragmentar HDD",           "hdd",      optimizer.desfragmentar_hdd,           CYAN),
            ("🧠  Liberar RAM",                 "ram",      optimizer.liberar_ram,                 WARNING),
            ("↩  Restaurar SysMain",           "restore",  optimizer.restaurar_sysmain,            TEXT_DIM),
            ("🌐  Limpiar DNS Cache",           "dns",      optimizer.limpiar_dns,                 CYAN),
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

        right = ctk.CTkFrame(main, fg_color=BG_MAIN, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=0)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

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

    def _run_action(self, func, key, color, label=""):
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
        if not messagebox.askyesno(
            f"⚠ {titulo}",
            mensaje,
            icon="warning"
        ):
            return
        self._running = True
        for btn in self._opt_buttons.values():
            btn.configure(state="disabled")
        self.progress_bar.configure(progress_color=color)
        self.progress_bar.set(0)
        self._log(f"\n{'─'*50}\n▶ Iniciando: {key.upper()}\n{'─'*50}")

        def worker():
            try:
                for msg, pct in func():
                    self.after(0, lambda m=msg, p=pct: self._update_progress(m, p))
            except Exception as e:
                self.after(0, lambda: self._log(f"❌ Error: {e}"))
            finally:
                self.after(0, self._finish_action)

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, msg, pct):
        self.status_label.configure(text=msg)
        self.progress_bar.set(pct / 100)
        self.pct_label.configure(text=f"{pct}%")
        self._log(msg)

    def _finish_action(self):
        self._running = False
        for btn in self._opt_buttons.values():
            btn.configure(state="normal")
        self.status_label.configure(text="✅ Operación completada")

    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.status_label.configure(text="Selecciona una acción para comenzar")
        self.progress_bar.set(0)
        self.pct_label.configure(text="0%")


class ToolsPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._running = False
        self._build_header()
        self._build_content()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🔧  Herramientas del Sistema", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Diagnóstico de red y licencias de Windows", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    def _build_content(self):
        main = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN, corner_radius=0, scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        net_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        net_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        net_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(net_card, height=3, fg_color=CYAN, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr_frame = ctk.CTkFrame(net_card, fg_color="transparent")
        hdr_frame.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")
        ctk.CTkLabel(hdr_frame, text="📡  Restablecer Red", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.net_btn = ctk.CTkButton(hdr_frame, text="Ejecutar Restablecimiento", width=200, height=36, fg_color=CYAN_DARK, hover_color=CYAN, font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2", command=self._run_net_reset)
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

        lic_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        lic_card.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew")
        lic_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(lic_card, height=3, fg_color=VIOLET, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr2_frame = ctk.CTkFrame(lic_card, fg_color="transparent")
        hdr2_frame.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")
        ctk.CTkLabel(hdr2_frame, text="🔑  Información de Licencia Windows", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.lic_btn = ctk.CTkButton(hdr2_frame, text="Detectar Licencia", width=180, height=36, fg_color=VIOLET, hover_color=VIOLET_DARK, font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2", command=self._detect_license)
        self.lic_btn.pack(side="right")
        ctk.CTkLabel(lic_card, text="Muestra la clave de Windows instalada, la clave BIOS/UEFI (OEM),\ny detecta el tipo de licencia: OEM, KMS Genérica, COA o Retail.", font=("Segoe UI", 11), text_color=TEXT_MUTED, justify="left", anchor="w", wraplength=700).grid(row=2, column=0, columnspan=2, padx=16, pady=(6, 12), sticky="w")
        self.lic_result = ctk.CTkFrame(lic_card, fg_color=BG_CARD2, corner_radius=10)
        self.lic_result.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="ew")
        self.lic_result.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.lic_result, text="Haz clic en 'Detectar Licencia' para comenzar", font=("Segoe UI", 12), text_color=TEXT_DIM).grid(row=0, column=0, columnspan=2, padx=20, pady=30)

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


class WindowsRepairPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._running = False
        self._build_header()
        self._build_content()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🪟  Reparación de Windows", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Soluciones automáticas para errores comunes del sistema", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    def _build_content(self):
        main = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(
            main, fg_color=BG_PANEL, corner_radius=0, width=360,
            border_width=1, border_color=BORDER,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="REPARACIONES DISPONIBLES", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(row=0, column=0, padx=20, pady=(20, 8), sticky="w")

        self._repair_buttons = {}
        repair_colors = {
            "startup":  VIOLET, "lockscreen": CYAN,    "settings": ORANGE,
            "sfc":      SUCCESS, "store":      CYAN,    "updates":  WARNING,
            "taskbar":  VIOLET,  "audio":      CYAN,    "drivers":  VIOLET,
            "defender": SUCCESS,
        }
        for i, (key, repair) in enumerate(tools.REPARACIONES_WINDOWS.items()):
            color = repair_colors.get(key, VIOLET)
            btn_frame = ctk.CTkFrame(left, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER)
            btn_frame.grid(row=i + 1, column=0, padx=12, pady=4, sticky="ew")
            btn_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(btn_frame, text=repair["nombre"], font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN, anchor="w").grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
            ctk.CTkLabel(btn_frame, text=repair["descripcion"], font=("Segoe UI", 10), text_color=TEXT_MUTED, anchor="w", wraplength=300, justify="left").grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")

            btn = ctk.CTkButton(
                btn_frame, text="Ejecutar", width=90, height=30,
                fg_color=color, hover_color=VIOLET_DARK if color == VIOLET else CYAN_DARK,
                font=("Segoe UI", 11, "bold"), corner_radius=8, cursor="hand2",
                command=lambda k=key: self._run_repair(k)
            )
            btn.grid(row=0, column=1, rowspan=2, padx=12, pady=8)
            self._repair_buttons[key] = btn

        right = ctk.CTkFrame(main, fg_color=BG_MAIN, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

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

        log_card = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        log_card.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)
        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        ctk.CTkLabel(log_hdr, text="📋  Registro de Reparación", font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkButton(log_hdr, text="Limpiar", width=70, height=26, fg_color=BG_CARD2, hover_color=BORDER, font=("Segoe UI", 10), corner_radius=6, cursor="hand2", command=self._clear_log).pack(side="right")
        self.repair_log = ctk.CTkTextbox(log_card, fg_color=BG_CARD2, corner_radius=10, text_color=TEXT_MUTED, font=("Cascadia Code", 11), wrap="word", border_width=0)
        self.repair_log.grid(row=1, column=0, padx=10, pady=(8, 10), sticky="nsew")
        self.repair_log.configure(state="disabled")

        warning_card = ctk.CTkFrame(right, fg_color="#1A1208", corner_radius=10, border_width=1, border_color=WARNING)
        warning_card.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(warning_card, text="⚠  Algunas reparaciones pueden tardar varios minutos y requieren reinicio posterior.", font=("Segoe UI", 11), text_color=WARNING, wraplength=600, justify="left", anchor="w").grid(padx=16, pady=10, sticky="w")

    def _run_repair(self, key):
        if self._running:
            return
        self._running = True
        for btn in self._repair_buttons.values():
            btn.configure(state="disabled")
        repair = tools.REPARACIONES_WINDOWS.get(key, {})
        nombre = repair.get("nombre", key)
        self.repair_progress.set(0)
        self._log(f"\n{'─'*50}\n▶ {nombre}\n{'─'*50}")

        def worker():
            try:
                for msg, pct in tools.reparar_windows(key):
                    self.after(0, lambda m=msg, p=pct: self._update(m, p))
            except Exception as e:
                self.after(0, lambda: self._log(f"❌ Error: {e}"))
            finally:
                self.after(0, self._finish)

        threading.Thread(target=worker, daemon=True).start()

    def _update(self, msg, pct):
        self.repair_status.configure(text=msg)
        self.repair_progress.set(pct / 100)
        self.repair_pct.configure(text=f"{pct}%")
        self._log(msg)

    def _finish(self):
        self._running = False
        for btn in self._repair_buttons.values():
            btn.configure(state="normal")
        self.repair_status.configure(text="✅ Reparación completada")

    def _log(self, msg):
        self.repair_log.configure(state="normal")
        self.repair_log.insert("end", msg + "\n")
        self.repair_log.see("end")
        self.repair_log.configure(state="disabled")

    def _clear_log(self):
        self.repair_log.configure(state="normal")
        self.repair_log.delete("1.0", "end")
        self.repair_log.configure(state="disabled")
        self.repair_status.configure(text="Selecciona una reparación para comenzar")
        self.repair_progress.set(0)
        self.repair_pct.configure(text="0%")


class InternetTestPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._running = False
        self._result_widgets = {}
        self._build_header()
        self._build_content()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🌐  Test de Internet", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w").place(x=30, y=14)
        ctk.CTkLabel(hdr, text="Análisis completo de velocidad, latencia, estabilidad y calidad de red", font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w").place(x=32, y=48)

    def _build_content(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN, corner_radius=0, scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET)
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure((0, 1), weight=1)

        ctrl_card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        ctrl_card.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        ctrl_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(ctrl_card, height=3, fg_color=CYAN, corner_radius=2).grid(row=0, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(ctrl_card, text="🔍  Análisis de Conexión", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN, anchor="w").grid(row=1, column=0, padx=16, pady=(14, 4), sticky="w")
        ctk.CTkLabel(ctrl_card, text="Mide descarga, subida, latencia, jitter, paquetes perdidos y calidad general de tu red.", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w").grid(row=2, column=0, padx=16, pady=(0, 10), sticky="w")

        self.test_btn = ctk.CTkButton(
            ctrl_card, text="▶  Iniciar Test", width=180, height=42,
            fg_color=CYAN_DARK, hover_color=CYAN,
            font=("Segoe UI", 13, "bold"), corner_radius=10, cursor="hand2",
            command=self._start_test
        )
        self.test_btn.grid(row=1, column=2, rowspan=2, padx=16, pady=10)

        self.test_progress = ctk.CTkProgressBar(ctrl_card, progress_color=CYAN, fg_color=BG_CARD2, height=6)
        self.test_progress.grid(row=3, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="ew")
        self.test_progress.set(0)
        self.test_status = ctk.CTkLabel(ctrl_card, text="Listo para comenzar el análisis", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w")
        self.test_status.grid(row=4, column=0, columnspan=3, padx=16, pady=(0, 14), sticky="w")

        self.quality_card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        self.quality_card.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        self.quality_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(self.quality_card, height=3, fg_color=VIOLET, corner_radius=2).grid(row=0, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(self.quality_card, text="📊  Calidad de Red", font=("Segoe UI", 15, "bold"), text_color=TEXT_MAIN, anchor="w").grid(row=1, column=0, padx=16, pady=(14, 8), sticky="w")

        self.quality_score_label = ctk.CTkLabel(self.quality_card, text="—", font=("Segoe UI", 48, "bold"), text_color=TEXT_DIM)
        self.quality_score_label.grid(row=2, column=0, padx=20, pady=(0, 4))
        self.quality_label = ctk.CTkLabel(self.quality_card, text="Sin datos", font=("Segoe UI", 16, "bold"), text_color=TEXT_DIM)
        self.quality_label.grid(row=3, column=0, padx=20, pady=(0, 6))
        self.quality_bar = ctk.CTkProgressBar(self.quality_card, progress_color=TEXT_DIM, fg_color=BG_CARD2, height=12, corner_radius=6)
        self.quality_bar.grid(row=4, column=0, padx=20, pady=(0, 16), sticky="ew")
        self.quality_bar.set(0)

        legend_frame = ctk.CTkFrame(self.quality_card, fg_color="transparent")
        legend_frame.grid(row=2, column=1, rowspan=3, padx=20, pady=10, sticky="nsew")
        for color, label in [("#EF4444", "1-3 Mala"), ("#F97316", "4-5 Regular"), ("#F59E0B", "6-7 Buena"), ("#10B981", "8-10 Excelente")]:
            f = ctk.CTkFrame(legend_frame, fg_color="transparent")
            f.pack(anchor="w", pady=2)
            ctk.CTkFrame(f, width=14, height=14, fg_color=color, corner_radius=3).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(f, text=label, font=("Segoe UI", 11), text_color=TEXT_MUTED).pack(side="left")

        metrics_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        metrics_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        metrics_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self._metric_cards = {}
        metrics = [
            ("down",    "⬇",  "Descarga",          "— Mbps",   CYAN),
            ("up",      "⬆",  "Subida",             "— Mbps",   VIOLET),
            ("latency", "📶", "Latencia",           "— ms",     SUCCESS),
            ("jitter",  "〜", "Jitter",             "— ms",     WARNING),
            ("loss",    "📦", "Paquetes Perdidos",  "—%",       ERROR),
            ("isp",     "🏢", "Proveedor",          "—",        CYAN),
        ]
        for i, (key, icon, name, default, color) in enumerate(metrics):
            col = i % 3
            row = i // 3 + 1
            mc = ctk.CTkFrame(metrics_frame, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
            mc.grid(row=row, column=col, padx=6, pady=6, sticky="ew")
            mc.grid_columnconfigure(0, weight=1)
            ctk.CTkFrame(mc, height=3, fg_color=color, corner_radius=2).grid(row=0, column=0, columnspan=2, sticky="ew")
            ctk.CTkLabel(mc, text=f"{icon}  {name}", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w").grid(row=1, column=0, padx=12, pady=(10, 2), sticky="w")
            val_label = ctk.CTkLabel(mc, text=default, font=("Segoe UI", 20, "bold"), text_color=color, anchor="w")
            val_label.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="w")
            self._metric_cards[key] = val_label

        info_card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER)
        info_card.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        info_card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(info_card, height=3, fg_color=VIOLET, corner_radius=2).grid(row=0, column=0, columnspan=4, sticky="ew")
        ctk.CTkLabel(info_card, text="🌍  Información de Conexión", font=("Segoe UI", 14, "bold"), text_color=TEXT_MAIN, anchor="w").grid(row=1, column=0, columnspan=4, padx=16, pady=(12, 8), sticky="w")

        self._info_labels = {}
        info_fields = [
            ("ip",      "IP Pública"),
            ("ciudad",  "Ciudad"),
            ("pais",    "País"),
            ("latmin",  "Latencia Mín."),
            ("latmax",  "Latencia Máx."),
        ]
        for col, (key, label) in enumerate(info_fields):
            ctk.CTkLabel(info_card, text=label, font=("Segoe UI", 10), text_color=TEXT_DIM, anchor="w").grid(row=2, column=col, padx=12, pady=(0, 2), sticky="w")
            lbl = ctk.CTkLabel(info_card, text="—", font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN, anchor="w")
            lbl.grid(row=3, column=col, padx=12, pady=(0, 14), sticky="w")
            self._info_labels[key] = lbl

    def _start_test(self):
        if self._running:
            return
        self._running = True
        self.test_btn.configure(state="disabled", text="⏳ Analizando...")
        self.test_progress.set(0)
        self._reset_results()

        def worker():
            result_data = None
            try:
                for msg, pct in tools.test_internet():
                    if msg == "__RESULT__":
                        result_data = pct
                    else:
                        self.after(0, lambda m=msg, p=pct: self._update_test(m, p))
            except Exception as e:
                self.after(0, lambda: self.test_status.configure(text=f"❌ Error: {e}"))
            finally:
                if result_data:
                    self.after(0, lambda d=result_data: self._render_results(d))
                self.after(0, self._finish_test)

        threading.Thread(target=worker, daemon=True).start()

    def _reset_results(self):
        for key, lbl in self._metric_cards.items():
            defaults = {"down": "— Mbps", "up": "— Mbps", "latency": "— ms", "jitter": "— ms", "loss": "—%", "isp": "—"}
            lbl.configure(text=defaults.get(key, "—"))
        for lbl in self._info_labels.values():
            lbl.configure(text="—")
        self.quality_score_label.configure(text="—", text_color=TEXT_DIM)
        self.quality_label.configure(text="Analizando...", text_color=TEXT_DIM)
        self.quality_bar.configure(progress_color=TEXT_DIM)
        self.quality_bar.set(0)

    def _update_test(self, msg, pct):
        self.test_status.configure(text=msg)
        self.test_progress.set(pct / 100)

    def _render_results(self, data):
        down = data.get("descarga_mbps")
        up = data.get("subida_mbps")
        lat = data.get("latencia_ms")
        jitter = data.get("jitter_ms")
        loss = data.get("paquetes_perdidos_pct")
        calidad = data.get("calidad", {})

        self._metric_cards["down"].configure(text=f"{down} Mbps" if down else "Sin datos")
        self._metric_cards["up"].configure(text=f"{up} Mbps" if up else "Sin datos")
        self._metric_cards["latency"].configure(text=f"{lat} ms" if lat is not None else "Sin datos")
        self._metric_cards["jitter"].configure(text=f"{jitter} ms" if jitter is not None else "Sin datos")
        self._metric_cards["loss"].configure(text=f"{loss}%" if loss is not None else "Sin datos")
        self._metric_cards["isp"].configure(text=data.get("proveedor", "No identificado"))

        self._info_labels["ip"].configure(text=data.get("ip_publica", "—"))
        self._info_labels["ciudad"].configure(text=data.get("ciudad", "—"))
        self._info_labels["pais"].configure(text=data.get("pais", "—"))
        self._info_labels["latmin"].configure(text=f"{data.get('latencia_min_ms', '—')} ms")
        self._info_labels["latmax"].configure(text=f"{data.get('latencia_max_ms', '—')} ms")

        if calidad:
            score = calidad.get("puntuacion", 0)
            color = calidad.get("color", TEXT_DIM)
            etiqueta = calidad.get("etiqueta", "")
            self.quality_score_label.configure(text=str(score), text_color=color)
            self.quality_label.configure(text=etiqueta, text_color=color)
            self.quality_bar.configure(progress_color=color)
            self.quality_bar.set(score / 10)

    def _finish_test(self):
        self._running = False
        self.test_btn.configure(state="normal", text="▶  Iniciar Test")
        self.test_status.configure(text="✅ Análisis completado")
        self.test_progress.set(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_as_admin()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = ProtoDeusBoostApp()
    app.mainloop()
