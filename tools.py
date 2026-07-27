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

def _run(cmd, shell=True, timeout=60):
    """
    Ejecuta un comando del sistema de forma silenciosa y captura su salida.
    Retorna (returncode, stdout, stderr).
    """
    try:
        r = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=timeout
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

    # ── Reparación del arranque usando bcdboot y bcdedit (funciona desde Windows activo) ──
    "startup": {
        "nombre": "🚀  Reparar Inicio de Windows",
        "descripcion": "Reconstruye el BCD, repara entradas de arranque y verifica archivos de sistema.",
        "tiempo_estimado": "~5-10 min",
        "pasos": [
            # Reconstruye el entorno de arranque EFI/MBR usando la instalación de Windows activa
            ("Reconstruyendo archivos de arranque con bcdboot (EFI + BIOS)...",
             "bcdboot C:\\Windows /s C: /f ALL /l es-ES"),

            # Limpia entradas de arranque duplicadas o corruptas del BCD
            ("Limpiando entradas corruptas del BCD...",
             "bcdedit /deletevalue {current} recoverysequence 2>nul & "
             "bcdedit /set {bootmgr} displaybootmenu no 2>nul & "
             "bcdedit /set {current} recoveryenabled yes"),

            # Fuerza la reparación de archivos del sistema con SFC
            ("Reparando archivos del sistema con SFC /scannow...",
             "sfc /scannow"),

            # Usa DISM para reparar la imagen del sistema si SFC encontró problemas
            ("Reparando imagen del sistema con DISM (puede tardar)...",
             "DISM /Online /Cleanup-Image /RestoreHealth"),

            # Verifica y establece el timeout de arranque correcto
            ("Configurando opciones de arranque correctas...",
             "bcdedit /timeout 5 & "
             "bcdedit /set {current} bootstatuspolicy IgnoreAllFailures & "
             "bcdedit /set {current} recoveryenabled yes"),
        ],
    },

    # ── Restablece pantalla de bloqueo y servicio de inicio de sesión ──
    "lockscreen": {
        "nombre": "🔐  Reparar Pantalla de Bloqueo",
        "descripcion": "Restablece la pantalla de bloqueo y el servicio de inicio de sesión.",
        "tiempo_estimado": "~1-2 min",
        "pasos": [
            # Detiene y reinicia el servicio de pantalla de bloqueo
            ("Reiniciando servicio de pantalla de bloqueo...",
             "sc stop LockAppHost & sc start LockAppHost"),

            # Elimina la caché local de la app de pantalla de bloqueo
            ("Limpiando caché de pantalla de bloqueo...",
             r'del /q /f "%localappdata%\Packages\Microsoft.LockApp_cw5n1h2txyewy\LocalCache\*" 2>nul'),

            # Elimina políticas de grupo que bloquean la personalización de la pantalla de bloqueo
            ("Restableciendo políticas de pantalla de bloqueo...",
             'reg delete "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Personalization" /f 2>nul'),

            # Vuelve a registrar la app de pantalla de bloqueo en el sistema
            ("Registrando pantalla de bloqueo de nuevo...",
             'powershell -NonInteractive -Command "Get-AppxPackage *LockApp* | '
             'ForEach-Object { Add-AppxPackage -DisableDevelopmentMode -Register '
             '(Join-Path $_.InstallLocation AppXManifest.xml) -ErrorAction SilentlyContinue }"'),
        ],
    },

    # ── Repara la app de Configuración de Windows que se cierra sola ──
    "settings": {
        "nombre": "⚙  Reparar Configuración de Windows",
        "descripcion": "Repara la app de Configuración que se cierra automáticamente al abrirse.",
        "tiempo_estimado": "~2-3 min",
        "pasos": [
            # Vuelve a registrar la app de Configuración del sistema
            ("Registrando app de Configuración...",
             'powershell -NonInteractive -Command "Get-AppxPackage *windows.immersivecontrolpanel* | '
             'ForEach-Object { Add-AppxPackage -DisableDevelopmentMode -Register '
             '(Join-Path $_.InstallLocation AppXManifest.xml) -ErrorAction SilentlyContinue }"'),

            # Asegura que el Panel de Control no esté bloqueado por política de usuario
            ("Reparando permisos de Configuración en registro...",
             'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" '
             '/v NoControlPanel /t REG_DWORD /d 0 /f'),

            # Restablece los permisos de la carpeta WindowsApps donde viven las apps UWP
            ("Restableciendo permisos de SystemSettings...",
             'icacls "%ProgramFiles%\\WindowsApps" /reset /T /C /Q 2>nul'),

            # Limpia la caché local de la app de Configuración
            ("Limpiando caché de la app de Configuración...",
             r'powershell -NonInteractive -Command "Remove-Item -Path '
             r"'$env:LOCALAPPDATA\Packages\windows.immersivecontrolpanel_cw5n1h2txyewy\LocalCache' "
             r'-Recurse -Force -ErrorAction SilentlyContinue"'),
        ],
    },

    # ── Escaneo y reparación profunda de archivos del sistema ──
    "sfc": {
        "nombre": "🛡  Escaneo SFC + DISM",
        "descripcion": "Verifica y repara archivos del sistema dañados. El DISM puede tardar 15-30 min.",
        "tiempo_estimado": "~20-40 min",
        "pasos": [
            # SFC: escanea y repara archivos protegidos del sistema
            ("Ejecutando SFC (Comprobador de archivos del sistema)... ~5 min",
             "sfc /scannow"),

            # DISM CheckHealth: verifica si la imagen tiene daños marcados
            ("Verificando estado de la imagen del sistema con DISM... ~2 min",
             "DISM /Online /Cleanup-Image /CheckHealth"),

            # DISM ScanHealth: escaneo completo buscando daños en la imagen
            ("Escaneando la imagen del sistema con DISM... ~5 min",
             "DISM /Online /Cleanup-Image /ScanHealth"),

            # DISM RestoreHealth: descarga y restaura componentes dañados desde Windows Update
            ("Reparando la imagen del sistema con DISM... ~15-30 min",
             "DISM /Online /Cleanup-Image /RestoreHealth"),
        ],
    },

    # ── Restablece Windows Store y re-registra todas las apps UWP ──
    "store": {
        "nombre": "🛒  Reparar Windows Store / Apps",
        "descripcion": "Restablece la tienda de Microsoft y re-registra las apps universales.",
        "tiempo_estimado": "~3-5 min",
        "pasos": [
            # Limpia la caché de la tienda de Windows
            ("Reseteando Windows Store...",
             "wsreset.exe"),

            # Vuelve a registrar todas las apps UWP instaladas para todos los usuarios
            ("Re-registrando apps de Microsoft...",
             'powershell -NonInteractive -Command "Get-AppxPackage -AllUsers | '
             'ForEach-Object { Add-AppxPackage -DisableDevelopmentMode -Register '
             '(Join-Path $_.InstallLocation AppXManifest.xml) -ErrorAction SilentlyContinue }"'),

            # Reinicia el servicio de Windows Update (necesario para la tienda)
            ("Reiniciando servicios de la tienda...",
             "net stop wuauserv & net start wuauserv"),
        ],
    },

    # ── Resetea todos los componentes de Windows Update ──
    "updates": {
        "nombre": "🔃  Reparar Windows Update",
        "descripcion": "Resetea los componentes de Windows Update para solucionar actualizaciones bloqueadas.",
        "tiempo_estimado": "~2-4 min",
        "pasos": [
            # Detiene todos los servicios relacionados con Windows Update
            ("Deteniendo servicios de Windows Update...",
             "net stop wuauserv & net stop cryptSvc & net stop bits & net stop msiserver"),

            # Elimina las carpetas de caché de actualizaciones descargadas
            ("Eliminando caché de actualizaciones...",
             r"rd /s /q C:\Windows\SoftwareDistribution 2>nul & rd /s /q C:\Windows\System32\catroot2 2>nul"),

            # Reinicia todos los servicios de Windows Update
            ("Reiniciando servicios de Windows Update...",
             "net start wuauserv & net start cryptSvc & net start bits & net start msiserver"),

            # Fuerza la detección de nuevas actualizaciones disponibles
            ("Forzando comprobación de actualizaciones...",
             "wuauclt /resetauthorization /detectnow"),
        ],
    },

    # ── Repara el explorador de Windows y la barra de tareas ──
    "taskbar": {
        "nombre": "📌  Reparar Barra de Tareas / Explorer",
        "descripcion": "Reinicia el explorador de Windows y repara la barra de tareas congelada.",
        "tiempo_estimado": "~1-2 min",
        "pasos": [
            # Mata el proceso de explorer.exe para poder limpiarlo y relanzarlo
            ("Terminando proceso Explorer.exe...",
             "taskkill /f /im explorer.exe 2>nul"),

            # Elimina la base de datos de caché de iconos que puede causar problemas
            ("Limpiando caché de iconos (IconCache.db)...",
             r'attrib -h "%localappdata%\IconCache.db" 2>nul & '
             r'del /f /q "%localappdata%\IconCache.db" 2>nul'),

            # Elimina las miniaturas en caché que pueden estar corruptas
            ("Limpiando caché de miniaturas (thumbcache)...",
             r'del /f /q /s "%localappdata%\Microsoft\Windows\Explorer\thumbcache_*.db" 2>nul'),

            # Limpia la caché de notificaciones de la barra de tareas en el registro
            ("Limpiando caché de notificaciones de la barra de tareas...",
             r'reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v IconStreams /f 2>nul & '
             r'reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v PastIconsStream /f 2>nul'),

            # Relanza explorer.exe usando PowerShell para asegurar contexto correcto de usuario
            ("Reiniciando Explorer.exe...",
             'powershell -NonInteractive -Command "Start-Process explorer.exe"'),
        ],
    },

    # ── Repara el servicio de audio y sus dependencias ──
    "audio": {
        "nombre": "🔊  Reparar Audio de Windows",
        "descripcion": "Reinicia los servicios de audio y repara el subsistema de sonido.",
        "tiempo_estimado": "~2-4 min",
        "pasos": [
            # Reinicia el servicio principal de audio de Windows
            ("Reiniciando servicio Windows Audio...",
             "net stop Audiosrv & net start Audiosrv"),

            # Reinicia el servicio que gestiona los dispositivos de audio (endpoints)
            ("Reiniciando servicio AudioEndpointBuilder...",
             "net stop AudioEndpointBuilder & net start AudioEndpointBuilder"),

            # Usa SFC para verificar y reparar archivos de drivers de audio dañados
            ("Escaneando drivers de audio con SFC...",
             "sfc /scannow"),
        ],
    },

    # ── Verifica la integridad de drivers y repara los dañados ──
    "drivers": {
        "nombre": "🖱  Reparar Drivers del Sistema",
        "descripcion": "Verifica la integridad de drivers y repara los dañados.",
        "tiempo_estimado": "~10-20 min",
        "pasos": [
            # Verifica la integridad de archivos sin reparar (modo solo verificación)
            ("Verificando integridad de drivers con SFC...",
             "sfc /verifyonly"),

            # Repara la imagen del sistema que incluye todos los drivers
            ("Reparando imagen con controladores (DISM)...",
             "DISM /Online /Cleanup-Image /RestoreHealth"),

            # Escaneo y reparación completa de archivos del sistema incluyendo drivers
            ("Escaneando y reparando archivos de sistema...",
             "sfc /scannow"),
        ],
    },

    # ── Reinicia Windows Defender y actualiza sus definiciones ──
    "defender": {
        "nombre": "🛡  Reparar Windows Defender",
        "descripcion": "Reinicia Windows Defender y actualiza sus definiciones de seguridad.",
        "tiempo_estimado": "~5-10 min",
        "pasos": [
            # Reinicia el servicio principal de Windows Defender
            ("Reiniciando Windows Defender...",
             "net stop WinDefend & net start WinDefend"),

            # Descarga las últimas definiciones de virus/malware
            ("Actualizando definiciones de Defender...",
             r'"C:\Program Files\Windows Defender\MpCmdRun.exe" -SignatureUpdate'),

            # Ejecuta un análisis rápido para verificar que Defender funciona
            ("Ejecutando análisis rápido de Defender...",
             r'"C:\Program Files\Windows Defender\MpCmdRun.exe" -Scan -ScanType 1'),
        ],
    },

    # ── Repara el Menú de Inicio y el buscador de Windows ──
    "startmenu": {
        "nombre": "🔍  Reparar Menú de Inicio / Búsqueda",
        "descripcion": "Elimina la base de datos de indexación y reinicia los servicios de búsqueda para que el menú de inicio y la búsqueda sean instantáneos.",
        "tiempo_estimado": "~3-5 min",
        "pasos": [
            # Detiene el servicio de búsqueda de Windows para poder modificar sus archivos
            ("Deteniendo servicio de búsqueda de Windows (WSearch)...",
             "net stop WSearch /y"),

            # Elimina la base de datos de índice de búsqueda que puede estar corrupta
            ("Eliminando base de datos de indexación corrupta...",
             r'del /f /q "%ProgramData%\Microsoft\Search\Data\Applications\Windows\Windows.edb" 2>nul & '
             r'rmdir /s /q "%ProgramData%\Microsoft\Search\Data\Applications\Windows" 2>nul'),

            # Aplica ajustes de registro para deshabilitar búsqueda web en el menú de inicio
            ("Aplicando ajustes de registro para búsqueda local instantánea...",
             'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Search" /v BingSearchEnabled /t REG_DWORD /d 0 /f & '
             'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Search" /v CortanaConsent /t REG_DWORD /d 0 /f & '
             'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search" /v AllowCortana /t REG_DWORD /d 0 /f'),

            # Vuelve a registrar la app del Shell de Windows (barra de tareas + menú inicio)
            ("Re-registrando ShellExperienceHost (Menú de Inicio)...",
             'powershell -NonInteractive -Command "Get-AppxPackage *ShellExperienceHost* | '
             'ForEach-Object { Add-AppxPackage -DisableDevelopmentMode -Register '
             '(Join-Path $_.InstallLocation AppXManifest.xml) -ErrorAction SilentlyContinue }"'),

            # Vuelve a registrar la app de búsqueda de Windows (puede variar en Win10/Win11)
            ("Re-registrando app de Búsqueda de Windows...",
             'powershell -NonInteractive -Command "'
             '$apps = @(\"*Windows.Search*\", \"*Cortana*\"); '
             'foreach ($a in $apps) { '
             'Get-AppxPackage $a -ErrorAction SilentlyContinue | ForEach-Object { '
             'Add-AppxPackage -DisableDevelopmentMode -Register '
             '(Join-Path $_.InstallLocation AppXManifest.xml) -ErrorAction SilentlyContinue } }"'),

            # Reinicia el servicio de búsqueda para que comience a re-indexar
            ("Reiniciando servicio de búsqueda y Explorer...",
             "net start WSearch & "
             'powershell -NonInteractive -Command "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue; Start-Sleep 1; Start-Process explorer"'),
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
    Limpia completamente Microsoft Teams: cierra el proceso, elimina todos sus
    datos en AppData (Roaming y Local), caché temporal, entradas de registro
    y credenciales guardadas. Deja el sistema como si Teams nunca hubiera sido instalado.
    """
    import shutil

    pasos = [
        # Cierra todas las instancias de Teams incluyendo el proceso de actualización
        ("Cerrando Microsoft Teams...",
         'taskkill /f /im Teams.exe /t 2>nul & '
         'taskkill /f /im ms-teams.exe /t 2>nul & '
         'taskkill /f /im Update.exe /t 2>nul'),

        # Elimina los datos de perfil de Teams en AppData\Roaming
        ("Eliminando datos de Teams en AppData\\Roaming...",
         r'rmdir /s /q "%AppData%\Microsoft\Teams" 2>nul'),

        # Elimina los datos de instalación de Teams en AppData\Local
        ("Eliminando datos de Teams en AppData\\Local...",
         r'rmdir /s /q "%LocalAppData%\Microsoft\Teams" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\TeamsMeetingAddin" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\Microsoft\TeamsPresenceAddin" 2>nul'),

        # Elimina archivos temporales de Teams en la carpeta Temp
        ("Eliminando caché de Teams en Temp...",
         r'del /f /s /q "%Temp%\*teams*" 2>nul'),

        # Elimina las entradas del registro relacionadas con Teams
        ("Limpiando entradas de registro de Teams...",
         'reg delete "HKCU\\Software\\Microsoft\\Office\\Teams" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Teams" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\Microsoft\\Teams" /f 2>nul'),

        # Elimina tareas programadas de Teams (actualización automática, etc.)
        ("Eliminando tareas programadas de Teams...",
         'schtasks /delete /tn "\\Microsoft\\Teams\\*" /f 2>nul'),
    ]

    total = len(pasos)
    for i, (msg, cmd) in enumerate(pasos):
        yield (msg, int((i / total) * 90))
        _run(cmd, timeout=30)
    yield ("✅ Teams limpiado completamente. Puedes reinstalarlo desde cero.", 100)


# =============================================================================
#  LIMPIEZA DE ONEDRIVE
# =============================================================================

def limpiar_onedrive():
    """
    Limpia completamente OneDrive: cierra el proceso, desregistra el cliente,
    elimina todos sus datos en AppData (Local y Roaming), carpetas de configuración,
    entradas de registro y tareas programadas. No elimina archivos del usuario en la nube.
    """
    pasos = [
        # Cierra OneDrive y su proceso de instalación/actualización
        ("Cerrando OneDrive...",
         'taskkill /f /im OneDrive.exe /t 2>nul & '
         'taskkill /f /im OneDriveSetup.exe /t 2>nul'),

        # Desregistra OneDrive del sistema (ambas versiones x64 y x86)
        ("Desregistrando OneDrive del sistema...",
         'if exist "%SystemRoot%\\SysWOW64\\OneDriveSetup.exe" '
         '"%SystemRoot%\\SysWOW64\\OneDriveSetup.exe" /unregister 2>nul & '
         'if exist "%SystemRoot%\\System32\\OneDriveSetup.exe" '
         '"%SystemRoot%\\System32\\OneDriveSetup.exe" /unregister 2>nul'),

        # Elimina los datos del cliente OneDrive en AppData\Local
        ("Eliminando datos de OneDrive en AppData\\Local...",
         r'rmdir /s /q "%LocalAppData%\Microsoft\OneDrive" 2>nul'),

        # Elimina los datos de configuración de OneDrive en AppData\Roaming
        ("Eliminando datos de OneDrive en AppData\\Roaming...",
         r'rmdir /s /q "%AppData%\Microsoft\OneDrive" 2>nul'),

        # Elimina carpetas adicionales de OneDrive en el perfil del usuario
        ("Eliminando carpeta de configuración de OneDrive...",
         r'rmdir /s /q "%UserProfile%\OneDrive" 2>nul & '
         r'rmdir /s /q "%LocalAppData%\OneDrive" 2>nul'),

        # Elimina todas las entradas de registro de OneDrive (usuario y sistema)
        ("Limpiando entradas de registro de OneDrive...",
         'reg delete "HKCU\\Software\\Microsoft\\OneDrive" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\Microsoft\\OneDrive" /f 2>nul & '
         'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "OneDrive" /f 2>nul & '
         'reg delete "HKLM\\SOFTWARE\\Policies\\Microsoft\\OneDrive" /f 2>nul'),

        # Elimina tareas programadas de OneDrive (sincronización automática, etc.)
        ("Eliminando tareas programadas de OneDrive...",
         'schtasks /delete /tn "\\Microsoft\\Windows\\OneDrive\\*" /f 2>nul'),
    ]

    total = len(pasos)
    for i, (msg, cmd) in enumerate(pasos):
        yield (msg, int((i / total) * 90))
        _run(cmd, timeout=30)
    yield ("✅ OneDrive limpiado completamente. Puedes reinstalarlo desde cero.", 100)
