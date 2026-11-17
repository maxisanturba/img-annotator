#!/usr/bin/env bash
# Instala Img Annotator para el usuario actual (sin sudo): lanzador, entrada de menú e icono.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
python3 -c "import PySide6" 2>/dev/null || { echo "Falta PySide6 (Fedora: sudo dnf install python3-pyside6)"; exit 1; }

mkdir -p ~/.local/bin ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
ln -sf "$here/img_annotator.py" ~/.local/bin/img-annotator
cp "$here/img-annotator.svg" ~/.local/share/icons/hicolor/scalable/apps/img-annotator.svg
cat > ~/.local/share/applications/img-annotator.desktop <<DESKTOP
[Desktop Entry]
Type=Application
Name=Img Annotator
Comment=Editor de capturas: anotar y recortar
Exec=python3 $here/img_annotator.py %f
Icon=img-annotator
Terminal=false
Categories=Graphics;Viewer;
MimeType=image/png;image/jpeg;image/bmp;image/gif;image/webp;image/tiff;
DESKTOP
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
echo "Listo. Buscá «Img Annotator» en el menú o ejecutá: img-annotator imagen.png"
