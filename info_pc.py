"""
info_pc.py — Módulo de información del hardware para ProtoDeus Boost
"""

import subprocess
import platform
import re


def get_cpu_info():
    """Obtiene información del procesador usando WMI y psutil."""
    try:
        import psutil
        import wmi
        c = wmi.WMI()
        cpu_wmi = c.Win32_Processor()[0]
        
        freq = psutil.cpu_freq()
        cpu = {
            "nombre": cpu_wmi.Name.strip() if cpu_wmi.Name else "Desconocido",
            "nucleos_fisicos": psutil.cpu_count(logical=False),
            "hilos": psutil.cpu_count(logical=True),
            "frecuencia_base_ghz": round(freq.min / 1000, 2) if freq and freq.min else "N/A",
            "frecuencia_max_ghz": round(freq.max / 1000, 2) if freq and freq.max else "N/A",
            "arquitectura": platform.machine(),
        }
        return cpu
    except Exception as e:
        return {"error": str(e)}


def get_ram_info():
    """Obtiene información de la RAM incluyendo tipo y slots vía WMI."""
    try:
        import psutil
        import wmi
        c = wmi.WMI()
        mem_total = psutil.virtual_memory()

        slots_total = 0
        slots_en_uso = 0
        tipo_ram = "Desconocido"
        modulos = []

        # Mapa de tipo numérico de WMI a nombre
        memory_type_map = {
            0:  "Desconocido",
            1:  "Otro",
            2:  "DRAM",
            3:  "Synchronous DRAM",
            4:  "Cache DRAM",
            5:  "EDO",
            6:  "EDRAM",
            7:  "VRAM",
            8:  "SRAM",
            9:  "RAM",
            10: "ROM",
            11: "Flash",
            12: "EEPROM",
            13: "FEPROM",
            14: "EPROM",
            15: "CDRAM",
            16: "3DRAM",
            17: "SDRAM",
            18: "SGRAM",
            19: "RDRAM",
            20: "DDR",
            21: "DDR2",
            22: "DDR2 FB-DIMM",
            24: "DDR3",
            26: "DDR4",
            30: "LPDDR",
            31: "LPDDR2",
            32: "LPDDR3",
            33: "LPDDR4",
            34: "Logical non-volatile device",
            35: "HBM",
            36: "HBM2",
            37: "DDR5",
            38: "LPDDR5",
        }

        # Slots totales desde Win32_PhysicalMemoryArray
        for arr in c.Win32_PhysicalMemoryArray():
            slots_total += int(arr.MemoryDevices or 0)

        # Módulos instalados desde Win32_PhysicalMemory
        for mem in c.Win32_PhysicalMemory():
            tipo_num = int(mem.SMBIOSMemoryType or 0)
            tipo_str = memory_type_map.get(tipo_num, f"Tipo {tipo_num}")
            cap_gb = round(int(mem.Capacity or 0) / (1024 ** 3), 1)
            speed_mhz = mem.Speed or "N/A"
            modulos.append({
                "slot": mem.DeviceLocator or "Slot desconocido",
                "capacidad_gb": cap_gb,
                "tipo": tipo_str,
                "velocidad_mhz": speed_mhz,
                "fabricante": mem.Manufacturer or "Desconocido",
            })
            slots_en_uso += 1
            tipo_ram = tipo_str  # Usa el último módulo como referencia

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
    """Obtiene información de almacenamiento con tipo de disco vía WMI."""
    try:
        import psutil
        import wmi
        c = wmi.WMI()

        # Mapa de tipo de disco
        media_type_map = {
            0: "Desconocido",
            3: "HDD",
            4: "SSD",
            5: "SCM",
        }

        discos_fisicos = {}
        for disk in c.Win32_DiskDrive():
            modelo = disk.Model or "Desconocido"
            size_bytes = int(disk.Size or 0)
            size_gb = round(size_bytes / (1024 ** 3), 1)
            media_num = getattr(disk, "MediaType", None)
            bus = (disk.InterfaceType or "").upper()

            # Determinar tipo de disco
            if media_num == 4 or "SSD" in modelo.upper():
                tipo = "SSD"
            elif media_num == 3 or "HDD" in modelo.upper():
                tipo = "HDD"
            else:
                tipo = "Desconocido"

            # Intentar detectar NVMe / M.2 por interfaz o modelo
            if "NVME" in modelo.upper() or "NVME" in bus:
                tipo = "NVMe SSD"
            elif "M.2" in modelo.upper():
                tipo = "M.2 SSD"

            discos_fisicos[disk.DeviceID] = {
                "modelo": modelo,
                "tipo": tipo,
                "interfaz": bus,
                "capacidad_gb": size_gb,
            }

        # Particiones lógicas
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

        return {
            "discos_fisicos": list(discos_fisicos.values()),
            "particiones": particiones,
        }
    except Exception as e:
        return {"error": str(e)}


def get_gpu_info():
    """Obtiene información de la tarjeta gráfica vía WMI."""
    try:
        import wmi
        c = wmi.WMI()
        gpus = []
        for gpu in c.Win32_VideoController():
            vram_bytes = int(gpu.AdapterRAM or 0)
            vram_gb = round(vram_bytes / (1024 ** 3), 1)
            gpus.append({
                "nombre": gpu.Name or "Desconocido",
                "vram_gb": vram_gb if vram_gb > 0 else "N/A",
                "driver_version": gpu.DriverVersion or "Desconocido",
                "resolucion": f"{gpu.CurrentHorizontalResolution or '?'}x{gpu.CurrentVerticalResolution or '?'}",
                "refresh_hz": gpu.CurrentRefreshRate or "N/A",
                "estado": gpu.Status or "N/A",
            })
        return gpus if gpus else [{"nombre": "No detectada", "vram_gb": "N/A"}]
    except Exception as e:
        return [{"error": str(e)}]


def get_all_info():
    """Retorna toda la información del sistema en un solo dict."""
    return {
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "storage": get_storage_info(),
        "gpu": get_gpu_info(),
        "os": {
            "nombre": platform.system(),
            "version": platform.version(),
            "release": platform.release(),
            "arquitectura": platform.machine(),
        }
    }
