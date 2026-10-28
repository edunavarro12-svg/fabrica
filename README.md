# Fábrica de contenido

Motor que genera vídeos verticales cortos (retos mentales y otros formatos) por código y los publica en las cuentas oficiales de cada marca.

- `engine/render.py`: renderizado (Pillow + ffmpeg), sin clips de stock ni servicios de pago.
- `engine/formats/`: formatos de vídeo.
- `engine/brands/`: estilo y cuentas de cada marca.
- `engine/episodes/`: contenido de cada vídeo.
- `.github/workflows/`: producción y publicación.

Las credenciales viven solo en los secretos de GitHub; nunca en el repositorio.

Tipografía Montserrat bajo licencia SIL OFL (ver `engine/fonts/OFL.txt`).
