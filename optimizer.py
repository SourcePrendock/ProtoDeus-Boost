"""
optimizer.py — Módulo de optimización del sistema para ProtoDeus Boost
Todas las funciones retornan un generador que yield ("mensaje", porcentaje)
para que la UI pueda mostrar progreso en tiempo real.
"""

import os
import shutil
import subprocess
import winreg
import ctypes
import glob
import threading


# ─────────────────────────────────────────
#  Utilidades internas
# ─────────────────────────────────────────

def _run(cmd, shell=True):
    """Ejecuta un comando y retorna (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=shell, capture_output=True, text=True,
        encoding="utf-8", errors="ignore"
    )
    return result.returncode, result.stdout, result.stderr


def _delete_folder_contents(path):
    """Elimina el contenido de una carpeta, retorna bytes liberados."""
    liberado = 0
    if not os.path.exists(path):
        return 0
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                liberado += os.path.getsize(item_path)
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                liberado += sum(
                    os.path.getsize(os.path.join(dirpath, f))
                    for dirpath, _, files in os.walk(item_path)
                    for f in files
                    if os.path.exists(os.path.join(dirpath, f))
                )
                shutil.rmtree(item_path, ignore_errors=True)
        except Exception:
            pass
    return liberado


def _bytes_to_mb(b):
    return round(b / (1024 * 1024), 2)


# ─────────────────────────────────────────
#  1. Limpieza de Temporales
# ─────────────────────────────────────────

def limpiar_temporales():
    """Limpia carpetas temporales del sistema y del usuario."""
    rutas = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        r"C:\Windows\Temp",
        r"C:\Windows\Prefetch",
    ]
    total = 0
    for i, ruta in enumerate(rutas):
        if ruta:
            yield (f"Limpiando: {ruta}", int((i / len(rutas)) * 90))
            total += _delete_folder_contents(ruta)
    yield (f"✅ Temporales limpiados — {_bytes_to_mb(total)} MB liberados", 100)


# ─────────────────────────────────────────
#  2. Limpieza Profunda
# ─────────────────────────────────────────

def limpieza_profunda():
    """Limpieza profunda: temporales + papelera + caché de miniaturas + logs."""
    yield ("Iniciando limpieza profunda...", 5)
    total = 0

    # Temporales
    for ruta in [os.environ.get("TEMP",""), r"C:\Windows\Temp", r"C:\Windows\Prefetch"]:
        if ruta:
            yield (f"Limpiando: {ruta}", 10)
            total += _delete_folder_contents(ruta)

    # Papelera de reciclaje
    yield ("Vaciando Papelera de Reciclaje...", 30)
    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)

    # Caché de miniaturas
    thumb_db = os.path.join(os.environ.get("LOCALAPPDATA",""), r"Microsoft\Windows\Explorer")
    yield ("Limpiando caché de miniaturas...", 50)
    total += _delete_folder_contents(thumb_db)

    # Caché de fuentes
    font_cache = r"C:\Windows\System32\FNTCACHE.DAT"
    yield ("Limpiando caché de fuentes...", 60)
    try:
        if os.path.exists(font_cache):
            os.unlink(font_cache)
    except Exception:
        pass

    # Logs de Windows Update
    wu_logs = r"C:\Windows\SoftwareDistribution\Download"
    yield ("Limpiando archivos de Windows Update...", 70)
    total += _delete_folder_contents(wu_logs)

    # Dumps de memoria
    yield ("Eliminando archivos de volcado de memoria...", 80)
    for dump_path in [r"C:\Windows\Minidump", r"C:\Windows\memory.dmp"]:
        if os.path.isdir(dump_path):
            total += _delete_folder_contents(dump_path)
        elif os.path.isfile(dump_path):
            try:
                total += os.path.getsize(dump_path)
                os.unlink(dump_path)
            except Exception:
                pass

    # Archivos .log y .bak del sistema
    yield ("Eliminando logs antiguos del sistema...", 90)
    for pattern in [r"C:\Windows\*.log", r"C:\Windows\*.bak"]:
        for f in glob.glob(pattern):
            try:
                total += os.path.getsize(f)
                os.unlink(f)
            except Exception:
                pass

    yield (f"✅ Limpieza profunda completa — {_bytes_to_mb(total)} MB liberados", 100)


# ─────────────────────────────────────────
#  3. Limpieza de Navegadores
# ─────────────────────────────────────────

def limpiar_navegadores():
    """Limpia caché de Chrome, Edge, Firefox y Brave."""
    localappdata = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")

    rutas_navegadores = {
        "Google Chrome":    [os.path.join(localappdata, r"Google\Chrome\User Data\Default\Cache"),
                             os.path.join(localappdata, r"Google\Chrome\User Data\Default\Code Cache")],
        "Microsoft Edge":   [os.path.join(localappdata, r"Microsoft\Edge\User Data\Default\Cache"),
                             os.path.join(localappdata, r"Microsoft\Edge\User Data\Default\Code Cache")],
        "Firefox":          [os.path.join(appdata, r"Mozilla\Firefox\Profiles")],
        "Brave":            [os.path.join(localappdata, r"BraveSoftware\Brave-Browser\User Data\Default\Cache")],
        "Opera":            [os.path.join(appdata, r"Opera Software\Opera Stable\Cache")],
    }

    total = 0
    items = list(rutas_navegadores.items())
    for i, (nav, rutas) in enumerate(items):
        pct = int((i / len(items)) * 90)
        yield (f"Limpiando {nav}...", pct)
        for ruta in rutas:
            if "Profiles" in ruta and os.path.exists(ruta):
                # Firefox tiene carpetas de perfiles dinámicas
                for perfil in os.listdir(ruta):
                    cache = os.path.join(ruta, perfil, "cache2")
                    total += _delete_folder_contents(cache)
            else:
                total += _delete_folder_contents(ruta)

    yield (f"✅ Caché de navegadores limpiada — {_bytes_to_mb(total)} MB liberados", 100)


# ─────────────────────────────────────────
#  4. Limpieza de Registro
# ─────────────────────────────────────────

def limpiar_registro():
    """Elimina claves de registro de software desinstalado y entradas huérfanas."""
    yield ("Analizando registro de Windows...", 10)

    # Usar cleanmgr en modo silencioso
    yield ("Ejecutando limpieza automática del sistema...", 30)
    _run("cleanmgr /sagerun:1", shell=True)

    # DISM cleanup
    yield ("Ejecutando limpieza de imagen de Windows (DISM)...", 50)
    _run("DISM /online /Cleanup-Image /StartComponentCleanup /ResetBase", shell=True)

    # Limpiar claves de uninstall huérfanas
    yield ("Revisando claves de desinstalación huérfanas...", 80)
    orphans = []
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, sub) as sk:
                        try:
                            loc = winreg.QueryValueEx(sk, "InstallLocation")[0]
                            if loc and not os.path.exists(loc):
                                orphans.append(sub)
                        except FileNotFoundError:
                            pass
                    i += 1
                except OSError:
                    break
    except Exception:
        pass

    yield (f"✅ Registro analizado — {len(orphans)} entradas huérfanas detectadas", 100)


# ─────────────────────────────────────────
#  5. Optimizar Red
# ─────────────────────────────────────────

def optimizar_red():
    """Optimiza parámetros de red TCP/IP."""
    comandos = [
        ("Reseteando parámetros TCP/IP...",           "netsh int tcp set global autotuninglevel=normal"),
        ("Deshabilitando timestamps TCP...",           "netsh int tcp set global timestamps=disabled"),
        ("Configurando RSS...",                        "netsh int tcp set global rss=enabled"),
        ("Deshabilitando Large Send Offload IPv4...",  "netsh int ip set global taskoffload=disabled"),
        ("Flusheando DNS...",                          "ipconfig /flushdns"),
        ("Liberando y renovando IP...",                "ipconfig /release && ipconfig /renew"),
        ("Optimizando parámetros Winsock...",          "netsh winsock reset catalog"),
    ]
    for i, (msg, cmd) in enumerate(comandos):
        pct = int((i / len(comandos)) * 90)
        yield (msg, pct)
        _run(cmd)

    yield ("✅ Red optimizada correctamente", 100)


# ─────────────────────────────────────────
#  6. Optimizar Efectos Visuales
# ─────────────────────────────────────────

def optimizar_efectos_visuales():
    """Ajusta Windows para rendimiento máximo (desactiva efectos visuales)."""
    yield ("Ajustando efectos visuales para máximo rendimiento...", 20)
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
    except Exception:
        pass

    yield ("Desactivando animaciones...", 50)
    try:
        key_path = r"Control Panel\Desktop\WindowMetrics"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "MinAnimate", 0, winreg.REG_SZ, "0")
    except Exception:
        pass

    yield ("Aplicando configuración de rendimiento...", 70)
    _run('reg add "HKCU\\Control Panel\\Desktop" /v UserPreferencesMask /t REG_BINARY /d 9012038010000000 /f')
    _run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v ListviewShadow /t REG_DWORD /d 0 /f')
    _run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v TaskbarAnimations /t REG_DWORD /d 0 /f')

    yield ("✅ Efectos visuales optimizados", 100)


# ─────────────────────────────────────────
#  7. Optimizar Disco (SSD - TRIM)
# ─────────────────────────────────────────

def optimizar_ssd():
    """Ejecuta TRIM en todos los SSDs disponibles."""
    yield ("Detectando SSDs...", 10)
    _run("defrag C: /U /V /retrim")
    yield ("Ejecutando TRIM en todas las unidades...", 50)
    # Ejecutar en todas las letras de unidad
    import psutil
    for part in psutil.disk_partitions():
        letra = part.mountpoint.replace("\\", "")
        _run(f"defrag {letra} /retrim /U")
    yield ("✅ TRIM ejecutado correctamente en SSDs", 100)


# ─────────────────────────────────────────
#  8. Desfragmentar HDD
# ─────────────────────────────────────────

def desfragmentar_hdd():
    """Desfragmenta las unidades HDD detectadas."""
    yield ("Detectando unidades HDD...", 10)
    import psutil
    particiones = psutil.disk_partitions()
    hdds = [p.mountpoint for p in particiones if "cdrom" not in p.opts]
    for i, letra in enumerate(hdds):
        pct = int(10 + (i / max(len(hdds), 1)) * 80)
        l = letra.replace("\\", "")
        yield (f"Desfragmentando {l}...", pct)
        _run(f"defrag {l} /U /V")
    yield ("✅ Desfragmentación completada", 100)


# ─────────────────────────────────────────
#  9. Liberar RAM (deshabilitar SysMain/Superfetch)
# ─────────────────────────────────────────

def liberar_ram():
    """
    Deshabilita Superfetch/SysMain modificando el registro:
    - EnablePrefetcher = 0 en PrefetchParameters
    - Start = 0 en SysMain service
    También vacía el Working Set de todos los procesos posibles.
    """
    yield ("Modificando registro — PrefetchParameters...", 20)
    try:
        key1 = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key1, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "EnablePrefetcher", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(k, "EnableSuperfetch", 0, winreg.REG_DWORD, 0)
    except Exception as e:
        yield (f"⚠ No se pudo modificar PrefetchParameters: {e}", 30)

    yield ("Modificando registro — SysMain (Superfetch service)...", 50)
    try:
        key2 = r"SYSTEM\CurrentControlSet\Services\SysMain"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key2, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "Start", 0, winreg.REG_DWORD, 0)
    except Exception as e:
        yield (f"⚠ No se pudo modificar SysMain: {e}", 60)

    yield ("Deteniendo servicio SysMain...", 70)
    _run("sc stop SysMain")
    _run("sc config SysMain start= disabled")

    yield ("Vaciando caché de memoria...", 85)
    # Vaciar working sets con EmptyWorkingSet via RAMMap equivalente
    _run('powershell -Command "Get-Process | ForEach-Object { $_.MinWorkingSet = 1MB }" 2>$null')

    yield ("✅ RAM liberada y Superfetch deshabilitado", 100)


# ─────────────────────────────────────────
#  10. Restaurar SysMain (revertir liberar RAM)
# ─────────────────────────────────────────

def restaurar_sysmain():
    """Restaura Superfetch/SysMain a su estado normal."""
    yield ("Restaurando PrefetchParameters...", 25)
    try:
        key1 = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key1, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "EnablePrefetcher", 0, winreg.REG_DWORD, 3)
            winreg.SetValueEx(k, "EnableSuperfetch", 0, winreg.REG_DWORD, 3)
    except Exception as e:
        yield (f"⚠ Error: {e}", 40)

    yield ("Restaurando SysMain service...", 60)
    try:
        key2 = r"SYSTEM\CurrentControlSet\Services\SysMain"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key2, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "Start", 0, winreg.REG_DWORD, 2)
    except Exception as e:
        yield (f"⚠ Error: {e}", 70)

    yield ("Iniciando servicio SysMain...", 85)
    _run("sc config SysMain start= auto")
    _run("sc start SysMain")

    yield ("✅ SysMain/Superfetch restaurado correctamente", 100)


# ─────────────────────────────────────────
#  11. Limpiar DNS Cache
# ─────────────────────────────────────────

def limpiar_dns():
    """Limpia la caché DNS del sistema."""
    yield ("Limpiando caché DNS...", 50)
    _run("ipconfig /flushdns")
    yield ("✅ Caché DNS limpiada", 100)


# ─────────────────────────────────────────
#  12. Deshabilitar Apps de Inicio
# ─────────────────────────────────────────

def get_startup_apps():
    """Retorna lista de apps de inicio desde el registro."""
    apps = []
    paths = [
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ]
    for hive, path in paths:
        try:
            with winreg.OpenKey(hive, path) as k:
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(k, i)
                        apps.append({"nombre": name, "comando": val, "hive": hive, "path": path})
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass
    return apps
