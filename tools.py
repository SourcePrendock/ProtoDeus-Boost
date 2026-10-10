# =============================================================================
#  tools.py — Módulo de Herramientas del Sistema
#  Contiene: Restablecimiento de red, Detección de licencia Windows,
#            Reparaciones de Windows (corregidas), Limpieza de Teams/OneDrive.
# =============================================================================

import subprocess
import winreg
import os
import re
import socket
import time
import statistics
import urllib.request
import threading
import json


# =============================================================================
#  HELPERS DE EJECUCIÓN DE COMANDOS
# =============================================================================

CREATE_NO_WINDOW = 0x08000000


def _run(cmd, shell=True, timeout=60):
    """
    Ejecuta un comando del sistema de forma silenciosa y captura su salida.
    Retorna (returncode, stdout, stderr).
    """
    try:
        r = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=timeout,
            creationflags=CREATE_NO_WINDOW
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def _run_ps(cmd, timeout=60):
    """
    Ejecuta un comando PowerShell de forma silenciosa y captura su salida.
    Útil para cmdlets de PowerShell que no existen en cmd.
    """
    full_cmd = f'powershell -NonInteractive -NoProfile -Command "{cmd}"'
    return _run(full_cmd, shell=True, timeout=timeout)


# =============================================================================
#  RESTABLECIMIENTO DE RED
# =============================================================================

def restablecer_red():
    """
    Resetea toda la pila de red de Windows: Winsock, TCP/IP, IPv4/IPv6,
    Firewall, DNS, ARP y proxy. Equivale al 'Restablecimiento de red' de
    la configuración de Windows 10/11.
    Genera (mensaje, porcentaje) como generador para actualizar la UI.
    """
    pasos = [
        ("Reseteando catálogo Winsock...",       "netsh winsock reset"),
        ("Reseteando pila IPv4...",              "netsh int ip reset"),
        ("Reseteando pila IPv6...",              "netsh int ipv6 reset"),
        ("Reseteando configuración Firewall...", "netsh advfirewall reset"),
        ("Reseteando parámetros TCP/IP...",      "netsh int tcp reset"),
        ("Liberando configuración IP actual...", "ipconfig /release"),
        ("Limpiando caché DNS...",               "ipconfig /flushdns"),
        ("Renovando dirección IP...",            "ipconfig /renew"),
        ("Limpiando caché ARP...",               "arp -d *"),
        ("Reseteando proxy de red...",           "netsh winhttp reset proxy"),
    ]
    for i, (msg, cmd) in enumerate(pasos):
        yield (msg, int((i / len(pasos)) * 90))
        _run(cmd)
    yield ("✅ Restablecimiento completado. Se recomienda reiniciar el PC.", 100)


# =============================================================================
#  DETECCIÓN DE LICENCIA DE WINDOWS
# =============================================================================

def _get_product_key_from_registry():
    """
    Intenta leer y decodificar la clave de producto desde el registro de Windows
    (DigitalProductId). No siempre está disponible en licencias digitales.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            try:
                return _decode_product_key(winreg.QueryValueEx(k, "DigitalProductId")[0])
            except Exception:
                return None
    except Exception:
        return None


def _decode_product_key(digital_product_id):
    """
    Decodifica el DigitalProductId binario del registro en una clave legible
    en formato XXXXX-XXXXX-XXXXX-XXXXX-XXXXX.
    """
    try:
        chars = "BCDFGHJKMPQRTVWXY2346789"
        key = ""
        product_id = list(digital_product_id[52:67])
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
    """
    Obtiene la clave OEM (OA3) incrustada en el BIOS/UEFI del fabricante
    usando WMIC. Esta clave suele ser la licencia real de equipos OEM.
    """
    rc, stdout, _ = _run("wmic path SoftwareLicensingService get OA3xOriginalProductKey", timeout=15)
    if rc == 0 and stdout:
        for line in [l.strip() for l in stdout.splitlines() if l.strip()]:
            if len(line) == 29 and line.count("-") == 4:
                return line
    return None


def _get_slmgr_info():
    """
    Ejecuta slmgr.vbs /dli para obtener información detallada de la licencia
    instalada actualmente (nombre, descripción, estado de activación).
    """
    rc, stdout, _ = _run("cscript //nologo %windir%\\system32\\slmgr.vbs /dli", timeout=30)
    return stdout if rc == 0 else ""


def _get_slmgr_xpr():
    """
    Ejecuta slmgr.vbs /xpr para obtener la fecha de expiración de la licencia
    o confirmar que la activación es permanente.
    """
    rc, stdout, _ = _run("cscript //nologo %windir%\\system32\\slmgr.vbs /xpr", timeout=30)
    return stdout if rc == 0 else ""


def _detect_license_type(slmgr_output, oa3_key):
    """
    Clasifica el tipo de licencia de Windows basándose en la salida de slmgr
    y la presencia de clave OA3 en BIOS. Retorna (tipo, descripcion).
    """
    low = slmgr_output.lower()
    if "volume:gvlk" in low or "kms" in low or "kmsclient" in low:
        return "KMS (Genérica / Volumen)", "Licencia de volumen activada por servidor KMS. Común en empresas y versiones genéricas."
    elif "oem" in low:
        return "OEM", "Licencia vinculada al hardware de fábrica. No transferible a otra PC."
    elif "retail" in low:
        return "Retail (Comprada)", "Licencia de venta al público. Transferible a otra PC."
    elif oa3_key:
        return "OEM (BIOS/UEFI)", "Licencia incrustada en el firmware del fabricante."
    elif "coa" in low:
        return "COA (Certificate of Authenticity)", "Licencia de sticker físico adjunto al equipo."
    return "Desconocido", ""


def get_license_info():
    """
    Recopila toda la información de licencia de Windows disponible:
    clave instalada, clave BIOS/UEFI, tipo, estado de activación y expiración.
    Retorna un diccionario con todos los campos.
    """
    info = {
        "clave_instalada": "No disponible", "clave_bios": "No disponible",
        "tipo": "Desconocido", "descripcion_tipo": "",
        "estado_activacion": "Desconocido", "edicion": "Desconocida",
        "nombre_licencia": "", "descripcion": "", "expiracion": "", "error": None,
    }
    try:
        # Leer clave desde registro (puede no estar en licencias digitales)
        reg_key = _get_product_key_from_registry()
        if reg_key:
            info["clave_instalada"] = reg_key

        # Leer clave OA3 del BIOS/UEFI
        oa3 = _get_oa3_key()
        if oa3:
            info["clave_bios"] = oa3

        # Obtener info detallada de slmgr
        slmgr_dli = _get_slmgr_info()
        slmgr_xpr = _get_slmgr_xpr()

        if slmgr_dli:
            # Extraer nombre de licencia
            m = re.search(r"Name:\s*(.+)", slmgr_dli, re.IGNORECASE)
            if m:
                info["nombre_licencia"] = m.group(1).strip()
            # Extraer descripción
            m = re.search(r"Description:\s*(.+)", slmgr_dli, re.IGNORECASE)
            if m:
                info["descripcion"] = m.group(1).strip()
            # Determinar estado de activación
            low = slmgr_dli.lower()
            if "licensed" in low:
                info["estado_activacion"] = "✅ Activado"
            elif "notification" in low:
                info["estado_activacion"] = "⚠ En período de notificación"
            elif "oob grace" in low:
                info["estado_activacion"] = "⚠ En período de gracia"
            else:
                info["estado_activacion"] = "❌ No activado"

        if slmgr_xpr:
            for line in [l.strip() for l in slmgr_xpr.splitlines() if l.strip()]:
                if "permanently activated" in line.lower():
                    info["expiracion"] = "Activación permanente"
                elif "expire" in line.lower():
                    info["expiracion"] = line

        tipo, desc = _detect_license_type(slmgr_dli, oa3)
        info["tipo"] = tipo
        info["descripcion_tipo"] = desc

        # Leer edición de Windows desde registro
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
                info["edicion"] = winreg.QueryValueEx(k, "EditionID")[0]
        except Exception:
            pass

    except Exception as e:
        info["error"] = str(e)
    return info


# =============================================================================
#  DEFINICIÓN DE REPARACIONES DE WINDOWS
#  Cada entrada tiene: nombre, descripción, tiempo estimado, y lista de pasos.
#  Cada paso es una tupla (mensaje_ui, comando_cmd).
#  NOTA: Todos los comandos se ejecutan dentro de Windows activo (no WinPE).
# =============================================================================

REPARACIONES_WINDOWS = {
    # ── Módulo 1: Reparación Integrada de Sistema (SFC + DISM) ──
    "system": {
        "nombre": "🛡  Reparación Integrada de Sistema (SFC + DISM)",
        "descripcion": "Comprueba y repara la integridad del núcleo de Windows y controladores base usando DISM y SFC.",
        "tiempo_estimado": "~15-30 min",
        "pasos": [
            ("Reparando la imagen del sistema con DISM (puede tardar bastante)...",
             "DISM /Online /Cleanup-Image /RestoreHealth"),
            ("Verificando y reparando archivos del sistema con SFC...",
             "sfc /scannow"),
        ],
    },

    # ── Módulo 2: Reparación de Entorno de Usuario / Shell & Apps ──
    "shell": {
        "nombre": "🖥  Reparación de Entorno de Usuario (Shell & Apps)",
        "descripcion": "Soluciona congelamientos del explorador, barra de tareas, menú de inicio, aplicaciones UWP y búsqueda.",
        "tiempo_estimado": "~2-5 min",
        "pasos": [
            ("Deteniendo servicios de búsqueda y explorador...",
             "taskkill /f /im explorer.exe 2>nul & net stop WSearch /y 2>nul"),
            ("Limpiando cachés de Iconos y Búsqueda...",
             r'del /f /q "%localappdata%\IconCache.db" 2>nul & '
             r'del /f /q "%ProgramData%\Microsoft\Search\Data\Applications\Windows\Windows.edb" 2>nul & '
             r'rmdir /s /q "%ProgramData%\Microsoft\Search\Data\Applications\Windows" 2>nul'),
            ("Re-registrando aplicaciones universales (AppX)...",
             'powershell -NonInteractive -Command "Get-AppXPackage -AllUsers | Foreach {Add-AppxPackage -DisableDevelopmentMode -Register \\"$($_.InstallLocation)\\AppXManifest.xml\\" -ErrorAction SilentlyContinue}"'),
            ("Reiniciando servicios y explorador...",
             'net start WSearch & powershell -NonInteractive -Command "Start-Process explorer.exe"'),
        ],
    },

    # ── Módulo 3: Reparación de Servicios y Red ──
    "services": {
        "nombre": "⚙  Reparación de Servicios y Red (Update, Audio, Defender)",
        "descripcion": "Restablece la infraestructura de servicios para actualizaciones, sonido, red y protección.",
        "tiempo_estimado": "~3-5 min",
        "pasos": [
            ("Deteniendo servicios de Update, Audio y Criptografía...",
             "net stop wuauserv /y & net stop bits /y & net stop cryptsvc /y & net stop audiosrv /y"),
            ("Purgando directorios de actualizaciones (SoftwareDistribution y catroot2)...",
             r'rd /s /q "%windir%\SoftwareDistribution" 2>nul & rd /s /q "%windir%\System32\catroot2" 2>nul'),
            ("Restableciendo pila de red y caché DNS...",
             "netsh winsock reset & netsh int ip reset & ipconfig /flushdns"),
            ("Reiniciando servicios y actualizando Windows Defender...",
             'net start wuauserv & net start bits & net start cryptsvc & net start audiosrv & '
             r'"%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate'),
        ],
    },
    
    # ── Módulo 4: Reparación Avanzada / In-Place Upgrade (Vía ISO) ──
    "advanced_iso": {
        "nombre": "💽  Reparación Avanzada / In-Place Upgrade",
        "descripcion": "Abre la página oficial de Microsoft para descargar la ISO de tu versión de Windows y reparar conservando archivos.",
        "tiempo_estimado": "~1 min",
        "pasos": [
            ("Identificando versión de Windows y abriendo página de descarga oficial...",
             'powershell -NonInteractive -NoProfile -Command "'
             '$os = (Get-CimInstance Win32_OperatingSystem).Caption; '
             'if ($os -match \'Windows 11\') { Start-Process \'https://www.microsoft.com/software-download/windows11\' } '
             'else { Start-Process \'https://www.microsoft.com/software-download/windows10\' }"'),
        ],
    },
}


# =============================================================================
#  FUNCIÓN PRINCIPAL DE REPARACIÓN
#  Ejecuta los pasos de una reparación seleccionada y emite progreso a la UI.
# =============================================================================

def reparar_windows(repair_key):
    """
    Ejecuta todos los pasos de la reparación indicada por repair_key.
    Es un generador que emite (mensaje, porcentaje) para actualizar la UI en tiempo real.
    Maneja DISM RestoreHealth con progreso simulado por tiempo (puede tardar 20+ min).
    """
    import queue as _queue

    repair = REPARACIONES_WINDOWS.get(repair_key)
    if not repair:
        yield ("❌ Reparación no encontrada.", 100)
        return

    pasos = repair["pasos"]
    total = len(pasos)
    est = repair.get("tiempo_estimado", "desconocido")
    yield (f"⏱ Tiempo estimado: {est}", 0)

    for i, (msg, cmd) in enumerate(pasos):
        pct_start = int((i / total) * 88)
        pct_end   = int(((i + 1) / total) * 88)
        yield (f"[{i+1}/{total}] {msg}", pct_start)

        # DISM RestoreHealth puede tardar mucho: se ejecuta en hilo aparte con barra simulada
        is_dism_restore = "DISM" in cmd and "RestoreHealth" in cmd
        if is_dism_restore:
            q = _queue.Queue()

            def _dism_worker(cmd=cmd, q=q, ps=pct_start, pe=pct_end):
                # Ejecuta DISM en un hilo interno mientras reporta progreso al exterior
                t_inner = threading.Thread(target=lambda: _run(cmd, timeout=2400), daemon=True)
                t_inner.start()
                elapsed = 0
                estimated = 1200  # estimado en segundos (20 min)
                while t_inner.is_alive():
                    time.sleep(30)
                    elapsed += 30
                    frac = min(elapsed / estimated, 0.95)
                    pct = int(ps + frac * (pe - ps))
                    mins_left = max(1, int((estimated - elapsed) / 60))
                    bar = "█" * int(frac * 20) + "░" * (20 - int(frac * 20))
                    q.put((f"  [{bar}] {int(frac*100)}% — DISM reparando... ~{mins_left} min restantes", pct))
                t_inner.join()
                q.put(None)  # Señal de fin

            dism_thread = threading.Thread(target=_dism_worker, daemon=True)
            dism_thread.start()
            while True:
                item = q.get()
                if item is None:
                    break
                yield item
            dism_thread.join()
            yield (f"  ✅ DISM RestoreHealth completado", pct_end)
        elif "sfc" in cmd.lower() and "/scannow" in cmd.lower():
            # SFC /scannow con reporte de porcentaje en vivo
            import preventive_maintenance
            for msg_sfc, p_sfc in preventive_maintenance.reparar_sfc_rapido():
                sub_pct = int(pct_start + (p_sfc / 100.0) * (pct_end - pct_start))
                yield (f"  {msg_sfc}", sub_pct)
        else:
            # Ejecución normal de comandos del sistema
            rc, stdout, stderr = _run(cmd, timeout=600)
            if rc == 0:
                yield (f"  ✅ Completado", pct_end)
            else:
                err = (stderr or stdout or "").strip()[:120] or "Sin detalles"
                yield (f"  ⚠ {err}", pct_end)

    yield (f"✅ {repair['nombre'].split('  ', 1)[-1]} completado.", 100)


# =============================================================================
#  LIMPIEZA DE MICROSOFT TEAMS
# =============================================================================

def limpiar_teams():
    """
    Limpieza TOTAL de Microsoft Teams: elimina absolutamente todo rastro de Teams
    del equipo. Cierra procesos, elimina Teams clásico y nuevo (MSIX), borra todos
    los datos de perfil, caché, credenciales, registros y tareas programadas.
    Después de esta limpieza, reinstalar Teams mostrará la pantalla de primer uso.
    """
    import shutil

    pasos = [
        # 1. Cierra todas las instancias de Teams (clásico, nuevo, actualizador)
        ("Cerrando todos los procesos de Microsoft Teams...",
         'taskkill /f /im Teams.exe /t 2>nul & '
         'taskkill /f /im ms-teams.exe /t 2>nul & '
         'taskkill /f /im Update.exe /t 2>nul & '
         'taskkill /f /im MSTeamsUpdateService.exe /t 2>nul & '
         'taskkill /f /im TeamsUpdaterService.exe /t 2>nul'),

        # 2. Desinstalar Teams nuevo (MSIX/AppX) si está instalado
        ("Desinstalando Teams nuevo (MSIX) si existe...",
         'powershell -NonInteractive -NoProfile -Command "'
         'Get-AppxPackage *MSTeams* -AllUsers -ErrorAction SilentlyContinue | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue; '
         'Get-AppxPackage *MicrosoftTeams* -AllUsers -ErrorAction SilentlyContinue | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"'),

        # 3. Elimina datos de Teams clásico en AppData\Roaming
        ("Eliminando datos de Teams en AppData\\Roaming...",
         r'rmdir /s /q "%AppData%\Microsoft\Teams" 2>nul'),

        # 4. Elimina datos de Teams en AppData\Local (instalación, caché, addins)
        ("Eliminando datos de Teams en AppData\\Local...",
         r'rmdir /s /q "%LocalAppData%\Microsoft\Teams" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\TeamsMeetingAddin" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\TeamsPresenceAddin" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\TeamsMeetingAdd-in" 2>nul'),

        # 5. Elimina paquetes de Teams nuevo (MSIX) en Packages
        ("Eliminando paquetes de Teams nuevo en Packages...",
         'powershell -NonInteractive -NoProfile -Command "'
         '$folders = Get-ChildItem \\"$env:LOCALAPPDATA\\Packages\\" -Directory -Filter \\"MSTeams_*\\" -ErrorAction SilentlyContinue; '
         '$folders += Get-ChildItem \\"$env:LOCALAPPDATA\\Packages\\" -Directory -Filter \\"MicrosoftTeams_*\\" -ErrorAction SilentlyContinue; '
         'foreach ($f in $folders) { Remove-Item $f.FullName -Recurse -Force -ErrorAction SilentlyContinue }"'),

        # 6. Elimina configuración compartida de Teams
        ("Eliminando configuración compartida de Teams...",
         'powershell -NonInteractive -NoProfile -Command "'
         '$p = \\"$env:LOCALAPPDATA\\Publishers\\8wekyb3d8bbwe\\TeamsSharedConfig\\"; '
         'if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }"'),

        # 7. Elimina caché de identidad y tokens (sesiones guardadas)
        ("Eliminando caché de identidad, tokens y sesiones...",
         r'rmdir /s /q "%LocalAppData%\Microsoft\IdentityCache" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\OneAuth" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\TokenBroker" 2>nul & '
         r'rmdir /s /q "%AppData%\Microsoft\Credentials" 2>nul'),

        # 8. Elimina archivos temporales de Teams
        ("Eliminando caché de Teams en Temp...",
         r'del /f /s /q "%Temp%\*teams*" 2>nul & '
         r'del /f /s /q "%Temp%\*MSTeams*" 2>nul'),

        # 9. Limpia credenciales de Teams del Credential Manager
        ("Eliminando credenciales de Teams del Credential Manager...",
         'powershell -NonInteractive -NoProfile -Command "'
         '$creds = cmdkey /list 2>$null | Select-String \\"MicrosoftTeams|msteams|teams.microsoft\\" -ErrorAction SilentlyContinue; '
         'foreach ($line in $creds) { '
         '  $target = ($line -split \\"Target:\\s*\\")[1]; '
         '  if ($target) { cmdkey /delete:$target 2>$null } '
         '}"'),

        # 10. Elimina TODAS las entradas de registro de Teams
        ("Limpiando entradas de registro de Teams...",
         'reg delete "HKCU\\Software\\Microsoft\\Office\\Teams" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Teams" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\Microsoft\\Teams" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Teams" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Office\\16.0\\Common\\Identity" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Teams" /f 2>nul'),

        # 11. Elimina auto-start de Teams
        ("Eliminando entradas de inicio automático de Teams...",
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "com.squirrel.Teams.Teams" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "Teams" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "MSTeams" /f 2>nul'),

        # 12. Elimina tareas programadas de Teams
        ("Eliminando tareas programadas de Teams...",
         'schtasks /delete /tn "\\Microsoft\\Teams\\*" /f 2>nul & '
         'schtasks /delete /tn "MicrosoftTeamsUpdateTask" /f 2>nul'),
    ]

    total = len(pasos)
    for i, (msg, cmd) in enumerate(pasos):
        yield (msg, int((i / total) * 90))
        _run(cmd, timeout=60)
    yield ("✅ Teams eliminado completamente. Al reinstalar aparecerá como nuevo, sin cuentas ni sesiones.", 100)


# =============================================================================
#  LIMPIEZA DE ONEDRIVE
# =============================================================================

def limpiar_onedrive():
    """
    Limpieza TOTAL de OneDrive: elimina absolutamente todo rastro de OneDrive
    del equipo. Cierra procesos, desregistra el cliente, elimina datos de perfil,
    caché, credenciales, registros, integración con el explorador y tareas.
    Después de esta limpieza, reinstalar OneDrive mostrará la pantalla de primer uso.
    """
    pasos = [
        # 1. Cierra todos los procesos de OneDrive
        ("Cerrando todos los procesos de OneDrive...",
         'taskkill /f /im OneDrive.exe /t 2>nul & '
         'taskkill /f /im OneDriveSetup.exe /t 2>nul & '
         'taskkill /f /im FileSyncHelper.exe /t 2>nul & '
         'taskkill /f /im FileCoAuth.exe /t 2>nul'),

        # 2. Desregistra OneDrive del sistema (x64 y x86)
        ("Desregistrando OneDrive del sistema...",
         'if exist "%SystemRoot%\\SysWOW64\\OneDriveSetup.exe" '
         '"%SystemRoot%\\SysWOW64\\OneDriveSetup.exe" /unregister 2>nul & '
         'if exist "%SystemRoot%\\System32\\OneDriveSetup.exe" '
         '"%SystemRoot%\\System32\\OneDriveSetup.exe" /unregister 2>nul'),

        # 3. Elimina datos de OneDrive en AppData\Local
        ("Eliminando datos de OneDrive en AppData\\Local...",
         r'rmdir /s /q "%LocalAppData%\Microsoft\OneDrive" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\OneDrive" 2>nul'),

        # 4. Elimina datos de OneDrive en AppData\Roaming
        ("Eliminando datos de OneDrive en AppData\\Roaming...",
         r'rmdir /s /q "%AppData%\Microsoft\OneDrive" 2>nul'),

        # 5. Elimina carpeta de usuario y logs
        ("Eliminando carpeta de OneDrive del usuario y logs...",
         r'rmdir /s /q "%UserProfile%\OneDrive" 2>nul & '
         r'rmdir /s /q "%ProgramData%\Microsoft OneDrive" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\OneDrive\setup\logs" 2>nul'),

        # 6. Elimina caché de identidad y tokens de OneDrive
        ("Eliminando caché de identidad y tokens de OneDrive...",
         r'rmdir /s /q "%LocalAppData%\Microsoft\IdentityCache" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\TokenBroker" 2>nul'),

        # 7. Limpia credenciales de OneDrive del Credential Manager
        ("Eliminando credenciales de OneDrive del Credential Manager...",
         'powershell -NonInteractive -NoProfile -Command "'
         '$creds = cmdkey /list 2>$null | Select-String \\"OneDrive|onedrive\\" -ErrorAction SilentlyContinue; '
         'foreach ($line in $creds) { '
         '  $target = ($line -split \\"Target:\\s*\\")[1]; '
         '  if ($target) { cmdkey /delete:$target 2>$null } '
         '}"'),

        # 8. Elimina TODAS las entradas de registro de OneDrive
        ("Limpiando entradas de registro de OneDrive...",
         'reg delete "HKCU\\Software\\Microsoft\\OneDrive" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\Microsoft\\OneDrive" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\OneDrive" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\Policies\\Microsoft\\OneDrive" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "OneDrive" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "OneDriveSetup" /f 2>nul'),

        # 9. Elimina integración de OneDrive del explorador de archivos (CLSID)
        ("Eliminando integración de OneDrive del Explorador de archivos...",
         'reg delete "HKCU\\Software\\Classes\\CLSID\\{018D5C66-4533-4307-9B53-224DE2ED1FE6}" /f 2>nul & '
         'reg delete "HKCU\\Software\\Classes\\WOW6432Node\\CLSID\\{018D5C66-4533-4307-9B53-224DE2ED1FE6}" /f 2>nul & '
         'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\OneDrive" /v DisableFileSyncNGSC /t REG_DWORD /d 1 /f 2>nul'),

        # 10. Elimina entradas del namespace del explorador
        ("Eliminando namespace de OneDrive del explorador...",
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Desktop\\NameSpace\\{018D5C66-4533-4307-9B53-224DE2ED1FE6}" /f 2>nul'),

        # 11. Elimina tareas programadas de OneDrive
        ("Eliminando tareas programadas de OneDrive...",
         'schtasks /delete /tn "\\Microsoft\\Windows\\OneDrive\\*" /f 2>nul & '
         'schtasks /delete /tn "OneDrive*" /f 2>nul'),
    ]

    total = len(pasos)
    for i, (msg, cmd) in enumerate(pasos):
        yield (msg, int((i / total) * 90))
        _run(cmd, timeout=60)
    yield ("✅ OneDrive eliminado completamente. Al reinstalar aparecerá como nuevo, sin cuentas ni sesiones.", 100)


# =============================================================================
#  LIMPIEZA DE AUTODESK / AUTOCAD / REVIT
# =============================================================================

def limpiar_autodesk():
    """
    Limpieza Exclusiva de Instaladores de Autodesk.
    No desinstala software ni borra licencias o registros.
    Elimina C:\\Autodesk y temporales generados durante la instalación.
    """
    pasos = [
        ("Eliminando instalador extraído en C:\\Autodesk...",
         r'rmdir /s /q "C:\Autodesk" 2>nul'),
        ("Eliminando temporales de instalación en %TEMP%...",
         r'powershell -NonInteractive -Command "Get-ChildItem -Path $env:TEMP -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like \'*Autodesk*\' -or $_.Name -like \'*AdODIS*\' -or $_.Name -like \'*Odis*\' } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"'),
        ("Eliminando paquetes temporales de despliegue en ProgramData...",
         r'powershell -NonInteractive -Command "if (Test-Path \'C:\ProgramData\Autodesk\Installer\') { Remove-Item -Path \'C:\ProgramData\Autodesk\Installer\*\' -Recurse -Force -ErrorAction SilentlyContinue }"'),
        ("Eliminando caché de Autodesk Access y AdODIS...",
         r'rmdir /s /q "%LocalAppData%\Autodesk\ODIS" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Autodesk\Autodesk Access" 2>nul'),
    ]

    total = len(pasos)
    for i, (msg, cmd) in enumerate(pasos):
        yield (msg, int((i / total) * 90))
        _run(cmd, timeout=60)
    yield ("✅ Temporales e instaladores de Autodesk limpiados (sin afectar software instalado).", 100)
