import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_leaflet as dl
import pandas as pd
from geopy.distance import geodesic

# Cargar los datos
df_cobertura = pd.read_csv('data/dataset_con_coordenadas.csv')
df_sin_cobertura = pd.read_csv('data/sinCoberturaCusco.csv')

# Crear listas de opciones para los dropdowns
opciones_inicio = [{'label': f"{row['DISTRITO']} ({row['Latitude']}, {row['Longitude']})", 'value': idx} for idx, row in df_cobertura.iterrows()]
opciones_fin = [{'label': f"{row['DISTRITO']} ({row['Latitude']}, {row['Longitude']})", 'value': idx} for idx, row in df_sin_cobertura.iterrows()]

# Crear la aplicación Dash
app = dash.Dash(__name__)

# Definir el layout de la aplicación
app.layout = html.Div([
    html.H1("Ruta de Conexión entre Puntos con y sin Cobertura de Agua"),
    
    html.Label("Selecciona un punto de inicio (con cobertura):"),
    dcc.Dropdown(id='punto-inicio', options=opciones_inicio, placeholder="Elige un punto de inicio"),
    
    html.Label("Selecciona un punto de llegada (sin cobertura):"),
    dcc.Dropdown(id='punto-fin', options=opciones_fin, placeholder="Elige un punto de llegada"),
    
    dl.Map([
        dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
        
        # Capa para los puntos de cobertura (azul)
        dl.LayerGroup(id='puntos-cobertura'),
        
        # Capa para los puntos sin cobertura (rojo)
        dl.LayerGroup(id='puntos-sin-cobertura'),
        
        # Capa para la ruta calculada
        dl.LayerGroup(id='ruta-camino')
        
    ], style={'width': '100%', 'height': '600px'}, center=[-13.5, -71.97], zoom=8)
])

# Actualizar los puntos en el mapa
@app.callback(
    [Output('puntos-cobertura', 'children'),
     Output('puntos-sin-cobertura', 'children')],
    Input('punto-inicio', 'options')
)
def mostrar_puntos(_):
    puntos_cobertura = [
        dl.CircleMarker(center=[row['Latitude'], row['Longitude']], color='blue', radius=5,
                        children=dl.Tooltip(f"{row['DISTRITO']}"))
        for idx, row in df_cobertura.iterrows()
    ]
    puntos_sin_cobertura = [
        dl.CircleMarker(center=[row['Latitude'], row['Longitude']], color='red', radius=5,
                        children=dl.Tooltip(f"{row['DISTRITO']}"))
        for idx, row in df_sin_cobertura.iterrows()
    ]
    return puntos_cobertura, puntos_sin_cobertura

# Calcular la ruta y mostrarla en el mapa
@app.callback(
    Output('ruta-camino', 'children'),
    [Input('punto-inicio', 'value'), Input('punto-fin', 'value')]
)
def calcular_ruta(punto_inicio, punto_fin):
    if punto_inicio is None or punto_fin is None:
        return []

    # Obtener las coordenadas de los puntos de inicio y fin seleccionados
    inicio = (df_cobertura.loc[punto_inicio, 'Latitude'], df_cobertura.loc[punto_inicio, 'Longitude'])
    fin = (df_sin_cobertura.loc[punto_fin, 'Latitude'], df_sin_cobertura.loc[punto_fin, 'Longitude'])
    
    # Lista para almacenar los segmentos de la ruta
    ruta = []
    nodo_actual = inicio
    visitados = set()
    visitados.add(punto_inicio)

    # Configuración de rangos progresivos para encontrar conexiones
    max_distancia_directa = 10000  # Distancia máxima para la conexión directa (en metros)
    max_distancia_nodo = 10000     # Distancia máxima para buscar el siguiente nodo intermedio

    # Iterar hasta que se alcance el destino
    while geodesic(nodo_actual, fin).meters > max_distancia_directa:
        # Encontrar el nodo más cercano al nodo actual que no haya sido visitado dentro del rango
        siguiente_nodo = None
        menor_distancia = float("inf")

        # Buscar el nodo más cercano dentro del rango de `max_distancia_nodo`
        for idx, row in df_cobertura.iterrows():
            if idx not in visitados:
                nodo_candidato = (row['Latitude'], row['Longitude'])
                distancia = geodesic(nodo_actual, nodo_candidato).meters

                if distancia < menor_distancia and distancia <= max_distancia_nodo:
                    menor_distancia = distancia
                    siguiente_nodo = nodo_candidato
                    siguiente_idx = idx

        # Si no se encontró un nodo dentro del rango, aumentar el rango de búsqueda
        if siguiente_nodo is None:
            max_distancia_nodo += 10000  # Aumentar el rango en 5 km
            continue

        # Agregar el segmento de la ruta y actualizar el nodo actual
        ruta.append(dl.Polyline(positions=[nodo_actual, siguiente_nodo], color="blue"))
        nodo_actual = siguiente_nodo
        visitados.add(siguiente_idx)

    # Conectar el último nodo al punto de llegada
    ruta.append(dl.Polyline(positions=[nodo_actual, fin], color="green"))
    
    return ruta

# Ejecutar la app
if __name__ == '__main__':
    app.run_server(debug=True)
