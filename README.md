
# 🛠️ ProtoDeus Boost — Windows Optimizer & Diagnostics

**ProtoDeus Boost** es una aplicación de escritorio *premium* para Windows diseñada específicamente para el **diagnóstico avanzado de hardware** y la **optimización profunda del sistema**.

Construida con una interfaz gráfica moderna en **Python + CustomTkinter**, la herramienta se empaqueta en un **único archivo ejecutable (`.exe`)** auto-elevado con **privilegios de administrador (UAC)** para garantizar un control total y directo sobre el rendimiento de tu PC.

---

## 🎨 Diseño & Identidad Visual

* **Tema Premium:** Modo oscuro (*Dark Mode*) nativo con acentos vibrantes en **violeta** y **cyan** (`#7C3AED` / `#06B6D4`).
* **Navegación Fluida:** Interfaz estructurada mediante una **sidebar izquierda estática** y un **panel dinámico de contenido** a la derecha.
* **Feedback en Tiempo Real:** Animaciones de transición suaves, **barras de progreso dinámicas** para las tareas de limpieza y **logs detallados** de ejecución instantáneos.

---

## 🧩 Módulos y Funcionalidades

### 1. 🖥️ Información del PC (`info_pc.py`)

Mapeo exhaustivo de hardware en tiempo real utilizando consultas de bajo nivel a través de las librerías `WMI`, `psutil`, `GPUtil` y `py-cpuinfo`:

* **Procesador (CPU):** Modelo exacto, núcleos/hilos, frecuencias (base/máxima) y **porcentaje de uso en tiempo real**.
* **Memoria RAM:** Estado detallado (total, usada, libre), cantidad de **slots ocupados** y tipo de tecnología exacta (**DDR3, DDR4, DDR5, LPDDR**).
* **Almacenamiento:** Identificación precisa de componentes (**SSD, M.2 NVMe, HDD**) y cálculo de espacio disponible por unidad.
* **Gráficos (GPU):** Nombre exacto de la tarjeta, cantidad de **VRAM instalada**, versión del driver actual y resolución de pantalla activa.

### 2. ⚡ Suite de Optimización (`optimizer.py`)

Mantenimiento profundo mediante comandos nativos del sistema y **manipulación segura del registro** de Windows:

* 🧹 **Limpieza del Sistema:** Vaciado de directorios temporales (`%TEMP%`, `Windows\Temp`, `Prefetch`), vaciado de papelera de reciclaje y eliminación de cachés críticas (miniaturas y fuentes).
* 🌐 **Limpieza de Navegadores:** Remoción selectiva de archivos basura acumulados en **Chrome, Edge, Firefox y Brave**.
* ⚙️ **Optimización de Registro & S.O.:** Depuración de claves huérfanas y reparación/saneamiento de la imagen del sistema a través de herramientas como `DISM`.
* 💾 **Mantenimiento de Unidades:** Invocación del comando **TRIM nativo** para la optimización de **SSDs** y procesos de desfragmentación inteligente para **HDDs**.
* 📉 **Gestión de RAM:** Optimización del consumo en segundo plano deshabilitando de forma segura servicios heredados de telemetría y precarga como **`SysMain` / `Superfetch**`.
* 🚀 **Red y DNS:** Optimización avanzada de parámetros TCP/IP y vaciado inmediato de la caché DNS (`ipconfig /flushdns`).

### 3. 🔧 Herramientas de Diagnóstico (`tools.py`)

* 🌀 **Restablecimiento de Red:** Solución rápida a problemas de conectividad mediante la reinstalación de la pila TCP/IP y la renovación de la interfaz de red:
```cmd
netsh winsock reset && netsh int ip reset && ipconfig /flushdns

```


* 🔑 **Auditoría de Licencias (Estilo ShowKeysPlus):** Extracción directa de la clave de producto activa, claves OEM incrustadas en la placa base (**ACPI MSDM**) e identificación del canal de licenciamiento legítimo (**OEM, KMS, COA, Retail**).

---

## 📁 Estructura del Repositorio

```text
ProtoDeus Boost/
├── main.py              # Punto de entrada de la app, GUI principal y bypass de UAC
├── info_pc.py           # Recolección y formateo de métricas de hardware
├── optimizer.py         # Lógica interna y ejecución de subprocesos de optimización
├── tools.py             # Herramientas de red y recuperación de claves de activación
├── assets/
│   └── icon.ico         # Identidad visual e icono incrustado del ejecutable
├── requirements.txt     # Dependencias de Python necesarias para el entorno
└── build.bat            # Script automatizado para compilación local con PyInstaller

```

---

## 🛠️ Instalación y Compilación (Desarrolladores)

Si deseas clonar el proyecto para modificarlo o compilarlo de forma independiente por tu cuenta, sigue estos pasos:

1. **Clonar el repositorio:**
```bash
git clone https://github.com/tu-usuario/ProtoDeus-Boost.git
cd ProtoDeus-Boost

```


2. **Instalar el entorno de dependencias:**
```bash
pip install -r requirements.txt

```


3. **Compilar a un único archivo `.exe`:**
Puedes utilizar el script automatizado `build.bat` o ejecutar directamente el comando de `PyInstaller` con los flags de elevación administrativa incluidos de fábrica:
```bash
pyinstaller --onefile --noconsole --uac-admin --icon=assets/icon.ico main.py

```



> 📦 **Resultado:** El binario final optimizado se guardará de forma automática en la carpeta `dist/`. Es completamente autónomo y está listo para usarse en cualquier máquina Windows sin necesidad de tener Python instalado.

---

## 🛑 Requisitos de Ejecución

* **Sistema Operativo:** Windows 10 o Windows 11 (Solo arquitecturas de **64 bits**).
* **Privilegios Requeridos:** Requiere la confirmación explícita de la ventana de **Control de Cuentas de Usuario (UAC)** al iniciar. La elevación a **Administrador** es estrictamente mandatoria para poder interactuar con los servicios del sistema, modificar parámetros del registro y resetear los sockets de red.

---

> ⚠️ **Aviso de Seguridad:** *ProtoDeus Boost interactúa con configuraciones sensibles a bajo nivel del sistema operativo. Se recomienda guardar cualquier trabajo abierto antes de ejecutar las tareas de limpieza profunda o restablecimiento de interfaces.*
