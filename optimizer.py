import os
import shutil
import subprocess
import winreg
import ctypes
import glob


def _run(cmd, shell=True):
    result = subprocess.run(
        cmd, shell=shell, capture_output=True, text=True,
        encoding="utf-8", errors="ignore"
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


def limpiar_temporales():
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
    yield (f"✅ Temporales limpiados — {_mb(total)} MB liberados", 100)


def limpieza_profunda():
    yield ("Iniciando limpieza profunda...", 5)
    total = 0
    for ruta in [os.environ.get("TEMP", ""), r"C:\Windows\Temp", r"C:\Windows\Prefetch"]:
        if ruta:
            yield (f"Limpiando: {ruta}", 10)
            total += _delete_folder_contents(ruta)
    yield ("Vaciando Papelera de Reciclaje...", 30)
    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
    thumb_db = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Explorer")
    yield ("Limpiando caché de miniaturas...", 50)
    total += _delete_folder_contents(thumb_db)
    yield ("Limpiando caché de fuentes...", 60)
    try:
        fc = r"C:\Windows\System32\FNTCACHE.DAT"
        if os.path.exists(fc):
            os.unlink(fc)
    except Exception:
        pass
    wu_logs = r"C:\Windows\SoftwareDistribution\Download"
    yield ("Limpiando archivos de Windows Update...", 70)
    total += _delete_folder_contents(wu_logs)
    yield ("Eliminando archivos de volcado de memoria...", 80)
    for dp in [r"C:\Windows\Minidump", r"C:\Windows\memory.dmp"]:
        if os.path.isdir(dp):
            total += _delete_folder_contents(dp)
        elif os.path.isfile(dp):
            try:
                total += os.path.getsize(dp)
                os.unlink(dp)
            except Exception:
                pass
    yield ("Eliminando logs antiguos del sistema...", 90)
    for pattern in [r"C:\Windows\*.log", r"C:\Windows\*.bak"]:
        for f in glob.glob(pattern):
            try:
                total += os.path.getsize(f)
                os.unlink(f)
            except Exception:
                pass
    yield (f"✅ Limpieza profunda completa — {_mb(total)} MB liberados", 100)


def limpiar_navegadores():
    local = os.environ.get("LOCALAPPDATA", "")
    appd = os.environ.get("APPDATA", "")
    rutas_nav = {
        "Google Chrome":  [os.path.join(local, r"Google\Chrome\User Data\Default\Cache"),
                           os.path.join(local, r"Google\Chrome\User Data\Default\Code Cache")],
        "Microsoft Edge": [os.path.join(local, r"Microsoft\Edge\User Data\Default\Cache"),
                           os.path.join(local, r"Microsoft\Edge\User Data\Default\Code Cache")],
        "Firefox":        [os.path.join(appd, r"Mozilla\Firefox\Profiles")],
        "Brave":          [os.path.join(local, r"BraveSoftware\Brave-Browser\User Data\Default\Cache")],
        "Opera":          [os.path.join(appd, r"Opera Software\Opera Stable\Cache")],
    }
    total = 0
    items = list(rutas_nav.items())
    for i, (nav, rutas) in enumerate(items):
        yield (f"Limpiando {nav}...", int((i / len(items)) * 90))
        for ruta in rutas:
            if "Profiles" in ruta and os.path.exists(ruta):
                for perfil in os.listdir(ruta):
                    total += _delete_folder_contents(os.path.join(ruta, perfil, "cache2"))
            else:
                total += _delete_folder_contents(ruta)
    yield (f"✅ Caché de navegadores limpiada — {_mb(total)} MB liberados", 100)


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
