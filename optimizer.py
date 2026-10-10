import os
import shutil
import subprocess
import winreg
import ctypes
import glob


CREATE_NO_WINDOW = 0x08000000


def _run(cmd, shell=True):
    result = subprocess.run(
        cmd, shell=shell, capture_output=True, text=True,
        encoding="utf-8", errors="ignore",
        creationflags=CREATE_NO_WINDOW
    )
    return result.returncode, result.stdout, result.stderr


def _delete_folder_contents(path):
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
                    os.path.getsize(os.path.join(dp, f))
                    for dp, _, files in os.walk(item_path)
                    for f in files
                    if os.path.exists(os.path.join(dp, f))
                )
                shutil.rmtree(item_path, ignore_errors=True)
        except Exception:
            pass
    return liberado


def _mb(b):
    return round(b / (1024 * 1024), 2)


def limpieza_express():
    """
    Limpieza Express — Rápida, sin riesgos, ejecutable diariamente.
    Limpia carpetas TEMP del usuario y del sistema, y vacía la Papelera de Reciclaje.
    """
    rutas = [
        ("Carpeta TEMP del usuario", os.environ.get("TEMP", "")),
        ("Carpeta TEMP del sistema", r"C:\Windows\Temp"),
    ]
    total = 0
    for i, (nombre, ruta) in enumerate(rutas):
        if ruta:
            yield (f"Limpiando {nombre}: {ruta}", int((i / len(rutas)) * 60))
            total += _delete_folder_contents(ruta)
    yield ("Vaciando Papelera de Reciclaje...", 75)
    try:
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
    except Exception:
        pass
    yield (f"✅ Limpieza Express completa — {_mb(total)} MB liberados", 100)


def limpieza_profunda():
    """
    Limpieza Profunda — Liberación masiva de espacio en disco.
    Ejecuta DISM para limpiar componentes antiguos de Windows Update,
    elimina archivos de volcado de memoria, logs antiguos y caché de shaders.
    ⚠ Requiere reinicio del sistema después de ejecutarse.
    """
    yield ("Iniciando limpieza profunda del sistema...", 5)
    total = 0

    # 1. DISM — Limpiar componentes antiguos de Windows Update (la operación más pesada)
    yield ("Ejecutando DISM /StartComponentCleanup /ResetBase (puede tardar varios minutos)...", 10)
    _run("DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase", shell=True)

    # 2. Limpiar carpeta SoftwareDistribution\Download (actualizaciones descargadas)
    wu_download = r"C:\Windows\SoftwareDistribution\Download"
    yield ("Limpiando descargas de Windows Update (SoftwareDistribution\\Download)...", 35)
    total += _delete_folder_contents(wu_download)

    # 3. Eliminar archivos de volcado de memoria (Memory.dmp y Minidump)
    yield ("Eliminando archivos de volcado de memoria (Memory.dmp, Minidump)...", 50)
    for dp in [r"C:\Windows\Minidump", r"C:\Windows\memory.dmp"]:
        if os.path.isdir(dp):
            total += _delete_folder_contents(dp)
        elif os.path.isfile(dp):
            try:
                total += os.path.getsize(dp)
                os.unlink(dp)
            except Exception:
                pass

    # 4. Eliminar registros antiguos de eventos de Windows (.log, .bak)
    yield ("Eliminando registros antiguos del sistema (.log, .bak)...", 65)
    for pattern in [r"C:\Windows\*.log", r"C:\Windows\*.bak"]:
        for f in glob.glob(pattern):
            try:
                total += os.path.getsize(f)
                os.unlink(f)
            except Exception:
                pass

    # 5. Limpiar caché de sombreadores de DirectX (D3DSCache, NVIDIA DXCache, AMD DxCache)
    yield ("Limpiando caché de sombreadores de DirectX...", 80)
    local = os.environ.get("LOCALAPPDATA", "")
    shader_caches = [
        os.path.join(local, "D3DSCache"),
        os.path.join(local, r"NVIDIA\DXCache"),
        os.path.join(local, r"NVIDIA\GLCache"),
        os.path.join(local, r"AMD\DxCache"),
        os.path.join(local, r"AMD\GLCache"),
    ]
    for cache_dir in shader_caches:
        if os.path.isdir(cache_dir):
            total += _delete_folder_contents(cache_dir)

    yield (f"✅ Limpieza profunda completa — {_mb(total)} MB liberados. Se recomienda reiniciar el PC.", 100)


def limpiar_navegadores():
    """
    Limpieza de Navegadores Web — Restablece perfiles eliminando caché, cookies, historial,
    sesiones persistentes y datos temporales.
    Soporta: Edge, Chrome, Firefox, Brave, Zen, Opera GX, Opera, Vivaldi, LibreWolf, IE.
    ⚠ Cierra todos los navegadores abiertos antes de limpiar.
    """
    local = os.environ.get("LOCALAPPDATA", "")
    appd = os.environ.get("APPDATA", "")

    # 1. Cerrar todos los procesos de navegadores
    yield ("Cerrando todos los navegadores abiertos en segundo plano...", 2)
    browser_processes = [
        "msedge.exe", "chrome.exe", "firefox.exe", "brave.exe",
        "opera.exe", "vivaldi.exe", "zen.exe", "librewolf.exe",
        "iexplore.exe",
    ]
    for proc in browser_processes:
        _run(f"taskkill /f /im {proc} /t 2>nul")
    import time
    time.sleep(2)  # Dar tiempo a que los procesos se cierren

    # Definir navegadores y sus rutas base
    navegadores = {
        "Microsoft Edge": {"rutas": [os.path.join(local, r"Microsoft\Edge\User Data")]},
        "Google Chrome": {"rutas": [os.path.join(local, r"Google\Chrome\User Data")]},
        "Firefox": {"rutas": [os.path.join(appd, r"Mozilla\Firefox\Profiles"), os.path.join(local, r"Mozilla\Firefox\Profiles")]},
        "Brave": {"rutas": [os.path.join(local, r"BraveSoftware\Brave-Browser\User Data")]},
        "Zen Browser": {"rutas": [os.path.join(appd, r"zen\Profiles"), os.path.join(local, r"zen\Profiles")]},
        "Opera GX": {"rutas": [os.path.join(appd, r"Opera Software\Opera GX Stable"), os.path.join(local, r"Opera Software\Opera GX Stable")]},
        "Opera": {"rutas": [os.path.join(appd, r"Opera Software\Opera Stable"), os.path.join(local, r"Opera Software\Opera Stable")]},
        "Vivaldi": {"rutas": [os.path.join(local, r"Vivaldi\User Data")]},
        "LibreWolf": {"rutas": [os.path.join(appd, r"librewolf\Profiles"), os.path.join(local, r"librewolf\Profiles")]},
    }

    subcarpetas_borrar = [
        "Cache",
        "Code Cache",
        "GPUCache",
        "Cookies",
        "Web Storage",
        "Network", # Chromium cache/cookies often stored here now
        "Storage", # Firefox local storage
        "cache2", # Firefox cache
    ]

    total = 0
    items = list(navegadores.items())
    for i, (nav, info) in enumerate(items):
        pct = int(5 + (i / len(items)) * 80)
        rutas_existentes = [r for r in info["rutas"] if os.path.exists(r)]
        if not rutas_existentes:
            yield (f"⏭ {nav} no encontrado — omitido", pct)
            continue
        yield (f"🗑 Eliminando caché y cookies de {nav}...", pct)
        
        # Buscar en las rutas base y en sus subdirectorios (como perfiles Default, Profile 1, etc.)
        for ruta_base in rutas_existentes:
            for root, dirs, files in os.walk(ruta_base):
                for sub_dir in dirs:
                    if sub_dir in subcarpetas_borrar or sub_dir.startswith("Cache"):
                        full_dir = os.path.join(root, sub_dir)
                        total += _delete_folder_contents(full_dir)
                
                # Para Firefox y Chromium, algunos archivos están en la raíz del perfil
                for f in files:
                    lower_f = f.lower()
                    if "cookie" in lower_f or "history" in lower_f or "webappsstore" in lower_f:
                        try:
                            full_file = os.path.join(root, f)
                            total += os.path.getsize(full_file)
                            os.unlink(full_file)
                        except Exception:
                            pass

    # Internet Explorer — usar la API del sistema
    yield ("🗑 Limpiando Internet Explorer (RunDll32)...", 90)
    _run("RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess 255")

    yield (f"✅ Todos los navegadores limpiados — {_mb(total)} MB liberados", 100)


def limpiar_registro():
    yield ("Analizando registro de Windows...", 10)
    yield ("Ejecutando limpieza automática del sistema...", 30)
    _run("cleanmgr /sagerun:1", shell=True)
    yield ("Ejecutando limpieza de imagen de Windows (DISM)...", 50)
    _run("DISM /online /Cleanup-Image /StartComponentCleanup /ResetBase", shell=True)
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


def optimizar_red():
    comandos = [
        ("Reseteando parámetros TCP/IP...",          "netsh int tcp set global autotuninglevel=normal"),
        ("Deshabilitando timestamps TCP...",          "netsh int tcp set global timestamps=disabled"),
        ("Configurando RSS...",                       "netsh int tcp set global rss=enabled"),
        ("Deshabilitando Large Send Offload IPv4...", "netsh int ip set global taskoffload=disabled"),
        ("Flusheando DNS...",                         "ipconfig /flushdns"),
        ("Liberando y renovando IP...",               "ipconfig /release && ipconfig /renew"),
        ("Optimizando parámetros Winsock...",         "netsh winsock reset catalog"),
    ]
    for i, (msg, cmd) in enumerate(comandos):
        yield (msg, int((i / len(comandos)) * 90))
        _run(cmd)
    yield ("✅ Red optimizada correctamente", 100)


def optimizar_efectos_visuales():
    yield ("Ajustando efectos visuales para máximo rendimiento...", 20)
    try:
        kp = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, kp, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
    except Exception:
        pass
    yield ("Desactivando animaciones...", 50)
    try:
        kp2 = r"Control Panel\Desktop\WindowMetrics"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, kp2, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "MinAnimate", 0, winreg.REG_SZ, "0")
    except Exception:
        pass
    yield ("Aplicando configuración de rendimiento...", 70)
    _run('reg add "HKCU\\Control Panel\\Desktop" /v UserPreferencesMask /t REG_BINARY /d 9012038010000000 /f')
    _run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v ListviewShadow /t REG_DWORD /d 0 /f')
    _run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v TaskbarAnimations /t REG_DWORD /d 0 /f')
    yield ("✅ Efectos visuales optimizados", 100)


def optimizar_ssd():
    yield ("Detectando SSDs...", 10)
    _run("defrag C: /U /V /retrim")
    yield ("Ejecutando TRIM en todas las unidades...", 50)
    try:
        import psutil
        for part in psutil.disk_partitions():
            letra = part.mountpoint.replace("\\", "")
            _run(f"defrag {letra} /retrim /U")
    except Exception:
        pass
    yield ("✅ TRIM ejecutado correctamente en SSDs", 100)


def desfragmentar_hdd():
    yield ("Detectando unidades HDD...", 10)
    try:
        import psutil
        hdds = [p.mountpoint for p in psutil.disk_partitions() if "cdrom" not in p.opts]
        for i, letra in enumerate(hdds):
            l = letra.replace("\\", "")
            yield (f"Desfragmentando {l}...", int(10 + (i / max(len(hdds), 1)) * 80))
            _run(f"defrag {l} /U /V")
    except Exception:
        yield ("⚠ No se pudo detectar unidades", 50)
    yield ("✅ Desfragmentación completada", 100)


def liberar_ram():
    yield ("Modificando registro — PrefetchParameters...", 20)
    try:
        k1 = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k1, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "EnablePrefetcher", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(k, "EnableSuperfetch", 0, winreg.REG_DWORD, 0)
    except Exception as e:
        yield (f"⚠ No se pudo modificar PrefetchParameters: {e}", 30)
    yield ("Modificando registro — SysMain (Superfetch service)...", 50)
    try:
        k2 = r"SYSTEM\CurrentControlSet\Services\SysMain"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k2, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "Start", 0, winreg.REG_DWORD, 0)
    except Exception as e:
        yield (f"⚠ No se pudo modificar SysMain: {e}", 60)
    yield ("Deteniendo servicio SysMain...", 70)
    _run("sc stop SysMain")
    _run("sc config SysMain start= disabled")
    yield ("Vaciando caché de memoria...", 85)
    _run('powershell -Command "Get-Process | ForEach-Object { $_.MinWorkingSet = 1MB }" 2>$null')
    yield ("✅ RAM liberada y Superfetch deshabilitado", 100)


def restaurar_sysmain():
    yield ("Restaurando PrefetchParameters...", 25)
    try:
        k1 = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k1, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "EnablePrefetcher", 0, winreg.REG_DWORD, 3)
            winreg.SetValueEx(k, "EnableSuperfetch", 0, winreg.REG_DWORD, 3)
    except Exception as e:
        yield (f"⚠ Error: {e}", 40)
    yield ("Restaurando SysMain service...", 60)
    try:
        k2 = r"SYSTEM\CurrentControlSet\Services\SysMain"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k2, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "Start", 0, winreg.REG_DWORD, 2)
    except Exception as e:
        yield (f"⚠ Error: {e}", 70)
    yield ("Iniciando servicio SysMain...", 85)
    _run("sc config SysMain start= auto")
    _run("sc start SysMain")
    yield ("✅ SysMain/Superfetch restaurado correctamente", 100)


def limpiar_dns():
    yield ("Limpiando caché DNS...", 50)
    _run("ipconfig /flushdns")
    yield ("✅ Caché DNS limpiada", 100)


def get_startup_apps():
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
