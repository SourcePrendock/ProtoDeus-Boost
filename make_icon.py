# =============================================================================
#  make_icon.py — Generador de Ícono para ProtoDeus Boost
#  Crea un ícono .ico vectorial programáticamente usando Pillow.
#  Diseño: fondo oscuro con gradiente, rayo (⚡) centrado en degradado violeta.
#  Tamaños generados: 256, 128, 64, 48, 32, 16 px — todos en un solo .ico.
# =============================================================================

import os
import math
from PIL import Image, ImageDraw, ImageFont


# =============================================================================
#  CONFIGURACIÓN DEL DISEÑO DEL ÍCONO
# =============================================================================

# Colores del diseño (consistentes con la paleta de la aplicación)
COLOR_BG_OUTER   = (10, 10, 15, 255)    # Fondo exterior muy oscuro
COLOR_BG_CENTER  = (28, 20, 60, 255)    # Centro violeta oscuro
COLOR_VIOLET     = (124, 58, 237, 255)  # Violeta principal (borde)
COLOR_BOLT_TOP   = (167, 139, 250, 255) # Rayo — punta (lila claro)
COLOR_BOLT_BOT   = (109, 40, 217, 255)  # Rayo — base (violeta profundo)
COLOR_GLOW       = (124, 58, 237, 80)   # Halo difuso alrededor del rayo


def _lerp_color(c1, c2, t):
    """Interpola linealmente entre dos colores RGBA según el parámetro t (0.0 a 1.0)."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))


def _draw_bolt(draw, cx, cy, size):
    """
    Dibuja un símbolo de rayo (⚡) centrado en (cx, cy) con el tamaño dado.
    Usa un polígono con gradiente vertical (top → bottom) para el efecto premium.
    El rayo es una forma clásica: diagonal hacia abajo-derecha con una muesca central.
    """
    # Escala relativa al tamaño del ícono
    w  = size * 0.28   # ancho total del rayo
    h  = size * 0.58   # alto total del rayo
    ox = cx - w * 0.5  # offset X para centrar
    oy = cy - h * 0.5  # offset Y para centrar

    # Puntos del polígono del rayo (forma de ⚡ clásico)
    pts = [
        (ox + w * 0.65, oy),               # 0: esquina superior derecha
        (ox + w * 0.20, oy + h * 0.44),    # 1: punta interna izquierda (medio)
        (ox + w * 0.55, oy + h * 0.42),    # 2: vértice central derecho
        (ox + w * 0.35, oy + h),           # 3: esquina inferior izquierda
        (ox + w * 0.80, oy + h * 0.52),    # 4: punta interna derecha (medio)
        (ox + w * 0.45, oy + h * 0.54),    # 5: vértice central izquierdo
    ]

    # Dibuja el rayo con el color superior (sin gradiente directo en Pillow para polígonos)
    draw.polygon(pts, fill=COLOR_BOLT_TOP)


def create_icon_at_size(size):
    """
    Crea una imagen RGBA del ícono al tamaño especificado.
    Pasos: fondo con gradiente radial → borde circular violeta → rayo centrado.
    """
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2

    # ── 1. Fondo: gradiente radial del centro hacia afuera ──
    # Se dibuja pixel a pixel para un gradiente suave y circular
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= r:
                t = min(dist / r, 1.0)  # 0 = centro, 1 = borde
                col = _lerp_color(COLOR_BG_CENTER, COLOR_BG_OUTER, t)
                img.putpixel((x, y), col)

    # ── 2. Anti-aliasing del borde circular (máscara suave) ──
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, size - 1, size - 1], fill=255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)

    # ── 3. Halo/glow violeta difuso (círculo semitransparente grande) ──
    glow_r = int(r * 0.70)
    glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw  = ImageDraw.Draw(glow_layer)
    for step in range(12):
        alpha = int(COLOR_GLOW[3] * (1 - step / 12) * 0.4)
        gr    = glow_r - step * int(r * 0.035)
        if gr > 0:
            glow_draw.ellipse(
                [cx - gr, cy - gr, cx + gr, cy + gr],
                fill=(COLOR_GLOW[0], COLOR_GLOW[1], COLOR_GLOW[2], alpha)
            )
    img = Image.alpha_composite(img, glow_layer)
    draw = ImageDraw.Draw(img)

    # ── 4. Borde circular violeta brillante ──
    border_w = max(1, size // 22)
    draw.ellipse(
        [border_w, border_w, size - border_w - 1, size - border_w - 1],
        outline=COLOR_VIOLET, width=border_w
    )

    # ── 5. Rayo centrado con gradiente vertical manual ──
    # Se dibuja primero en una capa de mayor resolución y luego se reduce (supersampling)
    ss = 4  # factor de supersampling para bordes suaves
    ss_size = size * ss
    ss_img  = Image.new("RGBA", (ss_size, ss_size), (0, 0, 0, 0))
    ss_draw = ImageDraw.Draw(ss_img)
    _draw_bolt(ss_draw, ss_size // 2, ss_size // 2, ss_size)
    # Escala de vuelta al tamaño destino con alta calidad (LANCZOS)
    bolt_img = ss_img.resize((size, size), Image.LANCZOS)

    # Aplica el gradiente vertical al rayo (recolorea píxel a píxel)
    bolt_arr = bolt_img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        grad_color = _lerp_color(COLOR_BOLT_TOP, COLOR_BOLT_BOT, t)
        for x in range(size):
            r_val, g_val, b_val, a_val = bolt_arr[x, y]
            if a_val > 10:
                bolt_arr[x, y] = (grad_color[0], grad_color[1], grad_color[2], a_val)

    img = Image.alpha_composite(img, bolt_img)
    return img


def create_icon():
    """
    Genera el archivo icon.ico con múltiples resoluciones para que se vea
    perfectamente en la barra de tareas, la ventana emergente y el explorador.
    Guarda el resultado en assets/icon.ico.
    """
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    # Tamaños requeridos para un .ico completo y de alta calidad
    sizes = [256, 128, 64, 48, 32, 16]

    print("[INFO] Generando ícono programático...")
    images = []
    for s in sizes:
        frame = create_icon_at_size(s)
        images.append(frame)
        print(f"  [OK] {s}x{s} generado")

    # El primer elemento es el principal (256x256); los demás son los tamaños adicionales
    images[0].save(
        target_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"[LISTO] Icono guardado en: {target_path}")


# =============================================================================
#  PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    create_icon()
