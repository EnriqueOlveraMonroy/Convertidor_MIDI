# Canción a MIDI en Kaggle

## Qué subir

Importa **Cancion_a_MIDI_Kaggle.ipynb**. El notebook ya contiene todo el código necesario. No tienes que subir `audio_a_midi.py`, `kaggle_runtime.py` ni instalar los scripts de Windows.

El repositorio incluye `kaggle_runtime.py` y `audio_a_midi.py` como código editable. **Descomprime el paquete antes de importar el archivo .ipynb.** No subas la carpeta `.venv`, `.cache` ni credenciales de tu equipo.

## 1. Crear e importar el notebook

1. Entra en [Kaggle](https://www.kaggle.com/) con tu cuenta.
2. Crea un notebook desde **Create → New Notebook**.
3. En el editor, usa **File → Import Notebook** y selecciona `Cancion_a_MIDI_Kaggle.ipynb` desde tu computadora. Los nombres de los menús pueden variar.
4. Comprueba que la visibilidad del notebook sea **Private**.
5. En las opciones de sesión, selecciona **Accelerator → GPU T4 x2** si está disponible, y activa **Internet**. El conversor utiliza una de las dos GPU; la segunda no duplica automáticamente la velocidad. También puedes probar P100; el notebook verifica el cálculo CUDA antes de descargar pesos y se detiene si no es compatible.
6. Si Kaggle exige verificación de tu cuenta para habilitar GPU o Internet, complétala en su página.

## 2. Añadir la canción

Desde **Add Input / Add Data → Upload**, crea un dataset **privado** con tu MP3, WAV, FLAC, M4A u otro audio compatible. Si esa opción no aparece, crea el dataset desde **Create → New Dataset**, elige **Private** y después añádelo al notebook con **Add Input**.

Selecciona tu canción en el diálogo de tu PC, por ejemplo:

```text
C:\Musica\cancion.mp3
```

Esa ruta sirve para seleccionar el archivo al subirlo. Dentro del notebook debes usar una ruta de Kaggle, que empieza por `/kaggle/input/`. Con una sola canción adjunta el notebook la encuentra automáticamente. Si adjuntas varias, te mostrará las rutas para elegir una.

El notebook y el dataset tienen visibilidades independientes: comprueba que **ambos** sean privados.

## 3. Dar acceso a Hugging Face

Ya aceptaste la licencia de [MuScriptor Medium](https://huggingface.co/MuScriptor/muscriptor-medium), por lo que no debes repetirlo si usas la misma cuenta.

1. En [Hugging Face → Settings → Access Tokens](https://huggingface.co/settings/tokens), crea un token de **lectura**. Si eliges permisos específicos, habilita el acceso al modelo autorizado.
2. En Kaggle abre **Add-ons → Secrets**.
3. Añade un secreto llamado exactamente **HF_TOKEN** y pega allí el token.
4. Habilita ese secreto para este notebook.

No pegues el token en el código, en archivos de entrada ni en el chat. El notebook lo lee desde Secrets, lo pasa al proceso de conversión en memoria y no ejecuta un login que lo guarde en disco. Tu sesión de Hugging Face en Windows no se transfiere a Kaggle.

## 4. Ejecutar

Ejecuta los bloques en este orden:

1. **Preparar archivos y dependencias:** comprueba CUDA y crea un entorno aislado aprovechando el PyTorch de Kaggle. No reinstala el paquete CUDA de Windows. Si la instalación informa de un conflicto, conserva el mensaje para revisarlo; no fuerces actualizar PyTorch.
2. **Conectar Hugging Face:** verifica el token sin mostrarlo. El acceso al modelo se comprueba al descargar los pesos durante la conversión.
3. **Elegir la canción:** deja `ARCHIVO_AUDIO = ""` si solo has adjuntado una canción. Usa `MODELO = "medium"`.
4. **Probar 30 segundos:** espera a que aparezca el enlace al ZIP y revisa el MIDI.
5. **Convertir la canción completa:** cambia `CONVERTIR_COMPLETA = False` a `CONVERTIR_COMPLETA = True` y ejecuta **solo ese bloque**.

La primera ejecución descarga los pesos. Una nueva sesión puede necesitar instalar y descargar de nuevo. La conversión se realiza en la GPU de Kaggle; no requiere tener encendida tu GPU local.

## 5. Descargar y terminar

El ZIP de cada conversión incluye:

- `cancion.mid`: MIDI tipo 1 con todas las pistas.
- `instrumentos/*.mid`: un MIDI independiente por instrumento detectado.
- `informe.json`: duración, tiempo de procesamiento e instrumentos.
- `LEEME.txt`: notas de uso y atribución.

El ZIP no incluye el audio original, los pesos, dependencias ni credenciales. Cada ejecución crea una carpeta distinta, sin sobrescribir conversiones anteriores.

Pulsa el enlace de descarga que muestra el notebook. Si Kaggle no permite descargar desde ese enlace, busca el ZIP en **Output / Files → audio-a-midi → resultados**. Descárgalo antes de detener la sesión.

Para conservar el código, usa **Quick Save**. **Save & Run All** vuelve a procesar y consume cuota. Finalmente pulsa **Stop Session** y comprueba que no queden sesiones activas; cerrar la pestaña no garantiza detenerlas.

## Cuota y limitaciones

La documentación de Kaggle indica una cuota semanal de unas **30 horas**, que puede variar, y su documentación de Notebooks indica hasta **12 horas por sesión**. Comprueba siempre el saldo y las opciones que muestre tu cuenta. Hay disponibilidad limitada y posibles colas; esta entrega no garantiza el acceso a una GPU.

Se descuenta tiempo mientras la sesión con GPU está activa, no según la duración de la canción. Las cachés se guardan en `/kaggle/temp/audio-midi-runtime`, fuera de los resultados descargables; son temporales.

El código original se probó en una RTX 4050 con una canción real. Para esta entrega se validó el formato Jupyter, pasaron cinco comprobaciones de selección de audio y empaquetado, y se ejecutaron las celdas de conversión y descarga con 30 segundos de la canción de demostración de MuScriptor en la GPU local: generaron tres pistas y un ZIP válido. **El usuario confirmó el 13 de octubre de 2026 que ejecutó el notebook correctamente en Kaggle.** La comprobación inicial de GPU detecta errores de compatibilidad antes de cargar el modelo. No podemos prometer que Kaggle tarde lo mismo que tu computadora.

Los 120 BPM del MIDI son una referencia técnica para conservar los tiempos originales, no una medición del tempo. Las notas no están cuantizadas. La separación y las notas son predicciones; dos intérpretes del mismo instrumento pueden quedar juntos. No se generan stems de audio.

MuScriptor: [Kyutai y Mirelo](https://github.com/muscriptor/muscriptor). Código MIT; pesos CC BY-NC 4.0 para uso no comercial.

Fuentes consultadas el 13 de octubre de 2026: [Kaggle Notebooks](https://www.kaggle.com/docs/notebooks), [cuota y uso de GPU](https://www.kaggle.com/docs/efficient-gpu-usage), [Secrets de Kaggle](https://www.kaggle.com/product-feedback/114053).
