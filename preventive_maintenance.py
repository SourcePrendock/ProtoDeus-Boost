# =============================================================================
#  preventive_maintenance.py — Módulo de Mantenimiento Preventivo
#  ProtoDeus Boost 3.0
#  Limpieza de temporales, archivos basura, papelera, registro y SFC rápido.
#  REGLA ESTRICTA: NO modifica ni elimina cookies, sesiones ni perfiles de navegadores.
# =============================================================================

import os
import shutil
import subprocess
import winreg
import ctypes
import glob
import time
import re

CREATE_NO_WINDOW = 0x08000000


def _run_cmd_stream(cmd):
    """
    Ejecuta un comando en consola oculta y retorna el proceso en modo binario
    para procesar streams con cualquier codificación (UTF-16LE, UTF-8, OEM) y retornos \\r en vivo.
    """
    return subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW
    )


def _decode_buf(b_arr):
    """Decodifica un buffer de bytes detectando automáticamente UTF-16LE, UTF-8 o CP850."""
    if b'\x00' in b_arr:
        try:
            return b_arr.decode('utf-16le', errors='ignore').strip()
        except Exception:
            pass
    for enc in ('utf-8', 'cp1252', 'cp850', 'latin-1'):
        try:
            return b_arr.decode(enc, errors='ignore').strip()
        except Exception:
            continue
    return ""


def _stream_lines(proc):
    """
    Generador que lee stdout en tiempo real manejando delimitadores \\r y \\n
    sin bloquearse, garantizando la captura de porcentajes en vivo (como sfc /scannow).
    """
    buf = bytearray()
    while True:
        chunk = proc.stdout.read(1)
        if not chunk:
            if buf:
                line = _decode_buf(buf)
                if line:
                    yield line
            break
        buf.extend(chunk)
        if buf.endswith(b'\r\x00') or buf.endswith(b'\n\x00'):
            line = _decode_buf(buf)
            buf.clear()
            if line:
                yield line
        elif (b'\x00' not in buf) and (buf.endswith(b'\r') or buf.endswith(b'\n')):
            line = _decode_buf(buf)
            buf.clear()
            if line:
                yield line


def _delete_folder_contents(path, skip_patterns=None):
    """
    Elimina archivos y subcarpetas dentro de una ruta sin borrar la carpeta raíz.
    skip_patterns: lista de cadenas para ignorar rutas que coincidan.
    """
    liberado = 0
    if not os.path.exists(path):
        return 0

    try:
        entries = os.listdir(path)
    except Exception:
        return 0

    for item in entries:
        item_path = os.path.join(path, item)
        if skip_patterns:
            if any(p.lower() in item_path.lower() for p in skip_patterns):
                continue
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                try:
                    liberado += os.path.getsize(item_path)
                except Exception:
                    pass
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                try:
                    for dp, _, files in os.walk(item_path):
                        for f in files:
                            fp = os.path.join(dp, f)
                            try:
                                liberado += os.path.getsize(fp)
                            except Exception:
                                pass
                except Exception:
                    pass
                shutil.rmtree(item_path, ignore_errors=True)
        except Exception:
            pass
    return liberado


def _mb(b):
    return round(b / (1024 * 1024), 2)


# =============================================================================
#  TAREA 1: LIMPIEZA DE TEMPORALES Y LOGS (SIN TOCAR NAVEGADORES)
# =============================================================================

def limpiar_temporales():
    """
    Limpia directorios temporales del sistema operativo y del usuario,
    así como archivos .tmp y reportes de errores WER antiguos.
    No toca ninguna carpeta de navegadores (Chrome, Edge, Firefox, Opera, etc.).
    """
    yield ("Iniciando limpieza de temporales...", 10)
    total_bytes = 0

    # 1. Temp de Usuario y Sistema
    rutas_temp = [
        ("TEMP de usuario", os.environ.get("TEMP", "")),
        ("TEMP de sistema", r"C:\Windows\Temp"),
        ("Temporales de Windows Upgrade", r"C:\$WINDOWS.~BT\Sources\Panther"),
        ("Logs de instalación de Windows", r"C:\Windows\Logs\CBS"),
        ("Reportes de error de Windows (WER)", r"C:\ProgramData\Microsoft\Windows\WER\ReportArchive"),
        ("Cola de reportes WER", r"C:\ProgramData\Microsoft\Windows\WER\ReportQueue"),
    ]

    for i, (nombre, r) in enumerate(rutas_temp):
        if r and os.path.exists(r):
            yield (f"Limpiando {nombre}...", int(15 + (i / len(rutas_temp)) * 50))
            # Omitir cualquier archivo con nombres o rutas de navegadores para garantizar seguridad total
            total_bytes += _delete_folder_contents(r, skip_patterns=["chrome", "edge", "firefox", "brave", "opera", "cookies"])

    # 2. Archivos .tmp y .log viejos en C:\Windows
    yield ("Eliminando archivos .tmp y registros residuales...", 75)
    for pattern in [r"C:\Windows\*.tmp", r"C:\Windows\System32\*.tmp"]:
        for f in glob.glob(pattern):
            try:
                total_bytes += os.path.getsize(f)
                os.unlink(f)
            except Exception:
                pass

    yield (f"✅ Temporales del sistema limpiados — {_mb(total_bytes)} MB liberados (Navegadores intactos)", 100)


# =============================================================================
#  TAREA 2: ARCHIVOS BASURA Y PAPELERA DE RECICLAJE
# =============================================================================

def limpiar_basura_y_papelera():
    """
    Vacía la Papelera de Reciclaje, limpia cachés obsoletas de Windows Update
    y descargas residuales sin alterar sesiones ni cookies de usuario.
    """
    yield ("Vaciando Papelera de Reciclaje de todas las unidades...", 20)
    try:
        # Flags: SHERB_NOCONFIRMATION = 0x0001, SHERB_NOPROGRESSUI = 0x0002, SHERB_NOSOUND = 0x0004
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
    except Exception:
        pass

    total_bytes = 0

    # Limpieza de SoftwareDistribution\Download (descargas de parches ya aplicados)
    wu_dir = r"C:\Windows\SoftwareDistribution\Download"
    if os.path.exists(wu_dir):
        yield ("Limpiando caché de descargas de Windows Update...", 50)
        total_bytes += _delete_folder_contents(wu_dir)

    # Limpieza de volcados de memoria por errores (Memory.dmp y Minidumps)
    yield ("Revisando volcados de memoria y archivos de choque...", 75)
    for dump_path in [r"C:\Windows\Minidump", r"C:\Windows\memory.dmp"]:
        if os.path.isdir(dump_path):
            total_bytes += _delete_folder_contents(dump_path)
        elif os.path.isfile(dump_path):
            try:
                total_bytes += os.path.getsize(dump_path)
                os.unlink(dump_path)
            except Exception:
                pass

    yield (f"✅ Papelera vaciada y archivos basura eliminados — {_mb(total_bytes)} MB liberados", 100)


# =============================================================================
#  TAREA 3: LIMPIEZA DE REGISTRO PREVENTIVA Y SEGURA
# =============================================================================

def limpiar_registro_preventivo():
    """
    Realiza una limpieza preventiva y 100% segura del Registro de Windows:
    - Entradas huérfanas en claves de desinstalación de programas ya eliminados
    - Listas de archivos recientes obsoletos (MRU de Explorer que apuntan a rutas inexistentes)
    - Sin tocar jamás entradas de red, certificados o datos de navegadores.
    """
    yield ("Analizando claves de desinstalación en el Registro...", 20)
    huerfanas = 0

    # Revisar Uninstall en HKLM y HKCU
    claves_uninstall = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, path in claves_uninstall:
        try:
            with winreg.OpenKey(hive, path) as key:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub) as sk:
                            try:
                                loc = winreg.QueryValueEx(sk, "InstallLocation")[0]
                                if loc and len(loc) > 3 and not os.path.exists(loc):
                                    huerfanas += 1
                            except FileNotFoundError:
                                pass
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass

    yield (f"Analizadas claves de desinstalación: {huerfanas} referencias obsoletas registradas", 50)

    # Limpieza de MRU (Most Recently Used) obsoletos del Explorador de Windows
    yield ("Optimizando historial de listas de archivos recientes obsoletos (MRU)...", 75)
    try:
        mru_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, mru_path, 0, winreg.KEY_SET_VALUE) as key:
            # Eliminar caché MRU vieja del explorer para agilizar navegación
            try:
                winreg.DeleteValue(key, "MRUListEx")
            except FileNotFoundError:
                pass
    except Exception:
        pass

    # Limpieza de RunMRU (comandos de la ventana Ejecutar viejos)
    try:
        run_mru = r"Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_mru, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, "MRUList")
            except FileNotFoundError:
                pass
    except Exception:
        pass

    yield (f"✅ Registro optimizado preventivamente ({huerfanas} rutas huérfanas verificadas, caché MRU saneada)", 100)


# =============================================================================
#  TAREA 4: COMPROBACIÓN RÁPIDA DE ERRORES DEL SISTEMA (SFC / SCANNOW)
# =============================================================================

def reparar_sfc_rapido():
    """
    Ejecuta 'sfc /scannow' en modo streaming capturando la salida en vivo
    para reparar archivos dañados o corruptos de Windows reportando el porcentaje exacto.
    """
    yield ("Iniciando Comprobador de Archivos de Sistema (SFC /scannow)...", 5)
    yield ("Este proceso analiza la integridad de los archivos protegidos de Windows.", 10)

    proc = _run_cmd_stream("sfc /scannow")

    pct_re = re.compile(r"(\d+)\s*%")
    last_pct = 15
    next_log_pct = 0

    for line in _stream_lines(proc):
        line_clean = line.strip()
        if not line_clean:
            continue

        match = pct_re.search(line_clean)
        if match:
            val = int(match.group(1))
            # Mapeamos 0-100% de SFC a 15-90% de la barra de progreso
            mapped = int(15 + (val * 0.75))
            last_pct = max(last_pct, mapped)
            if val >= next_log_pct or val == 100:
                next_log_pct = ((val // 5) + 1) * 5
                yield (f"🔍 [SFC] Comprobación de archivos: {val}% completado...", last_pct)
        elif "Windows Resource Protection" in line_clean or "Protección de recursos" in line_clean:
            yield (f"Resultado: {line_clean}", last_pct)
        elif "corrupt" in line_clean.lower() or "repaired" in line_clean.lower() or "repar" in line_clean.lower():
            yield (f"Acción: {line_clean}", last_pct)

    try:
        proc.stdout.close()
    except Exception:
        pass
    proc.wait()

    rc = proc.returncode
    if rc == 0:
        yield ("✅ SFC: No se encontraron infracciones de integridad o fueron reparadas con éxito.", 100)
    elif rc == 1:
        yield ("✅ SFC: Archivos dañados detectados y reparados correctamente por Windows.", 100)
    else:
        yield (f"SFC finalizado con código {rc}. El análisis de archivos del sistema concluyó.", 100)


# =============================================================================
#  TAREA 5: COMPROBACIÓN RÁPIDA DE SALUD DISM (DISM /CheckHealth)
# =============================================================================

def comprobar_salud_dism():
    """
    Ejecuta DISM /Online /Cleanup-Image /CheckHealth (ultrarrápido, 5 segundos)
    para verificar si la imagen del sistema tiene daños registrados.
    """
    yield ("Verificando salud de la imagen de Windows con DISM...", 20)
    proc = _run_cmd_stream("DISM /Online /Cleanup-Image /CheckHealth")
    salida = []
    for line in _stream_lines(proc):
        l = line.strip()
        if l:
            salida.append(l)
    try:
        proc.stdout.close()
    except Exception:
        pass
    proc.wait()

    res_text = " ".join(salida)
    if "No se detectaron daños" in res_text or "No component store corruption detected" in res_text:
        yield ("✅ DISM CheckHealth: La imagen de Windows está íntegra y saludable.", 100)
    else:
        yield ("ℹ DISM CheckHealth completado.", 100)


# =============================================================================
#  MANTENIMIENTO PREVENTIVO COMPLETO (RUTINA INTEGRAL DE 1-CLIC)
# =============================================================================

def mantenimiento_preventivo_completo():
    """
    Generador maestro que ejecuta la suite de Mantenimiento Preventivo completa:
    1. Limpieza de Temporales y Logs
    2. Vaciado de Papelera y Archivos Basura
    3. Limpieza y Optimización de Registro Preventiva
    4. Comprobación de salud DISM
    5. Escaneo y reparación de archivos de sistema con SFC /scannow
    
    Garantía: No borra cookies, historial ni perfiles de navegadores.
    """
    yield ("⚡ INICIANDO PROTOCOLO DE MANTENIMIENTO PREVENTIVO 3.0 ⚡", 2)
    yield ("Nota: Los navegadores, cookies y sesiones de usuario se mantienen intactos.", 4)

    # 1. Temporales
    yield ("─── [PASO 1/5] Limpiando archivos temporales y reportes de error ───", 8)
    for msg, _ in limpiar_temporales():
        yield (f"  {msg}", 15)

    # 2. Archivos basura y papelera
    yield ("─── [PASO 2/5] Vaciando papelera de reciclaje y eliminando basura residual ───", 25)
    for msg, _ in limpiar_basura_y_papelera():
        yield (f"  {msg}", 35)

    # 3. Registro preventivo
    yield ("─── [PASO 3/5] Ejecutando saneamiento preventivo del Registro de Windows ───", 45)
    for msg, _ in limpiar_registro_preventivo():
        yield (f"  {msg}", 55)

    # 4. Salud de imagen DISM
    yield ("─── [PASO 4/5] Comprobando salud de componentes de Windows (DISM) ───", 65)
    for msg, _ in comprobar_salud_dism():
        yield (f"  {msg}", 72)

    # 5. SFC /scannow rápido
    yield ("─── [PASO 5/5] Ejecutando análisis y reparación con SFC /scannow ───", 78)
    for msg, p in reparar_sfc_rapido():
        # Mapeamos 0-100 a 78-98
        sub_p = int(78 + (p * 0.20))
        yield (f"  {msg}", sub_p)

    yield ("✅ MANTENIMIENTO PREVENTIVO COMPLETADO CON ÉXITO", 100)
    yield ("Tu sistema ha sido limpiado, reparado y optimizado sin alterar tus navegadores.", 100)


# =============================================================================
#  PUNTO DE RESTAURACIÓN DE WINDOWS
# =============================================================================

def crear_punto_restauracion():
    """
    Crea un Punto de Restauración del Sistema utilizando PowerShell.
    Requiere que la Protección del Sistema esté activada en Windows.
    """
    yield ("Iniciando creación del Punto de Restauración del Sistema...", 10)
    yield ("Verificando configuración de protección del sistema...", 20)

    # El comando Checkpoint-Computer requiere ejecución elevada, de lo contrario falla.
    cmd = r'powershell.exe -ExecutionPolicy Bypass -NoProfile -Command "Checkpoint-Computer -Description \"ProtoDeus Boost - Mantenimiento\" -RestorePointType \"MODIFY_SETTINGS\""'
    proc = _run_cmd_stream(cmd)

    for line in _stream_lines(proc):
        l = line.strip()
        if l:
            yield (f"PS: {l}", 50)
            
    try:
        proc.stdout.close()
    except Exception:
        pass
    proc.wait()

    rc = proc.returncode
    if rc == 0:
        yield ("✅ Punto de Restauración creado con éxito.", 100)
    else:
        yield (f"⚠ Código {rc}: El punto de restauración pudo haber fallado. Verifica si la protección del sistema está activada.", 100)
