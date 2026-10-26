# Tablero Las Tortugas

Tablero del grupo de golf **Las Tortugas** (CC Medellín) con los índices, rondas y tarjetas oficiales de Fedegolf.
Se actualiza solo todos los días a las 6:17 a. m. (hora Colombia) y se publica en GitHub Pages.

## Cómo funciona

1. `scraper.py` consulta Fedegolf para los jugadores de `data/players.json` (índice vigente, últimas 20 rondas, tarjeta hoyo a hoyo, historial de liquidaciones, ranking nacional, próximos torneos) y escribe `data/fedegolf_latest.json`.
2. `merge.py` fusiona esa consulta con `data/historial.json`, el archivo acumulado del grupo. Fedegolf solo guarda las últimas 20 rondas por jugador; este archivo conserva todas las que alguna vez se vieron (las que ya salieron de Fedegolf quedan marcadas `vigente: false`). Produce `data/tortugas.json`.
3. `build_page.py` incrusta `data/tortugas.json` en `template.html` y genera `docs/index.html`, que es lo que publica GitHub Pages.
4. `.github/workflows/update.yml` ejecuta los tres pasos cada día y hace commit de los cambios. También se puede correr a mano desde la pestaña **Actions → Actualizar tablero → Run workflow**.

## Archivos que no hay que tocar

- `data/historial.json`: es la memoria del tablero. Si se borra, se pierden las rondas que Fedegolf ya no muestra.
- `docs/index.html`: lo genera el robot; cualquier cambio manual se sobrescribe.

## Cambiar jugadores

Edita `data/players.json` (código Fedegolf, nombre corto, categoría y marcas). El campo `id` lo resuelve el robot solo; puede dejarse vacío para un jugador nuevo.

## Ejecutar en el computador

```
pip install -r requirements.txt
python tests/test_parsers.py   # prueba los parsers con fragmentos reales de Fedegolf
python scraper.py              # consulta Fedegolf (tarda ~2 minutos)
python merge.py
python build_page.py           # genera docs/index.html
```
