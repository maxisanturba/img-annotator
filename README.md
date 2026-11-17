# Img Annotator

Editor de capturas simple para Linux: anotar y recortar, sin nada más. Lo hice para Nobara
(KDE) porque no encontraba algo así de liviano que abriera una imagen y me dejara marcarla ya.

![icono](img-annotator.svg)

## Qué hace

- **Anotar:** flecha, rectángulo, círculo y texto, con color, grosor y tamaño de texto.
- **Recortar:** con tiradores, tercios, tamaño en vivo y proporciones fijas (1:1, 4:3, 16:9…).
- **Deshacer/rehacer** de todo, incluido el recorte.
- **Carpeta:** abrís una imagen y pasás a las demás con las flechas del teclado.
- Copiar al portapapeles (Ctrl+C), guardar como PNG/JPG, zoom con la rueda.

## Atajos

| Tecla | Acción |
|---|---|
| V / Esc | Seleccionar (doble clic en un texto lo edita) |
| A / R / O / T | Flecha / rectángulo / círculo / texto |
| C | Recortar (Enter aplica, Esc cancela) |
| Shift | Cuadrado, círculo perfecto o flecha a 45° |
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
