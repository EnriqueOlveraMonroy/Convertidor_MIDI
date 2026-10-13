# Guardar en GitHub y ejecutar en Kaggle

## 1. Subir el proyecto manualmente

1. Descomprime `Proyecto_MIDI_GitHub.zip` en tu computadora.
2. En [GitHub](https://github.com/), crea un repositorio nuevo. Puedes llamarlo `audio-a-midi`; selecciona **Public** para publicar el código y permitir importar el notebook directamente desde su URL. Las canciones pueden seguir en datasets privados de Kaggle y el token, en Secrets.
3. No necesitas añadir otro README: el proyecto ya incluye uno.
4. En el repositorio, usa **Add file → Upload files**; en uno vacío, puede aparecer **uploading an existing file**.
5. Sube el contenido de la carpeta descomprimida. Comprueba que `README.md` y `Cancion_a_MIDI_Kaggle.ipynb` queden en la raíz del repositorio, y que `tools/actualizar_notebook.py` conserve su carpeta.
6. Guarda los archivos con **Commit changes**. Puedes usar el mensaje `Versión inicial: conversor MIDI para Kaggle`.

Sube los archivos descomprimidos, no solamente el ZIP. El paquete está preparado sin canciones, pesos, cachés, resultados ni credenciales. Si el navegador no muestra `.gitignore`, añádelo después desde **Add file → Create new file** con ese nombre y el contenido del archivo incluido.

## 2. Vincular el notebook que ya funciona

Kaggle incluye una integración para guardar versiones del notebook en GitHub, también en repositorios privados:

1. Abre en Kaggle el notebook que ya te funcionó.
2. Selecciona **File → Link to GitHub**.
3. Completa el inicio de sesión y la vinculación de GitHub en los diálogos del servicio.
4. Selecciona el repositorio y el destino que te muestre Kaggle. Si te permite elegir el nombre o ruta del archivo, usa `Cancion_a_MIDI_Kaggle.ipynb` para actualizar el mismo archivo del proyecto.
5. Al guardar una versión, selecciona la opción de guardarla también en GitHub. Utiliza **Quick Save** para guardar sin repetir la conversión cuando esa opción esté disponible. **Save & Run All** vuelve a ejecutar el código.

Esto guarda el notebook; los scripts y guías del proyecto se suben con la carga manual del paso 1. La vinculación no importa automáticamente los futuros cambios de GitHub hacia una sesión abierta de Kaggle. Si el menú no aparece, puedes descargar el notebook y subirlo manualmente.

El token `HF_TOKEN` sigue en Kaggle Secrets. Revisa las salidas del notebook antes de guardarlo en GitHub: las salidas pueden mostrar nombres de canciones y resultados.

Fuente: [anuncio oficial de la integración](https://www.kaggle.com/discussions/product-feedback/295170).

## 3. Volver a ejecutar cuando lo necesites

La opción más rápida es volver a abrir tu notebook que ya funcionó en Kaggle, activar la GPU, cambiar la canción y ejecutar los bloques. El repositorio de GitHub conserva el proyecto y su historial.

Para empezar desde una versión guardada en GitHub:

### Repositorio privado

1. Abre `Cancion_a_MIDI_Kaggle.ipynb` en GitHub con tu sesión iniciada y descarga el archivo con **Download raw file** (o la opción de descarga del archivo).
2. En Kaggle crea un notebook y usa **File → Import Notebook** para seleccionar ese archivo.
3. Comprueba GPU e Internet, añade tu canción privada y habilita `HF_TOKEN` en Secrets.
4. Ejecuta la prueba; después activa la conversión completa si quieres.

### Repositorio público

1. Abre el archivo `.ipynb` en GitHub y copia su URL.
2. En un notebook nuevo de Kaggle usa **Load from URL**, o la opción de URL de **Import Notebook** si aparece en tu editor, y pega el enlace público.
3. Comprueba GPU, Internet, entrada de audio y Secrets antes de ejecutar.

Puedes crear un enlace para el README con este formato, reemplazando los datos de ejemplo:

```text
https://www.kaggle.com/notebooks/welcome?src=https://github.com/TU_USUARIO/TU_REPO/blob/main/Cancion_a_MIDI_Kaggle.ipynb
```

Solo funciona si Kaggle puede leer ese archivo. No publiques el repositorio únicamente para evitar una descarga manual si prefieres mantenerlo privado.

## 4. Actualizaciones

GitHub y Kaggle mantienen copias independientes. Una importación no establece sincronización continua.

- Si cambias el código Python en tu computadora, ejecuta `python tools/actualizar_notebook.py` y sube a GitHub los archivos modificados y el `.ipynb` regenerado. Después importa esa versión en Kaggle.
- Si cambias el notebook en Kaggle y quieres conservar esos cambios, guarda una versión con la opción de enviarla al repositorio vinculado. También puedes descargar el notebook y subirlo manualmente. Revisa las salidas guardadas antes de compartirlo; pueden incluir rutas y resultados de tus canciones. El generador incluido limpia las salidas.
- Si cambias dentro de Kaggle el código incrustado del conversor, refleja esos cambios también en `audio_a_midi.py` o `kaggle_runtime.py` del repositorio antes de regenerar; el generador toma esos archivos como referencia.

El notebook incluido empieza sin salidas y con `CONVERTIR_COMPLETA = False`. Un notebook que descargues de Kaggle puede conservar otros valores; revísalo antes de usar **Run All**.

## 5. Qué se guarda en cada servicio

| Servicio | Contenido |
|---|---|
| GitHub | Código, notebook, guías e historial de cambios. |
| Kaggle | Sesión GPU, canción como dataset privado y resultados de las conversiones. |
| Kaggle Secrets | Tu token `HF_TOKEN`. |
| Hugging Face | Los pesos de MuScriptor que se descargan al preparar la conversión. |

No debes copiar el token al repositorio. Tampoco necesitas subir el modelo a GitHub. El `.gitignore` ayuda al usar Git, pero no impide subir archivos desde la web; selecciona los archivos de este paquete.

## Automatización opcional

Más adelante se puede usar la CLI oficial de Kaggle y un flujo manual de GitHub Actions. Para este uso personal no hace falta configurarlo: el notebook guardado se puede abrir y ejecutar a demanda.

La CLI actual permite descargar código con `kaggle kernels pull` y guardar una versión con `kaggle kernels push --no-run`. Un `push` sin `--no-run` intenta ejecutar el notebook y puede consumir cuota. No se incluye ninguna automatización que inicie GPU al subir cambios.

Fuentes consultadas el 13 de octubre de 2026: [subir archivos a GitHub](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository), [Kaggle: importar desde GitHub](https://www.kaggle.com/product-feedback/221448), [Kaggle: importar desde URL](https://www.kaggle.com/product-feedback/152480), [CLI oficial de Kaggle](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md).
