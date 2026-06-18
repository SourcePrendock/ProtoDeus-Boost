"""
main.py — ProtoDeus Boost | Aplicación principal
GUI premium con CustomTkinter, tema oscuro violeta/cyan
"""

import sys
import os
import ctypes
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# ── Verificar y solicitar privilegios de administrador ──────────────────────
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    if not is_admin():
        # En PyInstaller o scripts de Python, sys.argv[1:] contiene los parámetros reales
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        sys.exit(0)

# ── Importar módulos del proyecto ───────────────────────────────────────────
import info_pc
import optimizer
import tools

# ── Tema visual ─────────────────────────────────────────────────────────────
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


# ════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════
class ProtoDeusBoostApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ProtoDeus Boost")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self.configure(fg_color=BG_MAIN)

        # Intentar poner icono
        ico_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(ico_path):
            self.iconbitmap(ico_path)

        self._current_section = None
        self._build_layout()
        self._show_section("info")

    # ── Layout principal ────────────────────────────────────────────────────
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(
            self, width=240, fg_color=BG_PANEL,
            corner_radius=0, border_width=1, border_color=BORDER
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 8), sticky="ew")

        ctk.CTkLabel(
            logo_frame, text="⚡", font=("Segoe UI", 32),
            text_color=VIOLET
        ).pack(side="left", padx=(0, 8))

        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(
            title_frame, text="PROTODEUS", font=("Segoe UI", 16, "bold"),
            text_color=TEXT_MAIN
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="BOOST", font=("Segoe UI", 11, "bold"),
            text_color=VIOLET
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="By Prendock", font=("Segoe UI", 9, "italic"),
            text_color=TEXT_DIM
        ).pack(anchor="w", pady=(0, 0))

        # Separador
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(4, 16)
        )

        # Etiqueta de sección
        ctk.CTkLabel(
            self.sidebar, text="MENÚ PRINCIPAL",
            font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM
        ).grid(row=2, column=0, padx=20, pady=(0, 8), sticky="w")

        # Botones de navegación
        self._nav_buttons = {}
        nav_items = [
            ("info",       "🖥",  "Información PC"),
            ("optimizer",  "⚡",  "Optimización"),
            ("tools",      "🔧",  "Herramientas"),
        ]
        for row_idx, (key, icon, label) in enumerate(nav_items, start=3):
            btn = self._make_nav_button(icon, label, key)
            btn.grid(row=row_idx, column=0, padx=12, pady=3, sticky="ew")
            self._nav_buttons[key] = btn

        # Separador inferior
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(
            row=9, column=0, sticky="ew", padx=16, pady=12
        )

        # Versión
        ctk.CTkLabel(
            self.sidebar, text="v1.0.0 | by Prendock",
            font=("Segoe UI", 9), text_color=TEXT_DIM
        ).grid(row=10, column=0, padx=20, pady=(0, 6), sticky="sw")

        # Botón Salir
        exit_btn = ctk.CTkButton(
            self.sidebar, text="⏻  Salir",
            font=("Segoe UI", 13, "bold"),
            fg_color="#2D1B1B", hover_color="#5C1A1A",
            text_color="#FC8181", corner_radius=10,
            height=40, cursor="hand2",
            command=self._exit_app
        )
        exit_btn.grid(row=11, column=0, padx=12, pady=(0, 20), sticky="ew")

        # ── Panel de contenido ────────────────────────────────────────────
        self.content = ctk.CTkFrame(
            self, fg_color=BG_MAIN, corner_radius=0
        )
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Instanciar todos los paneles una sola vez para mantener su estado
        self.panels = {
            "info": InfoPanel(self.content),
            "optimizer": OptimizerPanel(self.content),
            "tools": ToolsPanel(self.content)
        }
        for p in self.panels.values():
            p.grid(row=0, column=0, sticky="nsew")

    def _make_nav_button(self, icon, label, key):
        btn = ctk.CTkButton(
            self.sidebar,
            text=f"  {icon}  {label}",
            font=("Segoe UI", 13),
            anchor="w",
            fg_color="transparent",
            hover_color=BG_CARD,
            text_color=TEXT_MUTED,
            corner_radius=10,
            height=44,
            cursor="hand2",
            command=lambda k=key: self._show_section(k),
        )
        return btn

    def _show_section(self, key):
        if self._current_section == key:
            return
        self._current_section = key

        # Actualizar estado visual de botones
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(
                    fg_color=BG_CARD, text_color=TEXT_MAIN,
                    border_width=1, border_color=VIOLET
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color=TEXT_MUTED,
                    border_width=0
                )

        # Traer al frente el panel seleccionado sin destruir los demás para mantener los datos fijos
        if hasattr(self, 'panels') and key in self.panels:
            self.panels[key].tkraise()

    def _exit_app(self):
        self.quit()
        self.destroy()
        sys.exit(0)


# ════════════════════════════════════════════════════════════════════════════
#  SECCIÓN: INFORMACIÓN DEL PC
# ════════════════════════════════════════════════════════════════════════════
class InfoPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_content()
        self._load_data()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0,
                           border_width=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)

        ctk.CTkLabel(
            hdr, text="🖥  Información del Sistema",
            font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN,
            anchor="w"
        ).place(x=30, y=14)
        ctk.CTkLabel(
            hdr, text="Hardware detectado en tiempo real",
            font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w"
        ).place(x=32, y=48)

    def _build_content(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, corner_radius=0,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure((0, 1), weight=1)

        # Placeholder de carga
        self.loading_label = ctk.CTkLabel(
            self.scroll, text="⏳ Cargando información del sistema...",
            font=("Segoe UI", 14), text_color=TEXT_MUTED
        )
        self.loading_label.grid(row=0, column=0, columnspan=2, pady=60)

    def _load_data(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.loading_label = ctk.CTkLabel(
            self.scroll, text="⏳ Detectando hardware...",
            font=("Segoe UI", 14), text_color=TEXT_MUTED
        )
        self.loading_label.grid(row=0, column=0, columnspan=2, pady=60)

        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        data = info_pc.get_all_info()
        self.after(0, lambda: self._render_data(data))

    def _render_data(self, data):
        for w in self.scroll.winfo_children():
            w.destroy()

        pad = {"padx": 16, "pady": 8}

        # ── CPU ──────────────────────────────────────────────────────────
        cpu = data.get("cpu", {})
        cpu_card = self._make_card("🔲  PROCESADOR", row=0, col=0)
        rows_cpu = [
            ("Modelo",           cpu.get("nombre", "N/A")),
            ("Núcleos físicos",  str(cpu.get("nucleos_fisicos", "N/A"))),
            ("Hilos",            str(cpu.get("hilos", "N/A"))),
            ("Frec. base",       f"{cpu.get('frecuencia_base_ghz', 'N/A')} GHz"),
            ("Frec. máxima",     f"{cpu.get('frecuencia_max_ghz', 'N/A')} GHz"),
            ("Arquitectura",     cpu.get("arquitectura", "N/A")),
        ]
        self._fill_card(cpu_card, rows_cpu)

        # ── GPU ──────────────────────────────────────────────────────────
        gpus = data.get("gpu", [{}])
        gpu = gpus[0] if gpus else {}
        gpu_card = self._make_card("🎮  TARJETA GRÁFICA", row=0, col=1)
        rows_gpu = [
            ("Modelo",      gpu.get("nombre", "N/A")),
            ("VRAM",        f"{gpu.get('vram_gb', 'N/A')} GB"),
            ("Driver",      gpu.get("driver_version", "N/A")),
            ("Resolución",  gpu.get("resolucion", "N/A")),
            ("Refresco",    f"{gpu.get('refresh_hz', 'N/A')} Hz"),
            ("Estado",      gpu.get("estado", "N/A")),
        ]
        self._fill_card(gpu_card, rows_gpu)

        # ── RAM ──────────────────────────────────────────────────────────
        ram = data.get("ram", {})
        ram_card = self._make_card("🧠  MEMORIA RAM", row=1, col=0)
        modulos = ram.get("modulos", [])
        mod_str = f"{len(modulos)} módulo(s)" if modulos else "N/A"
        rows_ram = [
            ("Total",           f"{ram.get('total_gb', 'N/A')} GB"),
            ("En uso",          f"{ram.get('usada_gb', 'N/A')} GB ({ram.get('porcentaje_uso','?')}%)"),
            ("Libre",           f"{ram.get('libre_gb', 'N/A')} GB"),
            ("Tipo",            ram.get("tipo", "N/A")),
            ("Slots totales",   str(ram.get("slots_totales", "N/A"))),
            ("Slots en uso",    str(ram.get("slots_en_uso", "N/A"))),
            ("Slots libres",    str(ram.get("slots_libres", "N/A"))),
            ("Módulos",         mod_str),
        ]
        if modulos:
            for m in modulos:
                rows_ram.append((f"  └ {m['slot']}", f"{m['capacidad_gb']} GB {m['tipo']} @ {m['velocidad_mhz']} MHz"))
        self._fill_card(ram_card, rows_ram)

        # ── Storage ──────────────────────────────────────────────────────
        storage = data.get("storage", {})
        storage_card = self._make_card("💾  ALMACENAMIENTO", row=1, col=1)
        rows_storage = []
        for disco in storage.get("discos_fisicos", []):
            rows_storage.append(("Modelo", disco.get("modelo", "N/A")))
            rows_storage.append(("Tipo", disco.get("tipo", "N/A")))
            rows_storage.append(("Capacidad", f"{disco.get('capacidad_gb', 'N/A')} GB"))
            rows_storage.append(("Interfaz", disco.get("interfaz", "N/A")))
            rows_storage.append(("──────", "──────"))
        for part in storage.get("particiones", []):
            rows_storage.append((f"Unidad {part['unidad']}", f"{part['total_gb']} GB total"))
            rows_storage.append(("  Usado / Libre", f"{part['usado_gb']} / {part['libre_gb']} GB ({part['porcentaje']}%)"))
        if not rows_storage:
            rows_storage = [("", "No se detectaron unidades")]
        self._fill_card(storage_card, rows_storage)

        # ── OS ────────────────────────────────────────────────────────────
        os_info = data.get("os", {})
        os_card = self._make_card("🪟  SISTEMA OPERATIVO", row=2, col=0, colspan=2)
        rows_os = [
            ("Sistema",        os_info.get("nombre", "N/A")),
            ("Versión",        os_info.get("version", "N/A")),
            ("Release",        os_info.get("release", "N/A")),
            ("Arquitectura",   os_info.get("arquitectura", "N/A")),
        ]
        self._fill_card(os_card, rows_os)

    def _make_card(self, title, row, col, colspan=1):
        card = ctk.CTkFrame(
            self.scroll, fg_color=BG_CARD, corner_radius=14,
            border_width=1, border_color=BORDER
        )
        card.grid(row=row, column=col, columnspan=colspan,
                  padx=14, pady=10, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)

        # Header con barra de color
        hdr = ctk.CTkFrame(card, fg_color=VIOLET, height=3, corner_radius=2)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 10))

        ctk.CTkLabel(
            card, text=title, font=("Segoe UI", 13, "bold"),
            text_color=TEXT_MAIN, anchor="w"
        ).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="w")

        return card

    def _fill_card(self, card, rows):
        start = 2
        for i, (key, val) in enumerate(rows):
            if key == "──────":
                ctk.CTkFrame(card, height=1, fg_color=BORDER).grid(
                    row=start + i, column=0, columnspan=2,
                    sticky="ew", padx=12, pady=4
                )
                continue
            ctk.CTkLabel(
                card, text=key, font=("Segoe UI", 11),
                text_color=TEXT_MUTED, anchor="w"
            ).grid(row=start + i, column=0, padx=(16, 8), pady=2, sticky="w")
            ctk.CTkLabel(
                card, text=str(val), font=("Segoe UI", 11, "bold"),
                text_color=TEXT_MAIN, anchor="w", wraplength=260
            ).grid(row=start + i, column=1, padx=(0, 16), pady=2, sticky="w")


# ════════════════════════════════════════════════════════════════════════════
#  SECCIÓN: OPTIMIZACIÓN
# ════════════════════════════════════════════════════════════════════════════
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
        ctk.CTkLabel(
            hdr, text="⚡  Optimización del Sistema",
            font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w"
        ).place(x=30, y=14)
        ctk.CTkLabel(
            hdr, text="Herramientas de limpieza y rendimiento — requiere permisos de administrador",
            font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w"
        ).place(x=32, y=48)

    def _build_content(self):
        main = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        # ── Panel izquierdo: botones ──────────────────────────────────────
        left = ctk.CTkScrollableFrame(
            main, fg_color=BG_PANEL, corner_radius=0, width=340,
            border_width=1, border_color=BORDER,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left, text="ACCIONES DISPONIBLES",
            font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM
        ).grid(row=0, column=0, padx=20, pady=(20, 8), sticky="w")

        self._opt_buttons = {}
        actions = [
            ("🗑  Limpiar Temporales",          "temp",       optimizer.limpiar_temporales,      VIOLET),
            ("🧹  Limpieza Profunda",            "deep",       optimizer.limpieza_profunda,        VIOLET),
            ("🌐  Limpiar Navegadores",          "browsers",   optimizer.limpiar_navegadores,      CYAN),
            ("🗂  Limpiar Registro",             "registry",   optimizer.limpiar_registro,         CYAN),
            ("📡  Optimizar Red",                "net",        optimizer.optimizar_red,            CYAN),
            ("🎨  Optimizar Efectos Visuales",   "visuals",    optimizer.optimizar_efectos_visuales, VIOLET),
            ("💿  Optimizar Disco (SSD)",        "ssd",        optimizer.optimizar_ssd,            VIOLET),
            ("🔧  Desfragmentar HDD",            "hdd",        optimizer.desfragmentar_hdd,        CYAN),
            ("🧠  Liberar RAM",                  "ram",        optimizer.liberar_ram,              WARNING),
            ("↩  Restaurar SysMain",            "restore",    optimizer.restaurar_sysmain,         TEXT_DIM),
            ("🌐  Limpiar DNS Cache",            "dns",        optimizer.limpiar_dns,              CYAN),
        ]

        for i, (label, key, func, color) in enumerate(actions):
            btn = ctk.CTkButton(
                left, text=label, font=("Segoe UI", 12), anchor="w",
                fg_color=BG_CARD, hover_color=BG_CARD2,
                text_color=TEXT_MAIN, corner_radius=10, height=46,
                border_width=1, border_color=BORDER, cursor="hand2",
                command=lambda f=func, k=key, c=color: self._run_action(f, k, c)
            )
            btn.grid(row=i + 1, column=0, padx=12, pady=4, sticky="ew")
            self._opt_buttons[key] = btn

        # ── Panel derecho: log + progreso ─────────────────────────────────
        right = ctk.CTkFrame(main, fg_color=BG_MAIN, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=0)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Barra de progreso
        prog_card = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=14,
                                 border_width=1, border_color=BORDER)
        prog_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        prog_card.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            prog_card, text="Selecciona una acción para comenzar",
            font=("Segoe UI", 13), text_color=TEXT_MUTED, anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(
            prog_card, progress_color=VIOLET, fg_color=BG_CARD2,
            height=8, corner_radius=4
        )
        self.progress_bar.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")
        self.progress_bar.set(0)

        self.pct_label = ctk.CTkLabel(
            prog_card, text="0%", font=("Segoe UI", 11, "bold"),
            text_color=VIOLET
        )
        self.pct_label.grid(row=1, column=1, padx=(0, 16), pady=(0, 14))

        # Log
        log_card = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=14,
                                border_width=1, border_color=BORDER)
        log_card.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))

        ctk.CTkLabel(
            log_hdr, text="📋  Registro de Actividad",
            font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            log_hdr, text="Limpiar", width=70, height=26,
            fg_color=BG_CARD2, hover_color=BORDER,
            font=("Segoe UI", 10), corner_radius=6, cursor="hand2",
            command=self._clear_log
        )
        clear_btn.pack(side="right")

        self.log_box = ctk.CTkTextbox(
            log_card, fg_color=BG_CARD2, corner_radius=10,
            text_color=TEXT_MUTED, font=("Cascadia Code", 11),
            wrap="word", border_width=0
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=(8, 10), sticky="nsew")
        self.log_box.configure(state="disabled")

    def _run_action(self, func, key, color):
        if self._running:
            return
        self._running = True

        for btn in self._opt_buttons.values():
            btn.configure(state="disabled")

        self.progress_bar.configure(progress_color=color)
        self.progress_bar.set(0)
        self._log(f"\n{'─'*50}")
        self._log(f"▶ Iniciando: {key.upper()}")
        self._log(f"{'─'*50}")

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


# ════════════════════════════════════════════════════════════════════════════
#  SECCIÓN: HERRAMIENTAS
# ════════════════════════════════════════════════════════════════════════════
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
        ctk.CTkLabel(
            hdr, text="🔧  Herramientas del Sistema",
            font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN, anchor="w"
        ).place(x=30, y=14)
        ctk.CTkLabel(
            hdr, text="Diagnóstico de red y licencias de Windows",
            font=("Segoe UI", 12), text_color=TEXT_MUTED, anchor="w"
        ).place(x=32, y=48)

    def _build_content(self):
        main = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, corner_radius=0,
            scrollbar_button_color=BG_CARD, scrollbar_button_hover_color=VIOLET
        )
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        # ── Tarjeta: Restablecer Red ───────────────────────────────────────
        net_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14,
                                border_width=1, border_color=BORDER)
        net_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        net_card.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(net_card, height=3, fg_color=CYAN, corner_radius=2).grid(
            row=0, column=0, columnspan=2, sticky="ew"
        )

        hdr_frame = ctk.CTkFrame(net_card, fg_color="transparent")
        hdr_frame.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")

        ctk.CTkLabel(
            hdr_frame, text="📡  Restablecer Red",
            font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN
        ).pack(side="left")

        self.net_btn = ctk.CTkButton(
            hdr_frame, text="Ejecutar Restablecimiento", width=200, height=36,
            fg_color=CYAN_DARK, hover_color=CYAN,
            font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2",
            command=self._run_net_reset
        )
        self.net_btn.pack(side="right")

        ctk.CTkLabel(
            net_card,
            text="Equivalente al restablecimiento de red de Windows 10/11.\n"
                 "Resetea Winsock, pila TCP/IP, DNS, firewall y renueva la IP.\n"
                 "⚠ Se recomienda reiniciar el PC al finalizar.",
            font=("Segoe UI", 11), text_color=TEXT_MUTED,
            justify="left", anchor="w", wraplength=700
        ).grid(row=2, column=0, columnspan=2, padx=16, pady=(6, 8), sticky="w")

        # Barra de progreso de red
        self.net_progress = ctk.CTkProgressBar(
            net_card, progress_color=CYAN, fg_color=BG_CARD2, height=6
        )
        self.net_progress.grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")
        self.net_progress.set(0)

        self.net_status = ctk.CTkLabel(
            net_card, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w"
        )
        self.net_status.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")

        self.net_log = ctk.CTkTextbox(
            net_card, fg_color=BG_CARD2, corner_radius=8,
            text_color=TEXT_MUTED, font=("Cascadia Code", 10),
            height=120, wrap="word", border_width=0
        )
        self.net_log.grid(row=5, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="ew")
        self.net_log.configure(state="disabled")

        # ── Tarjeta: Información de Licencia ──────────────────────────────
        lic_card = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=14,
                                border_width=1, border_color=BORDER)
        lic_card.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew")
        lic_card.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(lic_card, height=3, fg_color=VIOLET, corner_radius=2).grid(
            row=0, column=0, columnspan=2, sticky="ew"
        )

        hdr2_frame = ctk.CTkFrame(lic_card, fg_color="transparent")
        hdr2_frame.grid(row=1, column=0, columnspan=2, padx=16, pady=(14, 0), sticky="ew")

        ctk.CTkLabel(
            hdr2_frame, text="🔑  Información de Licencia Windows",
            font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN
        ).pack(side="left")

        self.lic_btn = ctk.CTkButton(
            hdr2_frame, text="Detectar Licencia", width=180, height=36,
            fg_color=VIOLET, hover_color=VIOLET_DARK,
            font=("Segoe UI", 12, "bold"), corner_radius=8, cursor="hand2",
            command=self._detect_license
        )
        self.lic_btn.pack(side="right")

        ctk.CTkLabel(
            lic_card,
            text="Muestra la clave de Windows instalada, la clave BIOS/UEFI (OEM),\n"
                 "y detecta el tipo de licencia: OEM, KMS Genérica, COA o Retail.",
            font=("Segoe UI", 11), text_color=TEXT_MUTED,
            justify="left", anchor="w", wraplength=700
        ).grid(row=2, column=0, columnspan=2, padx=16, pady=(6, 12), sticky="w")

        # Frame de resultado de licencia
        self.lic_result = ctk.CTkFrame(lic_card, fg_color=BG_CARD2, corner_radius=10)
        self.lic_result.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="ew")
        self.lic_result.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.lic_result, text="Haz clic en 'Detectar Licencia' para comenzar",
            font=("Segoe UI", 12), text_color=TEXT_DIM
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=30)

    # ── Acciones ─────────────────────────────────────────────────────────

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
        ctk.CTkLabel(
            self.lic_result, text="⏳ Analizando licencia de Windows...",
            font=("Segoe UI", 12), text_color=TEXT_MUTED
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=30)

        def worker():
            data = tools.get_license_info()
            self.after(0, lambda: self._render_license(data))

        threading.Thread(target=worker, daemon=True).start()

    def _render_license(self, data):
        self._running = False
        self.lic_btn.configure(state="normal", text="Detectar Licencia")

        for w in self.lic_result.winfo_children():
            w.destroy()

        # Tipo de licencia con badge de color
        tipo = data.get("tipo", "Desconocido")
        tipo_lower = tipo.lower()
        if "kms" in tipo_lower:
            badge_color = WARNING
        elif "oem" in tipo_lower:
            badge_color = CYAN
        elif "retail" in tipo_lower:
            badge_color = SUCCESS
        elif "coa" in tipo_lower:
            badge_color = VIOLET
        else:
            badge_color = TEXT_DIM

        # Badge de tipo
        badge_frame = ctk.CTkFrame(self.lic_result, fg_color=badge_color, corner_radius=8)
        badge_frame.grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 12), sticky="w")
        ctk.CTkLabel(
            badge_frame, text=f"  {tipo}  ",
            font=("Segoe UI", 13, "bold"), text_color="#000000"
        ).pack(padx=4, pady=4)

        # Descripción del tipo
        desc = data.get("descripcion_tipo", "")
        if desc:
            ctk.CTkLabel(
                self.lic_result, text=desc,
                font=("Segoe UI", 11), text_color=TEXT_MUTED,
                wraplength=650, anchor="w", justify="left"
            ).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")

        # Campos de información
        fields = [
            ("Licencia instalada",       data.get("clave_instalada", "No disponible")),
            ("Licencia BIOS/UEFI",       data.get("clave_bios", "No disponible")),
            ("Edición de Windows",       data.get("edicion", "Desconocida")),
            ("Estado de activación",     data.get("estado_activacion", "Desconocido")),
            ("Nombre de licencia",       data.get("nombre_licencia", "N/A")),
            ("Descripción",              data.get("descripcion", "N/A")),
            ("Expiración",               data.get("expiracion", "N/A")),
        ]

        for i, (key, val) in enumerate(fields):
            ctk.CTkLabel(
                self.lic_result, text=key + ":",
                font=("Segoe UI", 11), text_color=TEXT_DIM, anchor="w"
            ).grid(row=i + 2, column=0, padx=(16, 8), pady=3, sticky="w")

            # Las claves de producto tienen formato especial
            is_key = "licencia" in key.lower() or "clave" in key.lower()
            font = ("Cascadia Code", 11, "bold") if is_key else ("Segoe UI", 11, "bold")
            val_color = CYAN if (is_key and val not in ["No disponible", "N/A"]) else TEXT_MAIN

            ctk.CTkLabel(
                self.lic_result, text=str(val),
                font=font, text_color=val_color,
                anchor="w", wraplength=500
            ).grid(row=i + 2, column=1, padx=(0, 16), pady=3, sticky="w")

        # Error si lo hay
        if data.get("error"):
            ctk.CTkLabel(
                self.lic_result,
                text=f"⚠ Nota: {data['error']}",
                font=("Segoe UI", 10), text_color=WARNING,
                wraplength=600, anchor="w"
            ).grid(row=len(fields) + 2, column=0, columnspan=2, padx=16, pady=(8, 16), sticky="w")
        else:
            ctk.CTkFrame(self.lic_result, height=16, fg_color="transparent").grid(
                row=len(fields) + 2, column=0
            )


# ════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════
import multiprocessing

if __name__ == "__main__":
    # Solución al problema de las ventanas infinitas en el archivo .exe compilado.
    # Obligatorio en Windows si alguna librería usa multiprocessing (como 'cpuinfo').
    multiprocessing.freeze_support()
    
    # Comprobar privilegios de administrador SOLO en el proceso principal.
    run_as_admin()
    
    # Configurar tema visual.
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    
    app = ProtoDeusBoostApp()
    app.mainloop()
