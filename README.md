🛠️ ProtoDeus Boost — Windows Optimizer & Diagnostics

ProtoDeus Boost es una aplicación de escritorio premium para Windows diseñada para el diagnóstico avanzado de hardware y la optimización profunda del sistema. Construida con una interfaz gráfica moderna en Python + CustomTkinter, la herramienta se empaqueta en un único archivo ejecutable (.exe) auto-elevado con privilegios de administrador (UAC) para garantizar un control total sobre el rendimiento de tu PC.
🎨 Diseño & Identidad Visual

    Tema Premium: Modo oscuro nativo con acentos vibrantes en violeta y cyan (#7C3AED / #06B6D4).

    Navegación Fluida: Interfaz estructurada mediante una sidebar izquierda estática y un panel dinámico de contenido a la derecha.

    Feedback en Tiempo Real: Animaciones de transición suaves, barras de progreso dinámicas para las tareas de limpieza y logs detallados de ejecución.

🧩 Módulos y Funcionalidades
1. 🖥️ Información del PC (info_pc.py)

Mapeo de hardware en tiempo real utilizando consultas de bajo nivel (WMI, psutil, GPUtil, py-cpuinfo):

    Procesador: Modelo exacto, núcleos/hilos, frecuencias (base/máxima) y porcentaje de uso actual.

    Memoria RAM: Estado de la memoria (total, usada, libre), cantidad de slots ocupados y tipo de tecnología exacta (DDR3, DDR4, DDR5, LPDDR).

    Almacenamiento: Identificación de componentes (SSD, M.2 NVMe, HDD) y espacio disponible por unidad.

    Gráficos: Nombre de la GPU, cantidad de VRAM instalada, versión del driver y resolución de pantalla activa.

2. ⚡ Suite de Optimización (optimizer.py)

Mantenimiento profundo mediante comandos nativos y manipulación segura del registro de Windows:

    🧹 Limpieza del Sistema: Vaciado de directorios temporales (%TEMP%, Windows\Temp, Prefetch), papelera de reciclaje y cachés críticas (miniaturas/fuentes).

    🌐 Limpieza de Navegadores: Remoción de archivos basura acumulados en Chrome, Edge, Firefox y Brave.

    ⚙️ Optimización de Registro & S.O.: Depuración de claves huérfanas y reparación de la imagen del sistema a través de DISM.

    💾 Mantenimiento de Unidades: Comando TRIM nativo para la optimización de SSDs y desfragmentación inteligente para HDDs.

    📉 Gestión de RAM: Optimización del consumo en segundo plano deshabilitando servicios heredados como SysMain / Superfetch.

    🚀 Red y DNS: Optimización de parámetros TCP/IP y vaciado de caché DNS (ipconfig /flushdns).

3. 🔧 Herramientas de Diagnóstico (tools.py)

    🌀 Restablecimiento de Red: Solución rápida a problemas de conectividad mediante la reinstalación de la pila TCP/IP y renovación de la interfaz de red:
    DOS

    netsh winsock reset && netsh int ip reset && ipconfig /flushdns

    🔑 Auditoría de Licencias (Estilo ShowKeysPlus): Extracción directa de la clave de producto activa, claves OEM incrustadas en la placa base (ACPI MSDM) e identificación del canal de licenciamiento (OEM, KMS, COA, Retail).

📁 Estructura del Repositorio
Plaintext

ProtoDeus Boost/
├── main.py              # Punto de entrada de la app, GUI principal y bypass de UAC
├── info_pc.py           # Recolección y formateo de métricas de hardware
├── optimizer.py         # Lógica interna y ejecución de subprocesos de optimización
├── tools.py             # Herramientas de red y recuperación de claves de activación
├── assets/
│   └── icon.ico         # Identidad visual e icono incrustado del ejecutable
├── requirements.txt     # Dependencias de Python necesarias para el entorno
└── build.bat            # Script automatizado para compilación local con PyInstaller

🛠️ Instalación y Compilación (Desarrolladores)

Si deseas clonar el proyecto para modificarlo o compilarlo de forma independiente, sigue estos pasos:

    Clonar el repositorio:
    Bash

    git clone https://github.com/tu-usuario/ProtoDeus-Boost.git
    cd ProtoDeus-Boost

    Instalar el entorno de dependencias:
    Bash

    pip install -r requirements.txt

    Compilar a un único archivo .exe:
    Puedes utilizar el script automatizado build.bat o ejecutar directamente el comando de PyInstaller con los flags de elevación administrativa incluidos:
    Bash

    pyinstaller --onefile --noconsole --uac-admin --icon=assets/icon.ico main.py

El binario final optimizado se guardará en la carpeta dist/, completamente autónomo y listo para usarse en cualquier máquina Windows sin necesidad de dependencias externas.
🛑 Requisitos de Ejecución

    Sistema Operativo: Windows 10 o Windows 11 (64 bits).

    Privilegios: Requiere confirmación de la ventana de Control de Cuentas de Usuario (UAC) al iniciar. La elevación a Administrador es mandatoria para modificar los parámetros del registro de Windows, interactuar con servicios del sistema y resetear los sockets de red.
