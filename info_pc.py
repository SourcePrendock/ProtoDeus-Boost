import subprocess
import platform
import re


def get_cpu_info():
    try:
        import psutil
        import wmi
        c = wmi.WMI()
        cpu_wmi = c.Win32_Processor()[0]
        freq = psutil.cpu_freq()
        return {
            "nombre": cpu_wmi.Name.strip() if cpu_wmi.Name else "No identificado",
            "nucleos_fisicos": psutil.cpu_count(logical=False),
            "hilos": psutil.cpu_count(logical=True),
            "frecuencia_base_ghz": round(freq.min / 1000, 2) if freq and freq.min else "No identificado",
            "frecuencia_max_ghz": round(freq.max / 1000, 2) if freq and freq.max else "No identificado",
            "arquitectura": platform.machine(),
        }
    except Exception as e:
        return {"error": str(e)}


def get_ram_info():
    try:
        import psutil
        import wmi
        c = wmi.WMI()
        mem_total = psutil.virtual_memory()
        slots_total = 0
        slots_en_uso = 0
        tipo_ram = "No identificado"
        modulos = []

        memory_type_map = {
            0: "No identificado", 1: "Otro", 2: "DRAM", 3: "Synchronous DRAM",
            4: "Cache DRAM", 5: "EDO", 6: "EDRAM", 7: "VRAM", 8: "SRAM",
            9: "RAM", 10: "ROM", 11: "Flash", 12: "EEPROM", 13: "FEPROM",
            14: "EPROM", 15: "CDRAM", 16: "3DRAM", 17: "SDRAM", 18: "SGRAM",
            19: "RDRAM", 20: "DDR", 21: "DDR2", 22: "DDR2 FB-DIMM", 24: "DDR3",
            26: "DDR4", 30: "LPDDR", 31: "LPDDR2", 32: "LPDDR3", 33: "LPDDR4",
            34: "Logical non-volatile", 35: "HBM", 36: "HBM2", 37: "DDR5", 38: "LPDDR5",
        }

        for arr in c.Win32_PhysicalMemoryArray():
            slots_total += int(arr.MemoryDevices or 0)

        for mem in c.Win32_PhysicalMemory():
            tipo_num = int(mem.SMBIOSMemoryType or 0)
            tipo_str = memory_type_map.get(tipo_num, f"Tipo {tipo_num}")
            cap_gb = round(int(mem.Capacity or 0) / (1024 ** 3), 1)
            modulos.append({
                "slot": mem.DeviceLocator or "Slot desconocido",
                "capacidad_gb": cap_gb,
                "tipo": tipo_str,
                "velocidad_mhz": mem.Speed or "No identificado",
                "fabricante": mem.Manufacturer or "No identificado",
            })
            slots_en_uso += 1
            tipo_ram = tipo_str

        return {
            "total_gb": round(mem_total.total / (1024 ** 3), 2),
            "usada_gb": round(mem_total.used / (1024 ** 3), 2),
            "libre_gb": round(mem_total.available / (1024 ** 3), 2),
            "porcentaje_uso": mem_total.percent,
            "tipo": tipo_ram,
            "slots_totales": slots_total,
            "slots_en_uso": slots_en_uso,
            "slots_libres": slots_total - slots_en_uso,
            "modulos": modulos,
        }
    except Exception as e:
        return {"error": str(e)}


def get_storage_info():
    try:
        import psutil
        import wmi
        c = wmi.WMI()

        discos_fisicos = {}
        for disk in c.Win32_DiskDrive():
            modelo = disk.Model or "No identificado"
            size_gb = round(int(disk.Size or 0) / (1024 ** 3), 1)
            bus = (disk.InterfaceType or "").upper()
            m_upper = modelo.upper()

            if "NVME" in m_upper or "NVME" in bus:
                tipo = "NVMe SSD"
            elif "M.2" in m_upper:
                tipo = "M.2 SSD"
            elif "SSD" in m_upper:
                tipo = "SSD"
            elif "HDD" in m_upper:
                tipo = "HDD"
            else:
                tipo = "No identificado"

            discos_fisicos[disk.DeviceID] = {
                "modelo": modelo, "tipo": tipo,
                "interfaz": bus or "No identificado",
                "capacidad_gb": size_gb,
            }

        particiones = []
        for part in psutil.disk_partitions(all=False):
            try:
                uso = psutil.disk_usage(part.mountpoint)
                particiones.append({
                    "unidad": part.mountpoint,
                    "sistema_archivos": part.fstype,
                    "total_gb": round(uso.total / (1024 ** 3), 1),
                    "usado_gb": round(uso.used / (1024 ** 3), 1),
                    "libre_gb": round(uso.free / (1024 ** 3), 1),
                    "porcentaje": uso.percent,
                })
            except PermissionError:
                continue

        return {"discos_fisicos": list(discos_fisicos.values()), "particiones": particiones}
    except Exception as e:
        return {"error": str(e)}


def get_gpu_info():
    try:
        import wmi
        c = wmi.WMI()
        gpus = []
        for gpu in c.Win32_VideoController():
            vram_bytes = int(gpu.AdapterRAM or 0)
            vram_gb = round(vram_bytes / (1024 ** 3), 1)
            gpus.append({
                "nombre": gpu.Name or "No identificado",
                "vram_gb": vram_gb if vram_gb > 0 else "No identificado",
                "driver_version": gpu.DriverVersion or "No identificado",
                "resolucion": f"{gpu.CurrentHorizontalResolution or '?'}x{gpu.CurrentVerticalResolution or '?'}",
                "refresh_hz": gpu.CurrentRefreshRate or "No identificado",
                "estado": gpu.Status or "No identificado",
            })
        return gpus if gpus else [{"nombre": "No detectada", "vram_gb": "No identificado"}]
    except Exception as e:
        return [{"error": str(e)}]


def _get_windows_edition():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            edition_id = ""
            product_name = ""
            try:
                edition_id = winreg.QueryValueEx(k, "EditionID")[0]
            except Exception:
                pass
            try:
                product_name = winreg.QueryValueEx(k, "ProductName")[0]
            except Exception:
                pass
            edition_map = {
                "Enterprise":          "Windows Enterprise",
                "EnterpriseS":         "Windows Enterprise LTSC",
                "EnterpriseSEval":     "Windows Enterprise LTSC (Eval)",
                "EnterpriseG":         "Windows Enterprise G",
                "Professional":        "Windows Pro",
                "ProfessionalN":       "Windows Pro N",
                "ProfessionalEducation": "Windows Pro Education",
                "Education":           "Windows Education",
                "Home":                "Windows Home",
                "HomeN":               "Windows Home N",
                "HomeSingleLanguage":  "Windows Home Single Language",
                "Core":                "Windows Home",
                "CoreN":               "Windows Home N",
                "CoreSingleLanguage":  "Windows Home Single Language",
                "IoTEnterprise":       "Windows IoT Enterprise",
                "ServerStandard":      "Windows Server Standard",
                "ServerDatacenter":    "Windows Server Datacenter",
            }
            if edition_id in edition_map:
                return edition_map[edition_id]
            if product_name:
                return product_name
            return edition_id or "No identificado"
    except Exception:
        return "No identificado"


def get_all_info():
    return {
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "storage": get_storage_info(),
        "gpu": get_gpu_info(),
        "os": {
            "nombre": platform.system(),
            "edicion": _get_windows_edition(),
            "version": platform.version(),
            "release": platform.release(),
            "arquitectura": platform.machine(),
        }
    }
