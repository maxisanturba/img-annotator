# Img Annotator

Editor de capturas simple para Linux: anotar y recortar, sin nada más. Lo hice para Nobara
(KDE) porque no encontraba algo así de liviano que abriera una imagen y me dejara marcarla ya.

![icono](img-annotator.svg)

## Qué hace

- **Anotar:** flecha, rectángulo, círculo y texto, con color, grosor y tamaño de texto.
- **Resaltador** translúcido, **pasos numerados** (1, 2, 3… automáticos) y **pixelar** una zona para tapar datos sensibles. El pixelado lee la imagen al pintar, así que sigue bien si lo movés, recortás o girás la imagen.
- **Recortar:** con tiradores, tercios, tamaño en vivo y proporciones fijas (1:1, 4:3, 16:9…).
- **Rotar** 90° a izquierda o derecha, **enderezar** con cualquier ángulo (con cuadrícula de guía, para nivelar un horizonte) y **voltear** horizontal o vertical. Las anotaciones acompañan a la imagen.
- **Deshacer/rehacer** de todo, incluido el recorte.
- **Carpeta:** abrís una imagen y pasás a las demás con las flechas del teclado.
- Copiar al portapapeles (Ctrl+C), guardar como PNG/JPG, zoom con la rueda.

## Atajos

| Tecla | Acción |
|---|---|
| V / Esc | Seleccionar (doble clic en un texto lo edita) |
| A / R / O / T | Flecha / rectángulo / círculo / texto |
| H / N / P | Resaltador / pasos numerados / pixelar |
| C | Recortar (Enter aplica, Esc cancela) |
| Shift | Cuadrado, círculo perfecto o flecha a 45° |
| E | Enderezar (Enter aplica, Esc cancela) |
| Ctrl+L / Ctrl+R | Rotar a la izquierda / derecha |
| Ctrl+Shift+H / Ctrl+Shift+V | Voltear horizontal / vertical |
| Ctrl+Z / Ctrl+Shift+Z | Deshacer / rehacer |
| Ctrl+C / Ctrl+S / Ctrl+O | Copiar / guardar como / abrir |
| ← / → | Imagen anterior / siguiente |
| Ctrl+0 / Ctrl+1 | Ajustar a la ventana / 100 % |

## Instalar

Necesita Python 3 y PySide6 (Fedora/Nobara: `sudo dnf install python3-pyside6`).

```
git clone https://github.com/maxisanturba/img-annotator.git
cd img-annotator
./install.sh
```

Deja el lanzador en el menú de aplicaciones y el comando `img-annotator`. También se puede
correr directo: `python3 img_annotator.py [imagen_o_carpeta]`.

## Alternativas

Si necesitás captura de pantalla integrada, mirá Spectacle (KDE), Ksnip o Flameshot. Este
programa solo edita imágenes que ya tenés.

## Licencia

MIT.
