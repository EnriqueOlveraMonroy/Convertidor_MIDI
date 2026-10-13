# Audio a MIDI

[![Abrir en Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://www.kaggle.com/notebooks/welcome?src=https://github.com/EnriqueOlveraMonroy/Convertidor_MIDI/blob/main/Cancion_a_MIDI_Kaggle.ipynb)

Transcripción de canciones a MIDI con pistas separadas por instrumento.

Este proyecto convierte una grabación de audio en una representación musical editable. A partir de una canción, utiliza MuScriptor para estimar las notas y los instrumentos presentes y organizarlos en archivos MIDI que pueden abrirse en un DAW o editor musical.

Nace como una herramienta de uso personal para explorar arreglos, estudiar partes instrumentales y obtener un punto de partida para trabajar con una canción en formato MIDI.

## Qué ofrece

- **Transcripción de varios instrumentos:** notas agrupadas según el instrumento que identifica el modelo.
- **MIDI completo:** un archivo tipo 1 con las pistas de los instrumentos detectados.
- **Archivos individuales:** un MIDI por instrumento, conservando el mismo origen temporal que el archivo completo.
- **Procesamiento de fragmentos o canciones completas:** permite trabajar con una sección concreta o con toda la grabación.
- **Informe de conversión:** incluye instrumentos detectados, número de notas, duración del audio y tiempo de procesamiento.
- **Resultados en ZIP:** reúne los MIDI y el informe en una sola descarga desde el notebook.

## Cómo funciona

El audio se decodifica y adapta al formato de entrada del modelo. MuScriptor analiza la grabación y produce eventos musicales con información sobre notas, tiempos e instrumentos. El conversor transforma esos eventos en pistas MIDI y genera los archivos individuales.

El procesamiento se realiza en el equipo o en la sesión de Kaggle que ejecuta el proyecto. Hugging Face proporciona los pesos del modelo y gestiona el acceso a su descarga.

La batería se exporta en el canal MIDI 10. Por defecto, los archivos utilizan una referencia de 120 BPM para conservar el tiempo original de las notas; ese valor no representa una medición del tempo de la canción. Las notas se exportan sin cuantizar.

## GitHub y Kaggle

GitHub alberga el código, el notebook y la documentación del proyecto. Kaggle proporciona un entorno de ejecución con GPU para realizar conversiones a demanda desde el navegador.

El notebook incluye el código necesario para la conversión y presenta el proceso en bloques, desde la preparación del entorno hasta la descarga de los resultados. También existe una versión de ejecución local en Python, con scripts para Windows.

El repositorio contiene código y documentación. Las canciones, las credenciales y los pesos del modelo se mantienen fuera de sus archivos.

## Estado del proyecto

La conversión ya se ha ejecutado con éxito tanto en una GPU local como en Kaggle. El proyecto cuenta con comprobaciones de decodificación de audio, exportación MIDI, sincronización de archivos individuales y empaquetado de resultados.

Actualmente está disponible como programa de Python y notebook de Kaggle. Una interfaz web propia forma parte de la evolución prevista del proyecto.

## Alcance de la transcripción

Las notas y las etiquetas de instrumentos son predicciones y pueden necesitar correcciones. Dos intérpretes del mismo instrumento pueden quedar agrupados en una sola pista.

La separación se realiza sobre la representación MIDI. El proyecto no genera grabaciones de audio aisladas de cada instrumento. Su objetivo es ofrecer material editable para análisis y producción musical, con resultados que deben revisarse al escuchar la transcripción.

## Tecnologías y créditos

El proyecto utiliza Python, PyTorch, FFmpeg y Mido, con **MuScriptor 0.3.0** como modelo de transcripción.

[MuScriptor](https://github.com/muscriptor/muscriptor) fue desarrollado por **Kyutai y Mirelo**. Su código se distribuye bajo licencia MIT y sus pesos bajo CC BY-NC 4.0, para uso no comercial. Los pesos no se incluyen en este repositorio.

La documentación de uso está disponible en [la guía de Kaggle](GUIA_KAGGLE.md) y [la guía de GitHub](GUIA_GITHUB.md).
