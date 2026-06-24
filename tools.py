import subprocess
import winreg
import os
import re
import socket
import time
import statistics
import urllib.request


def _run(cmd, shell=True, timeout=60):
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


def restablecer_red():
    pasos = [
        ("Reseteando catálogo Winsock...",         "netsh winsock reset"),
        ("Reseteando pila IPv4...",                 "netsh int ip reset"),
        ("Reseteando pila IPv6...",                 "netsh int ipv6 reset"),
        ("Reseteando configuración Firewall...",    "netsh advfirewall reset"),
        ("Reseteando parámetros TCP/IP...",         "netsh int tcp reset"),
        ("Liberando configuración IP actual...",    "ipconfig /release"),
        ("Limpiando caché DNS...",                  "ipconfig /flushdns"),
        ("Renovando dirección IP...",               "ipconfig /renew"),
        ("Limpiando caché ARP...",                  "arp -d *"),
        ("Reseteando proxy de red...",              "netsh winhttp reset proxy"),
    ]
    for i, (msg, cmd) in enumerate(pasos):
        pct = int((i / len(pasos)) * 90)
        yield (msg, pct)
        _run(cmd)
    yield ("✅ Restablecimiento completado. Se recomienda reiniciar el PC.", 100)


def _get_product_key_from_registry():
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
    rc, stdout, _ = _run(
        "wmic path SoftwareLicensingService get OA3xOriginalProductKey",
        timeout=15
    )
    if rc == 0 and stdout:
        for line in [l.strip() for l in stdout.splitlines() if l.strip()]:
            if len(line) == 29 and line.count("-") == 4:
                return line
    return None


def _get_slmgr_info():
    rc, stdout, _ = _run("cscript //nologo %windir%\\system32\\slmgr.vbs /dli", timeout=30)
    return stdout if rc == 0 else ""


def _get_slmgr_xpr():
    rc, stdout, _ = _run("cscript //nologo %windir%\\system32\\slmgr.vbs /xpr", timeout=30)
    return stdout if rc == 0 else ""


def _detect_license_type(slmgr_output, oa3_key):
    output_lower = slmgr_output.lower()
    if "volume:gvlk" in output_lower or "kms" in output_lower or "kmsclient" in output_lower:
        return "KMS (Genérica / Volumen)", "Licencia de volumen activada por servidor KMS. Común en empresas y versiones genéricas."
    elif "oem" in output_lower:
        return "OEM", "Licencia vinculada al hardware de fábrica. No transferible a otra PC."
    elif "retail" in output_lower:
        return "Retail (Comprada)", "Licencia de venta al público. Transferible a otra PC."
    elif oa3_key:
        return "OEM (BIOS/UEFI)", "Licencia incrustada en el firmware del fabricante."
    elif "coa" in output_lower:
        return "COA (Certificate of Authenticity)", "Licencia de sticker físico adjunto al equipo."
    return "Desconocido", ""


def get_license_info():
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
        reg_key = _get_product_key_from_registry()
        if reg_key:
            info["clave_instalada"] = reg_key
        oa3 = _get_oa3_key()
        if oa3:
            info["clave_bios"] = oa3
        slmgr_dli = _get_slmgr_info()
        slmgr_xpr = _get_slmgr_xpr()
        if slmgr_dli:
            m = re.search(r"Name:\s*(.+)", slmgr_dli, re.IGNORECASE)
            if m:
                info["nombre_licencia"] = m.group(1).strip()
            m = re.search(r"Description:\s*(.+)", slmgr_dli, re.IGNORECASE)
            if m:
                info["descripcion"] = m.group(1).strip()
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
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
                info["edicion"] = winreg.QueryValueEx(k, "EditionID")[0]
        except Exception:
            pass
    except Exception as e:
        info["error"] = str(e)
    return info


REPARACIONES_WINDOWS = {
    "lockscreen": {
        "nombre": "🔐  Reparar Pantalla de Bloqueo",
        "descripcion": "Restablece la pantalla de bloqueo y el servicio de inicio de sesión.",
        "pasos": [
            ("Reiniciando servicio de pantalla de bloqueo...",
             "sc stop LockAppHost & sc start LockAppHost"),
            ("Limpiando caché de pantalla de bloqueo...",
             r'del /q /f "%localappdata%\Packages\Microsoft.LockApp_cw5n1h2txyewy\LocalCache\*"'),
            ("Restableciendo políticas de pantalla de bloqueo...",
             "reg delete \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Personalization\" /f"),
            ("Registrando pantalla de bloqueo de nuevo...",
             "powershell -Command \"Get-AppxPackage Microsoft.LockApp | "
             "Foreach {Add-AppxPackage -DisableDevelopmentMode -Register \\\"$($_.InstallLocation)\\AppXManifest.xml\\\"}\""),
        ],
    },
    "settings": {
        "nombre": "⚙  Reparar Configuración de Windows",
        "descripcion": "Repara la app de Configuración que se cierra automáticamente al abrirse.",
        "pasos": [
            ("Registrando app de Configuración...",
             "powershell -Command \"Get-AppxPackage *windows.immersivecontrolpanel* | "
             "Foreach {Add-AppxPackage -DisableDevelopmentMode -Register \\\"$($_.InstallLocation)\\AppXManifest.xml\\\"}\""),
            ("Reparando permisos de Configuración en registro...",
             "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer\" "
             "/v NoControlPanel /t REG_DWORD /d 0 /f"),
            ("Restableciendo permisos de SystemSettings...",
             "icacls \"%ProgramFiles%\\WindowsApps\" /reset /T /C /Q"),
            ("Limpiando caché de la app de Configuración...",
             r"powershell -Command \"Remove-Item -Path "
             r"'$env:LOCALAPPDATA\Packages\windows.immersivecontrolpanel_cw5n1h2txyewy\LocalCache' "
             r"-Recurse -Force -ErrorAction SilentlyContinue\""),
        ],
    },
    "sfc": {
        "nombre": "🛡  Escaneo SFC + DISM",
        "descripcion": "Verifica y repara archivos de sistema dañados o faltantes.",
        "pasos": [
            ("Ejecutando SFC /scannow (puede tardar varios minutos)...", "sfc /scannow"),
            ("Verificando imagen del sistema con DISM...",
             "DISM /Online /Cleanup-Image /CheckHealth"),
            ("Reparando imagen del sistema con DISM...",
             "DISM /Online /Cleanup-Image /RestoreHealth"),
        ],
    },
    "store": {
        "nombre": "🛒  Reparar Windows Store / Apps",
        "descripcion": "Restablece la tienda de Microsoft y re-registra las apps universales.",
        "pasos": [
            ("Reseteando Windows Store...", "wsreset.exe"),
            ("Re-registrando apps de Microsoft...",
             "powershell -Command \"Get-AppxPackage -AllUsers | "
             "Foreach {Add-AppxPackage -DisableDevelopmentMode -Register "
             "\\\"$($_.InstallLocation)\\AppXManifest.xml\\\" -ErrorAction SilentlyContinue}\""),
            ("Reiniciando servicios de la tienda...",
             "net stop wuauserv & net start wuauserv"),
        ],
    },
    "updates": {
        "nombre": "🔃  Reparar Windows Update",
        "descripcion": "Resetea los componentes de Windows Update para solucionar actualizaciones bloqueadas.",
        "pasos": [
            ("Deteniendo servicios de Windows Update...",
             "net stop wuauserv & net stop cryptSvc & net stop bits & net stop msiserver"),
            ("Eliminando caché de actualizaciones...",
             r"rd /s /q C:\Windows\SoftwareDistribution & rd /s /q C:\Windows\System32\catroot2"),
            ("Reiniciando servicios de Windows Update...",
             "net start wuauserv & net start cryptSvc & net start bits & net start msiserver"),
            ("Forzando comprobación de actualizaciones...",
             "wuauclt /resetauthorization /detectnow"),
        ],
    },
    "taskbar": {
        "nombre": "📌  Reparar Barra de Tareas / Explorer",
        "descripcion": "Reinicia el explorador de Windows y repara la barra de tareas congelada.",
        "pasos": [
            ("Terminando proceso Explorer.exe...", "taskkill /f /im explorer.exe"),
            ("Limpiando caché de la barra de tareas...",
             r'del /q /f "%localappdata%\IconCache.db"'),
            ("Reparando caché de miniaturas...",
             r'del /q /f /s "%localappdata%\Microsoft\Windows\Explorer\thumbcache_*.db"'),
            ("Reiniciando Explorer.exe...", "start explorer.exe"),
        ],
    },
    "audio": {
        "nombre": "🔊  Reparar Audio de Windows",
        "descripcion": "Reinicia los servicios de audio y repara el subsistema de sonido.",
        "pasos": [
            ("Reiniciando servicio Windows Audio...",
             "net stop Audiosrv & net start Audiosrv"),
            ("Reiniciando servicio AudioEndpointBuilder...",
             "net stop AudioEndpointBuilder & net start AudioEndpointBuilder"),
            ("Escaneando drivers de audio con SFC...", "sfc /scannow"),
        ],
    },
    "drivers": {
        "nombre": "🖱  Reparar Drivers del Sistema",
        "descripcion": "Verifica la integridad de drivers y repara los dañados.",
        "pasos": [
            ("Verificando integridad de drivers con SFC...", "sfc /verifyonly"),
            ("Analizando drivers problemáticos...",
             "dism /online /get-drivers /all"),
            ("Reparando imagen con controladores...",
             "DISM /Online /Cleanup-Image /RestoreHealth"),
            ("Escaneando y reparando archivos de sistema...", "sfc /scannow"),
        ],
    },
    "defender": {
        "nombre": "🛡  Reparar Windows Defender",
        "descripcion": "Reinicia Windows Defender y actualiza sus definiciones de seguridad.",
        "pasos": [
            ("Reiniciando Windows Defender...",
             "net stop WinDefend & net start WinDefend"),
            ("Actualizando definiciones de Defender...",
             r'"C:\Program Files\Windows Defender\MpCmdRun.exe" -SignatureUpdate'),
            ("Ejecutando análisis rápido de Defender...",
             r'"C:\Program Files\Windows Defender\MpCmdRun.exe" -Scan -ScanType 1'),
        ],
    },
}


def reparar_windows(repair_key):
    repair = REPARACIONES_WINDOWS.get(repair_key)
    if not repair:
        yield ("❌ Reparación no encontrada.", 100)
        return
    pasos = repair["pasos"]
    total = len(pasos)
    for i, (msg, cmd) in enumerate(pasos):
        pct = int((i / total) * 90)
        yield (msg, pct)
        rc, stdout, stderr = _run(cmd, timeout=300)
        if rc == 0:
            yield (f"✅ {msg.rstrip('.')}", pct + int(90 / total))
        else:
            err = stderr.strip() or "Sin detalles"
            yield (f"⚠ {msg.rstrip('.')} — {err[:80]}", pct + int(90 / total))
    yield (f"✅ {repair['nombre'].split('  ', 1)[-1]} completado.", 100)


def test_internet():
    resultados = {}

    yield ("🔍 Detectando proveedor de internet...", 5)
    try:
        resp = urllib.request.urlopen("https://ipinfo.io/json", timeout=8)
        import json
        data = json.loads(resp.read().decode())
        resultados["proveedor"] = data.get("org", "No identificado")
        resultados["ip_publica"] = data.get("ip", "No identificado")
        resultados["ciudad"] = data.get("city", "No identificado")
        resultados["pais"] = data.get("country", "No identificado")
    except Exception:
        resultados["proveedor"] = "No identificado"
        resultados["ip_publica"] = "No identificado"
        resultados["ciudad"] = "No identificado"
        resultados["pais"] = "No identificado"

    yield ("📡 Midiendo latencia y paquetes perdidos...", 20)
    hosts = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
    latencias = []
    perdidos = 0
    total_pings = 0
    for host in hosts:
        rc, stdout, _ = _run(f"ping -n 10 {host}", timeout=30)
        if rc == 0:
            tiempos = re.findall(r"tiempo[<=](\d+)ms|time[<=](\d+)ms", stdout, re.IGNORECASE)
            for t1, t2 in tiempos:
                latencias.append(int(t1 or t2))
            m = re.search(r"Perdidos\s*=\s*(\d+)|Lost\s*=\s*(\d+)", stdout, re.IGNORECASE)
            if m:
                perdidos += int(m.group(1) or m.group(2))
            total_pings += 10

    if latencias:
        resultados["latencia_ms"] = round(statistics.mean(latencias), 1)
        resultados["latencia_min_ms"] = min(latencias)
        resultados["latencia_max_ms"] = max(latencias)
        resultados["jitter_ms"] = round(statistics.stdev(latencias), 1) if len(latencias) > 1 else 0
    else:
        resultados["latencia_ms"] = None
        resultados["latencia_min_ms"] = None
        resultados["latencia_max_ms"] = None
        resultados["jitter_ms"] = None

    resultados["paquetes_perdidos_pct"] = round((perdidos / total_pings) * 100, 1) if total_pings > 0 else 100

    yield ("⬇ Midiendo velocidad de descarga...", 50)
    descarga_mbps = _medir_velocidad_descarga()
    resultados["descarga_mbps"] = descarga_mbps

    yield ("⬆ Midiendo velocidad de subida...", 75)
    subida_mbps = _medir_velocidad_subida()
    resultados["subida_mbps"] = subida_mbps

    yield ("📊 Calculando calidad de red...", 90)
    resultados["calidad"] = _calcular_calidad(resultados)

    yield ("✅ Test de internet completado.", 100)
    resultados["completado"] = True
    yield ("__RESULT__", resultados)


def _medir_velocidad_descarga():
    urls = [
        "http://speedtest.tele2.net/10MB.zip",
        "http://proof.ovh.net/files/10Mb.dat",
    ]
    for url in urls:
        try:
            inicio = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            datos = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                datos += len(chunk)
                if time.time() - inicio > 10:
                    break
            elapsed = time.time() - inicio
            if elapsed > 0.5 and datos > 0:
                return round((datos * 8) / (elapsed * 1_000_000), 2)
        except Exception:
            continue
    return None


def _medir_velocidad_subida():
    try:
        import http.client
        payload = b"0" * (2 * 1024 * 1024)
        inicio = time.time()
        conn = http.client.HTTPSConnection("httpbin.org", timeout=15)
        conn.request("POST", "/post", body=payload,
                     headers={"Content-Type": "application/octet-stream",
                               "Content-Length": str(len(payload))})
        resp = conn.getresponse()
        elapsed = time.time() - inicio
        conn.close()
        if elapsed > 0.5:
            return round((len(payload) * 8) / (elapsed * 1_000_000), 2)
    except Exception:
        pass
    return None


def _calcular_calidad(r):
    score = 10.0

    lat = r.get("latencia_ms")
    if lat is None:
        score -= 4
    elif lat > 200:
        score -= 3
    elif lat > 100:
        score -= 2
    elif lat > 50:
        score -= 1

    jitter = r.get("jitter_ms", 0) or 0
    if jitter > 50:
        score -= 2
    elif jitter > 20:
        score -= 1

    perdidos = r.get("paquetes_perdidos_pct", 100)
    if perdidos > 10:
        score -= 3
    elif perdidos > 5:
        score -= 2
    elif perdidos > 1:
        score -= 1

    down = r.get("descarga_mbps")
    if down is None:
        score -= 1
    elif down < 5:
        score -= 2
    elif down < 20:
        score -= 1

    up = r.get("subida_mbps")
    if up is None:
        score -= 0.5
    elif up < 2:
        score -= 1

    score = max(1, min(10, round(score, 1)))

    if score >= 8:
        color = "#10B981"
        etiqueta = "Excelente"
    elif score >= 6:
        color = "#F59E0B"
        etiqueta = "Buena"
    elif score >= 4:
        color = "#F97316"
        etiqueta = "Regular"
    else:
        color = "#EF4444"
        etiqueta = "Mala"

    return {"puntuacion": score, "color": color, "etiqueta": etiqueta}
