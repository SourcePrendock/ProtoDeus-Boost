"""
tools.py — Módulo de herramientas del sistema para ProtoDeus Boost
"""

import subprocess
import winreg
import os
import re


def _run(cmd, shell=True, timeout=60):
    """Ejecuta un comando y retorna (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


# ─────────────────────────────────────────
#  1. Restablecer Red (Network Reset)
# ─────────────────────────────────────────

def restablecer_red():
    """
    Equivalente completo al restablecimiento de red de Windows 10/11.
    Retorna un generador de (mensaje, porcentaje).
    """
    pasos = [
        ("Reseteando catálogo Winsock...",          "netsh winsock reset"),
        ("Reseteando pila IPv4...",                  "netsh int ip reset"),
        ("Reseteando pila IPv6...",                  "netsh int ipv6 reset"),
        ("Reseteando configuración Firewall...",     "netsh advfirewall reset"),
        ("Reseteando parámetros TCP/IP...",          "netsh int tcp reset"),
        ("Liberando configuración IP actual...",     "ipconfig /release"),
        ("Limpiando caché DNS...",                   "ipconfig /flushdns"),
        ("Renovando dirección IP...",                "ipconfig /renew"),
        ("Limpiando caché ARP...",                   "arp -d *"),
        ("Reseteando proxy de red...",               "netsh winhttp reset proxy"),
    ]

    resultados = []
    for i, (msg, cmd) in enumerate(pasos):
        pct = int((i / len(pasos)) * 90)
        yield (msg, pct)
        rc, stdout, stderr = _run(cmd)
        estado = "✅" if rc == 0 else "⚠"
        resultados.append(f"{estado} {msg.rstrip('.')}")

    yield ("✅ Restablecimiento de red completado. Se recomienda reiniciar el PC.", 100)


def get_restablecer_red_resultado():
    """Ejecuta restablecer_red y retorna lista de resultados."""
    return list(restablecer_red())


# ─────────────────────────────────────────
#  2. Información de Licencia Windows
# ─────────────────────────────────────────

def _get_product_key_from_registry():
    """Intenta obtener la clave de producto desde el registro."""
    try:
        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
            try:
                digital_id = winreg.QueryValueEx(k, "DigitalProductId")[0]
                return _decode_product_key(digital_id)
            except Exception:
                return None
    except Exception:
        return None


def _decode_product_key(digital_product_id):
    """Decodifica la clave de producto desde DigitalProductId."""
    try:
        key_offset = 52
        chars = "BCDFGHJKMPQRTVWXY2346789"
        key = ""
        product_id = list(digital_product_id[key_offset:key_offset + 15])
        for i in range(24, -1, -1):
            n = 0
            for j in range(14, -1, -1):
                n = (n << 8) ^ product_id[j]
                product_id[j] = n // 24
                n %= 24
            key = chars[n] + key
            if (i % 5 == 0) and (i != 0):
                key = "-" + key
        return key
    except Exception:
        return None


def _get_oa3_key():
    """Obtiene la clave OA3 del BIOS/UEFI via WMIC."""
    rc, stdout, _ = _run(
        'wmic path SoftwareLicensingService get OA3xOriginalProductKey',
        timeout=15
    )
    if rc == 0 and stdout:
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        for line in lines:
            if len(line) == 29 and line.count("-") == 4:
                return line
    return None


def _get_slmgr_info():
    """Obtiene información de licencia via slmgr /dli."""
    rc, stdout, _ = _run("cscript //nologo %windir%\\system32\\slmgr.vbs /dli", timeout=30)
    return stdout if rc == 0 else ""


def _get_slmgr_xpr():
    """Obtiene estado de activación via slmgr /xpr."""
    rc, stdout, _ = _run("cscript //nologo %windir%\\system32\\slmgr.vbs /xpr", timeout=30)
    return stdout if rc == 0 else ""


def _detect_license_type(slmgr_output, oa3_key):
    """Detecta el tipo de licencia basándose en la salida de slmgr."""
    output_lower = slmgr_output.lower()
    tipo = "Desconocido"
    descripcion = ""

    if "volume:gvlk" in output_lower or "kms" in output_lower or "kmsclient" in output_lower:
        tipo = "KMS (Genérica / Volumen)"
        descripcion = "Licencia de volumen activada por servidor KMS. Común en empresas y versiones genéricas."
    elif "oem" in output_lower:
        tipo = "OEM"
        descripcion = "Licencia vinculada al hardware de fábrica. No transferible a otra PC."
    elif "retail" in output_lower:
        tipo = "Retail (Comprada)"
        descripcion = "Licencia de venta al público. Transferible a otra PC."
    elif oa3_key:
        tipo = "OEM (BIOS/UEFI)"
        descripcion = "Licencia incrustada en el firmware del fabricante."
    elif "coa" in output_lower:
        tipo = "COA (Certificate of Authenticity)"
        descripcion = "Licencia de sticker físico adjunto al equipo."

    return tipo, descripcion


def get_license_info():
    """
    Obtiene información completa de la licencia de Windows.
    Retorna un diccionario con todos los datos.
    """
    info = {
        "clave_instalada": "No disponible",
        "clave_bios": "No disponible",
        "tipo": "Desconocido",
        "descripcion_tipo": "",
        "estado_activacion": "Desconocido",
        "edicion": "Desconocida",
        "nombre_licencia": "",
        "descripcion": "",
        "expiracion": "",
        "error": None,
    }

    try:
        # Clave instalada desde registro
        reg_key = _get_product_key_from_registry()
        if reg_key:
            info["clave_instalada"] = reg_key

        # Clave OA3 del BIOS
        oa3 = _get_oa3_key()
        if oa3:
            info["clave_bios"] = oa3

        # Información de slmgr
        slmgr_dli = _get_slmgr_info()
        slmgr_xpr = _get_slmgr_xpr()

        if slmgr_dli:
            # Extraer nombre de licencia
            match_name = re.search(r"Name:\s*(.+)", slmgr_dli, re.IGNORECASE)
            if match_name:
                info["nombre_licencia"] = match_name.group(1).strip()

            # Extraer descripción
            match_desc = re.search(r"Description:\s*(.+)", slmgr_dli, re.IGNORECASE)
            if match_desc:
                info["descripcion"] = match_desc.group(1).strip()

            # Estado de activación
            if "licensed" in slmgr_dli.lower():
                info["estado_activacion"] = "✅ Activado"
            elif "notification" in slmgr_dli.lower():
                info["estado_activacion"] = "⚠ En período de notificación"
            elif "oob grace" in slmgr_dli.lower():
                info["estado_activacion"] = "⚠ En período de gracia"
            else:
                info["estado_activacion"] = "❌ No activado"

        if slmgr_xpr:
            lines = [l.strip() for l in slmgr_xpr.splitlines() if l.strip()]
            for line in lines:
                if "permanently activated" in line.lower():
                    info["expiracion"] = "Activación permanente"
                elif "expire" in line.lower():
                    info["expiracion"] = line

        # Tipo de licencia
        tipo, desc = _detect_license_type(slmgr_dli, oa3)
        info["tipo"] = tipo
        info["descripcion_tipo"] = desc

        # Edición desde registro
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
                info["edicion"] = winreg.QueryValueEx(k, "EditionID")[0]
        except Exception:
            pass

    except Exception as e:
        info["error"] = str(e)

    return info
