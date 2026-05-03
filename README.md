# Muro de escalada

Aplicacion Streamlit para marcar presas sobre fotos del muro, clasificarlas y crear rutas estilo board.

## Ejecutar

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Streamlit Cloud

Configurar la app con:

- Main file path: `app.py`
- Python dependencies: `requirements.txt`

## Datos

- `data/holds.json`: presas por imagen.
- `data/routes.json`: rutas por imagen, con presas seleccionadas en orden.

Las coordenadas se guardan en pixeles de la imagen original.
