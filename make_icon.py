# =============================================================================
#  make_icon.py — Generador de Ícono HD para ProtoDeus Boost
#  Crea un ícono .ico de alta definición usando renderizado a resolución 8x
#  y reducción con LANCZOS para obtener bordes nítidos como Chrome u Office.
#  Tamaños generados: 256, 128, 64, 48, 32, 16 px — todos en un solo .ico.
# =============================================================================

import os
import math
from PIL import Image, ImageDraw, ImageFilter

# =============================================================================
#  CONFIGURACIÓN DEL DISEÑO DEL ÍCONO
# =============================================================================

# Colores del diseño (consistentes con la paleta de la aplicación)
COLOR_BG_OUTER   = (10, 10, 15, 255)    # Fondo exterior muy oscuro
COLOR_BG_CENTER  = (30, 22, 65, 255)    # Centro violeta oscuro (más saturado)
COLOR_VIOLET     = (124, 58, 237, 255)  # Violeta principal (borde)
COLOR_VIOLET_BRT = (147, 87, 255, 255)  # Violeta brillante (borde highlight)
COLOR_BOLT_TOP   = (180, 160, 255, 255) # Rayo — punta superior (lila claro brillante)
COLOR_BOLT_MID   = (140, 100, 250, 255) # Rayo — centro (violeta medio)
COLOR_BOLT_BOT   = (100, 35, 210, 255)  # Rayo — base (violeta profundo)
COLOR_GLOW       = (124, 58, 237, 100)  # Halo difuso alrededor del rayo
COLOR_BOLT_GLOW  = (167, 139, 250, 60)  # Resplandor suave del rayo
COLOR_SHADOW     = (20, 10, 50, 120)    # Sombra del rayo


def _lerp_color(c1, c2, t):
    """Interpola linealmente entre dos colores RGBA según el parámetro t (0.0 a 1.0)."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))


def _draw_radial_gradient(img, cx, cy, radius, inner_color, outer_color):
    """
    Dibuja un gradiente radial de alta calidad usando bandas concéntricas
    para evitar el método pixel-a-pixel que es lento y borroso.
    """
    draw = ImageDraw.Draw(img)
    steps = max(radius, 200)  # Más pasos = gradiente más suave
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        color = _lerp_color(inner_color, outer_color, t)
        if r > 0:
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                fill=color
            )


def _get_bolt_polygon(cx, cy, size):
    """
    Retorna los puntos del polígono del rayo (⚡) con proporciones refinadas.
    Forma más angular y definida que la versión anterior.
    """
    w = size * 0.30   # ancho total del rayo
    h = size * 0.56   # alto total del rayo
    ox = cx - w * 0.45
    oy = cy - h * 0.50

    # Polígono del rayo — forma ⚡ con ángulos más definidos
    return [
        (ox + w * 0.60, oy),                # 0: punta superior derecha
        (ox + w * 0.10, oy + h * 0.46),     # 1: vértice izquierdo medio
        (ox + w * 0.48, oy + h * 0.43),     # 2: muesca central derecha
        (ox + w * 0.32, oy + h),            # 3: punta inferior
        (ox + w * 0.85, oy + h * 0.52),     # 4: vértice derecho medio
        (ox + w * 0.50, oy + h * 0.55),     # 5: muesca central izquierda
    ]


def _draw_bolt_with_gradient(img, cx, cy, size):
    """
    Dibuja el rayo con gradiente vertical y efecto de profundidad.
    Usa una capa separada para el gradiente y composición alpha.
    """
    s = img.size[0]
    pts = _get_bolt_polygon(cx, cy, size)

    # Crear máscara del rayo
    mask = Image.new("L", (s, s), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.polygon(pts, fill=255)

    # Crear capa del rayo con gradiente vertical
    bolt_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bolt_draw = ImageDraw.Draw(bolt_layer)

    # Calcular bounding box del rayo
    min_y = min(p[1] for p in pts)
    max_y = max(p[1] for p in pts)
    height = max_y - min_y

    # Dibujar bandas horizontales con gradiente
    for y in range(s):
        if y < min_y or y > max_y:
            continue
        t = (y - min_y) / max(height, 1)
        if t < 0.5:
            color = _lerp_color(COLOR_BOLT_TOP, COLOR_BOLT_MID, t * 2)
        else:
            color = _lerp_color(COLOR_BOLT_MID, COLOR_BOLT_BOT, (t - 0.5) * 2)
        bolt_draw.line([(0, y), (s - 1, y)], fill=color)

    # Aplicar la máscara al rayo
    bolt_layer.putalpha(mask)

    # Componer sobre la imagen
    img.paste(Image.alpha_composite(
        Image.new("RGBA", (s, s), (0, 0, 0, 0)),
        bolt_layer
    ), (0, 0), bolt_layer)

    return img


def create_icon_master(master_size=2048):
    """
    Crea la imagen maestra del ícono a alta resolución (2048x2048).
    Todos los elementos se renderizan a esta resolución y luego se reducen
    con LANCZOS para obtener bordes nítidos y anti-aliasing perfecto.
    """
    s = master_size
    cx, cy = s // 2, s // 2
    r = s // 2

    # ── 1. Fondo: gradiente radial suave ──
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    _draw_radial_gradient(img, cx, cy, r, COLOR_BG_CENTER, COLOR_BG_OUTER)

    # ── 2. Máscara circular con anti-aliasing ──
    # Renderizar la máscara a 2x para AA perfecto
    mask_ss = 2
    mask_size = s * mask_ss
    mask = Image.new("L", (mask_size, mask_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, mask_size - 1, mask_size - 1], fill=255)
    mask = mask.resize((s, s), Image.LANCZOS)
    img.putalpha(mask)

    # ── 3. Halo/glow violeta difuso (varias capas con blur) ──
    glow_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    # Glow central grande
    glow_r = int(r * 0.65)
    for step in range(20):
        alpha = int(COLOR_GLOW[3] * (1 - step / 20) * 0.5)
        gr = glow_r - step * int(r * 0.02)
        if gr > 0 and alpha > 0:
            glow_draw.ellipse(
                [cx - gr, cy - gr, cx + gr, cy + gr],
                fill=(COLOR_GLOW[0], COLOR_GLOW[1], COLOR_GLOW[2], alpha)
            )
    # Aplicar blur gaussiano para suavizar el glow
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=int(s * 0.04)))
    img = Image.alpha_composite(img, glow_layer)

    # ── 4. Resplandor del rayo (antes de dibujarlo) ──
    bolt_glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bolt_glow_draw = ImageDraw.Draw(bolt_glow)
    glow_pts = _get_bolt_polygon(cx, cy, s)
    # Dibujar forma expandida como glow
    bolt_glow_draw.polygon(glow_pts, fill=COLOR_BOLT_GLOW)
    bolt_glow = bolt_glow.filter(ImageFilter.GaussianBlur(radius=int(s * 0.035)))
    img = Image.alpha_composite(img, bolt_glow)

    # ── 5. Sombra del rayo (offset hacia abajo) ──
    shadow_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_offset = int(s * 0.012)
    shadow_pts = [(x, y + shadow_offset) for x, y in _get_bolt_polygon(cx, cy, s)]
    shadow_draw.polygon(shadow_pts, fill=COLOR_SHADOW)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=int(s * 0.015)))
    img = Image.alpha_composite(img, shadow_layer)

    # ── 6. Rayo con gradiente vertical ──
    img = _draw_bolt_with_gradient(img, cx, cy, s)

    # ── 7. Highlight sutil en la parte superior del rayo ──
    highlight = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(highlight)
    bolt_pts = _get_bolt_polygon(cx, cy, s)
    min_y_bolt = min(p[1] for p in bolt_pts)
    max_y_bolt = max(p[1] for p in bolt_pts)
    h_bolt = max_y_bolt - min_y_bolt
    # Máscara de highlight solo en el tercio superior
    h_mask = Image.new("L", (s, s), 0)
    h_mask_draw = ImageDraw.Draw(h_mask)
    h_mask_draw.polygon(bolt_pts, fill=255)
    # Gradiente de highlight (solo arriba)
    for y in range(s):
        if y < min_y_bolt or y > min_y_bolt + h_bolt * 0.35:
            continue
        t = (y - min_y_bolt) / (h_bolt * 0.35)
        alpha = int(60 * (1 - t))
        h_draw.line([(0, y), (s - 1, y)], fill=(255, 255, 255, alpha))
    highlight.putalpha(h_mask)
    img = Image.alpha_composite(img, highlight)

    # ── 8. Borde circular violeta con gradiente ──
    border_w = max(2, s // 20)
    # Borde exterior
    draw = ImageDraw.Draw(img)
    draw.ellipse(
        [border_w // 2, border_w // 2, s - border_w // 2 - 1, s - border_w // 2 - 1],
        outline=COLOR_VIOLET, width=border_w
    )
    # Línea interior más brillante (efecto de profundidad)
    inner_bw = max(1, border_w // 3)
    draw.ellipse(
        [border_w - inner_bw, border_w - inner_bw,
         s - border_w + inner_bw - 1, s - border_w + inner_bw - 1],
        outline=(*COLOR_VIOLET_BRT[:3], 100), width=inner_bw
    )

    # Reaplicar la máscara circular para limpiar bordes
    img.putalpha(mask)

    return img


def create_icon():
    """
    Genera el archivo icon.ico con múltiples resoluciones de alta calidad.
    Renderiza todo a 2048x2048 y reduce con LANCZOS para cada tamaño.
    Esto produce íconos nítidos comparables a los de Chrome o Microsoft Office.
    """
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    # Tamaños requeridos para un .ico completo y de alta calidad
    sizes = [256, 128, 64, 48, 32, 16]

    print("[INFO] Generando ícono HD con supersampling...")
    print("  [1/2] Renderizando imagen maestra a 2048x2048...")
    master = create_icon_master(2048)
    print("  [OK] Imagen maestra generada")

    print("  [2/2] Generando tamaños finales con LANCZOS...")
    images = []
    for s in sizes:
        # Reducción con LANCZOS (mejor anti-aliasing disponible)
        frame = master.resize((s, s), Image.LANCZOS)
        images.append(frame)
        print(f"    [OK] {s}x{s} generado")

    # El primer elemento es el principal (256x256); los demás son los tamaños adicionales
    images[0].save(
        target_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"[LISTO] Ícono HD guardado en: {target_path}")


# =============================================================================
#  PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    create_icon()
