# =============================================================================
#  performance.py — Módulo de Monitoreo de Rendimiento y Gestión de Procesos
#  ProtoDeus Boost 3.0
#  Métricas en tiempo real de CPU, RAM, Disco, Red y control de procesos pesados.
# =============================================================================

import time
import psutil

# Cache de mediciones de red previas para calcular velocidad (delta bytes / seg)
_last_net_time = None
_last_net_bytes_sent = None
_last_net_bytes_recv = None

# Procesos críticos de Windows que nunca deben cerrarse para evitar inestabilidad o BSOD
PROTECTED_PROCESSES = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "fontdrvhost.exe",
    "svchost.exe",
    "dwminit.exe",
}


def get_performance_snapshot():
    """
    Retorna una instantánea rápida y no bloqueante del estado del sistema:
    - cpu_pct: porcentaje global de uso de CPU (0-100)
    - cpu_freq: frecuencia actual en GHz
    - cpu_cores: núcleos lógicos y físicos
    - ram: diccionario con total_gb, used_gb, free_gb, percent
    - disks: lista de particiones activas con total, used, free y percent
    - net: velocidades calculadas de subida y bajada (KB/s)
    - proc_count: total de procesos en ejecución
    """
    global _last_net_time, _last_net_bytes_sent, _last_net_bytes_recv

    # CPU (interval=None no bloquea el hilo)
    cpu_pct = psutil.cpu_percent(interval=None)
    freq = psutil.cpu_freq()
    cpu_freq_ghz = round(freq.current / 1000, 2) if freq and freq.current else None

    # RAM
    vmem = psutil.virtual_memory()
    ram_info = {
        "total_gb": round(vmem.total / (1024 ** 3), 1),
        "used_gb": round(vmem.used / (1024 ** 3), 1),
        "free_gb": round(vmem.available / (1024 ** 3), 1),
        "percent": vmem.percent,
    }

    # Discos / Particiones fijas
    disks = []
    for part in psutil.disk_partitions(all=False):
        # Excluir unidades CD-ROM o virtuales vacías
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device.rstrip("\\"),
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 1),
                "used_gb": round(usage.used / (1024 ** 3), 1),
                "free_gb": round(usage.free / (1024 ** 3), 1),
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            continue

    # Red (cálculo de tasa de transferencia)
    net_io = psutil.net_io_counters()
    now = time.time()
    net_up_kbs = 0.0
    net_down_kbs = 0.0

    if _last_net_time and _last_net_bytes_sent is not None:
        dt = max(now - _last_net_time, 0.1)
        net_up_kbs = round((net_io.bytes_sent - _last_net_bytes_sent) / (1024 * dt), 1)
        net_down_kbs = round((net_io.bytes_recv - _last_net_bytes_recv) / (1024 * dt), 1)

    _last_net_time = now
    _last_net_bytes_sent = net_io.bytes_sent
    _last_net_bytes_recv = net_io.bytes_recv

    return {
        "cpu_pct": cpu_pct,
        "cpu_freq_ghz": cpu_freq_ghz,
        "cpu_physical_cores": psutil.cpu_count(logical=False) or 0,
        "cpu_logical_cores": psutil.cpu_count(logical=True) or 0,
        "ram": ram_info,
        "disks": disks,
        "net_up_kbs": max(net_up_kbs, 0.0),
        "net_down_kbs": max(net_down_kbs, 0.0),
        "proc_count": len(psutil.pids()),
    }


def get_processes_list(limit=25):
    """
    Obtiene la lista de procesos ordenada por uso de recursos (CPU y RAM).
    Marca aquellos que tienen 'Alto Consumo' según umbrales recomendados:
    - CPU > 4% o RAM > 250 MB
    Retorna lista de diccionarios:
    [ {pid, name, cpu_percent, ram_mb, is_high, status}, ... ]
    """
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
        try:
            info = p.info
            name = info.get('name') or "Desconocido"
            pid = info.get('pid')
            cpu = info.get('cpu_percent') or 0.0
            mem_info = info.get('memory_info')
            ram_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0

            # Determinar si consume más de lo normal/recomendado
            is_high = (cpu >= 4.0 or ram_mb >= 250.0)
            is_protected = name.lower() in PROTECTED_PROCESSES

            procs.append({
                "pid": pid,
                "name": name,
                "cpu_percent": round(cpu, 1),
                "ram_mb": ram_mb,
                "is_high": is_high,
                "is_protected": is_protected,
                "status": info.get('status') or "running",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Ordenar primero los de mayor CPU, y luego mayor RAM
    procs.sort(key=lambda x: (x["cpu_percent"] * 10 + x["ram_mb"] / 10), reverse=True)
    return procs[:limit]


def kill_process_by_pid(pid):
    """
    Finaliza un proceso por su PID con validación de seguridad.
    Retorna (éxito: bool, mensaje: str).
    """
    try:
        proc = psutil.Process(pid)
        name = proc.name().lower()

        if name in PROTECTED_PROCESSES:
            return False, f"El proceso '{name}' es crítico para Windows y no puede ser finalizado."

        proc.terminate()
        # Esperar brevemente para confirmar
        try:
            proc.wait(timeout=1.5)
        except psutil.TimeoutExpired:
            proc.kill()

        return True, f"Proceso '{name}' (PID: {pid}) finalizado con éxito."
    except psutil.NoSuchProcess:
        return True, f"El proceso (PID: {pid}) ya no se encuentra en ejecución."
    except psutil.AccessDenied:
        return False, f"Acceso denegado al finalizar PID {pid}. Ejecuta ProtoDeus como Administrador."
    except Exception as e:
        return False, f"No se pudo finalizar el proceso: {e}"
