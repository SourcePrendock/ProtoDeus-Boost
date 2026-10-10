import platform
import subprocess
import socket
import re
import json

CREATE_NO_WINDOW = 0x08000000

def _run_cmd(cmd, timeout=4):
    try:
        res = subprocess.run(cmd, text=True, shell=True, capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=timeout)
        return res.stdout.strip()
    except Exception:
        return ""

def get_cpu_info():
    info = {
        "nombre": "No identificado",
        "nucleos_fisicos": "No identificado",
        "hilos": "No identificado",
        "frecuencia_base_ghz": "No identificado",
        "frecuencia_max_ghz": "No identificado",
        "arquitectura": platform.machine(),
    }
    try:
        import psutil
        info["nucleos_fisicos"] = psutil.cpu_count(logical=False) or "No identificado"
        info["hilos"] = psutil.cpu_count(logical=True) or "No identificado"
        freq = psutil.cpu_freq()
        if freq:
            if freq.min: info["frecuencia_base_ghz"] = round(freq.min / 1000, 2)
            if freq.max: info["frecuencia_max_ghz"] = round(freq.max / 1000, 2)
    except Exception:
        pass

    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            info["nombre"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    except Exception:
        out = _run_cmd("wmic cpu get name")
        lines = [line.strip() for line in out.split('\n') if line.strip()]
        if len(lines) > 1:
            info["nombre"] = lines[1]
        else:
            info["nombre"] = platform.processor() or "No identificado"
    return info

def get_ram_info():
    info = {
        "total_gb": "No identificado",
        "usada_gb": "No identificado",
        "libre_gb": "No identificado",
        "porcentaje_uso": "No identificado",
        "tipo": "No identificado",
        "slots_totales": "No identificado",
        "slots_en_uso": "No identificado",
        "slots_libres": "No identificado",
        "modulos": [],
    }
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["total_gb"] = round(mem.total / (1024 ** 3), 2)
        info["usada_gb"] = round(mem.used / (1024 ** 3), 2)
        info["libre_gb"] = round(mem.available / (1024 ** 3), 2)
        info["porcentaje_uso"] = mem.percent
    except Exception:
        out = _run_cmd("wmic computersystem get TotalPhysicalMemory")
        lines = [line.strip() for line in out.split('\n') if line.strip()]
        if len(lines) > 1 and lines[1].isdigit():
            info["total_gb"] = round(int(lines[1]) / (1024 ** 3), 2)

    try:
        out = _run_cmd("wmic memorychip get capacity, speed, manufacturer, devicelocator, memorytype, smbiosmemorytype")
        lines = [line.strip() for line in out.split('\n') if line.strip()]
        if len(lines) > 1:
            for line in lines[1:]:
                parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
                modulo = {
                    "slot": "Desconocido",
                    "capacidad_gb": "No identificado",
                    "tipo": "No identificado",
                    "velocidad_mhz": "No identificado",
                    "fabricante": "No identificado"
                }
                if parts:
                    try: modulo["capacidad_gb"] = round(int(parts[0]) / (1024 ** 3), 1)
                    except: pass
                    if len(parts) > 1: modulo["slot"] = parts[1]
                    if len(parts) > 2: modulo["fabricante"] = parts[2]
                    
                    modulo["tipo"] = "RAM"
                    for p in parts:
                        if p.isdigit() and int(p) in [20, 21, 24, 26, 37]:
                            tipo_map = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 37: "DDR5"}
                            modulo["tipo"] = tipo_map.get(int(p), "RAM")
                        elif p.isdigit() and 1000 <= int(p) <= 10000:
                            modulo["velocidad_mhz"] = p

                info["modulos"].append(modulo)
                
            info["slots_en_uso"] = len(info["modulos"])
            info["tipo"] = info["modulos"][0]["tipo"] if info["modulos"] else "No identificado"
    except Exception:
        pass
    return info

def get_storage_info():
    info = {"discos_fisicos": [], "particiones": []}
    try:
        out = _run_cmd('powershell "Get-PhysicalDisk | Select-Object Model, MediaType, Size, BusType | ConvertTo-Json"')
        if out:
            disks = json.loads(out)
            if isinstance(disks, dict): disks = [disks]
            for d in disks:
                size = round(d.get("Size", 0) / (1024 ** 3), 1) if d.get("Size") else "No identificado"
                tipo = d.get("MediaType", "No identificado")
                bus = d.get("BusType", "")
                if str(bus).upper() == "NVME": tipo = "NVMe SSD"
                info["discos_fisicos"].append({
                    "modelo": d.get("Model", "No identificado"),
                    "tipo": tipo,
                    "interfaz": bus,
                    "capacidad_gb": size
                })
        else:
            out = _run_cmd("wmic diskdrive get model, size, interfacetype")
            lines = [line.strip() for line in out.split('\n') if line.strip()]
            if len(lines) > 1:
                for line in lines[1:]:
                    parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
                    if len(parts) >= 2:
                        modelo = parts[0]
                        interfaz = parts[1] if len(parts) > 2 else "No identificado"
                        try: size = round(int(parts[-1]) / (1024 ** 3), 1)
                        except: size = "No identificado"
                        tipo = "SSD" if "SSD" in modelo.upper() else ("NVMe" if "NVME" in modelo.upper() else "No identificado")
                        info["discos_fisicos"].append({
                            "modelo": modelo,
                            "tipo": tipo,
                            "interfaz": interfaz,
                            "capacidad_gb": size
                        })
    except Exception:
        pass

    try:
        import psutil
        for part in psutil.disk_partitions(all=False):
            try:
                uso = psutil.disk_usage(part.mountpoint)
                info["particiones"].append({
                    "unidad": part.mountpoint,
                    "sistema_archivos": part.fstype,
                    "total_gb": round(uso.total / (1024 ** 3), 1),
                    "usado_gb": round(uso.used / (1024 ** 3), 1),
                    "libre_gb": round(uso.free / (1024 ** 3), 1),
                    "porcentaje": uso.percent,
                })
            except PermissionError:
                continue
    except Exception:
        pass
    return info

def get_gpu_info():
    gpus = []
    out = _run_cmd('powershell "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, Status | ConvertTo-Json"')
    if out:
        try:
            data = json.loads(out)
            if isinstance(data, dict): data = [data]
            for gpu in data:
                ram = gpu.get("AdapterRAM", 0)
                vram_gb = round(ram / (1024 ** 3), 1) if ram else "No identificado"
                res_h = gpu.get("CurrentHorizontalResolution", "?")
                res_v = gpu.get("CurrentVerticalResolution", "?")
                gpus.append({
                    "nombre": gpu.get("Name", "No identificado"),
                    "vram_gb": vram_gb,
                    "driver_version": gpu.get("DriverVersion", "No identificado"),
                    "resolucion": f"{res_h}x{res_v}" if res_h and res_h != "?" else "No identificado",
                    "refresh_hz": gpu.get("CurrentRefreshRate", "No identificado"),
                    "estado": gpu.get("Status", "No identificado")
                })
            return gpus
        except:
            pass

    out = _run_cmd('wmic path win32_VideoController get name, DriverVersion, AdapterRAM')
    lines = [line.strip() for line in out.split('\n') if line.strip()]
    if len(lines) > 1:
        for line in lines[1:]:
            parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
            if parts:
                ram = "No identificado"
                try: ram = round(int(parts[0]) / (1024 ** 3), 1)
                except: pass
                gpus.append({
                    "nombre": parts[-1] if len(parts) > 1 else parts[0],
                    "vram_gb": ram,
                    "driver_version": parts[1] if len(parts) > 2 else "No identificado",
                    "resolucion": "No identificado",
                    "refresh_hz": "No identificado",
                    "estado": "No identificado"
                })

    return gpus if gpus else [{"nombre": "No detectada", "vram_gb": "No identificado", "driver_version": "No identificado", "resolucion": "No identificado", "refresh_hz": "No identificado", "estado": "No identificado"}]

def _get_windows_edition():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            try: edition_id = winreg.QueryValueEx(k, "EditionID")[0]
            except: edition_id = ""
            try: product_name = winreg.QueryValueEx(k, "ProductName")[0]
            except: product_name = ""
            
            edition_map = {
                "Enterprise": "Windows Enterprise", "EnterpriseS": "Windows Enterprise LTSC",
                "Professional": "Windows Pro", "ProfessionalN": "Windows Pro N",
                "Education": "Windows Education", "Home": "Windows Home",
                "HomeN": "Windows Home N", "Core": "Windows Home",
                "CoreN": "Windows Home N", "ServerStandard": "Windows Server Standard",
                "ServerDatacenter": "Windows Server Datacenter",
            }
            return edition_map.get(edition_id) or product_name or edition_id or "No identificado"
    except Exception:
        return "No identificado"

def get_network_info():
    info = {
        "nombre_equipo": "No identificado",
        "adaptadores": [],
    }
    try:
        info["nombre_equipo"] = socket.gethostname()
    except:
        info["nombre_equipo"] = platform.node()

    try:
        import psutil
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        for iface_name, addrs in net_if_addrs.items():
            if iface_name in net_if_stats and net_if_stats[iface_name].isup:
                mac = "No identificado"
                ip = []
                for addr in addrs:
                    if addr.family == socket.AF_INET and str(addr.address) != '127.0.0.1':
                        ip.append(str(addr.address))
                    elif addr.family == psutil.AF_LINK:
                        mac = str(addr.address)
                
                if ip:
                    info["adaptadores"].append({
                        "descripcion": iface_name,
                        "mac": mac,
                        "ip": ", ".join(ip)
                    })
    except Exception:
        pass

    if not info["adaptadores"]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()
            info["adaptadores"].append({
                "descripcion": "Adaptador principal",
                "mac": "No disponible",
                "ip": ip_local,
            })
        except:
            pass

    return info

def get_serial_number():
    out = _run_cmd('powershell "(Get-CimInstance Win32_BIOS).SerialNumber"')
    if out and "No identificado" not in out and "Error" not in out:
        return out.strip()
        
    out = _run_cmd("wmic bios get serialnumber")
    lines = [line.strip() for line in out.split('\n') if line.strip()]
    if len(lines) > 1 and lines[1] != "":
        return lines[1]
    
    return "No identificado"

def get_all_info():
    return {
        "cpu":     get_cpu_info(),
        "ram":     get_ram_info(),
        "storage": get_storage_info(),
        "gpu":     get_gpu_info(),
        "network": get_network_info(),
        "serial":  get_serial_number(),
        "os": {
            "nombre":       platform.system(),
            "edicion":      _get_windows_edition(),
            "version":      platform.version(),
            "release":      platform.release(),
            "arquitectura": platform.machine(),
        }
    }
