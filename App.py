import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_leaflet as dl
import pandas as pd
from geopy.distance import geodesic
import os

# Cargar los datos y reiniciar los índices
df_cobertura = pd.read_csv('data/dataset_con_coordenadas.csv').drop_duplicates(subset=['Latitude', 'Longitude']).reset_index(drop=True)
df_sin_cobertura = pd.read_csv('data/sinCoberturaCusco.csv').reset_index(drop=True)

# Crear listas de opciones para los dropdowns
opciones_sin_cobertura = [{'label': f"{row['DISTRITO']} ({row['Latitude']}, {row['Longitude']})", 'value': idx} for idx, row in df_sin_cobertura.iterrows()]

# Verificar si el archivo de usuarios existe, sino crear uno
if not os.path.exists('data/usuarios.csv'):
    pd.DataFrame(columns=["username", "password"]).to_csv('data/usuarios.csv', index=False)

usuarios = pd.read_csv("data/usuarios.csv")

# Crear la aplicación Dash
app = dash.Dash(__name__)

# Definir el layout de la aplicación
app.layout = html.Div([
    # Layout de autenticación
    html.Div(id="auth-layout", children=[
        html.H1("Bienvenido"),
        dcc.Tabs(id="auth-tabs", value="login", children=[
            dcc.Tab(label="Iniciar Sesión", value="login", children=[
                html.Div([
                    html.Label("Usuario:"),
                    dcc.Input(id="login-username", type="text", placeholder="Ingrese su usuario"),
                    html.Br(),
                    html.Label("Contraseña:"),
                    dcc.Input(id="login-password", type="password", placeholder="Ingrese su contraseña"),
                    html.Br(),
                    html.Button("Ingresar", id="login-button"),
                    html.Div(id="login-error", style={"color": "red"})
                ])
            ]),
            dcc.Tab(label="Registrar Usuario", value="register", children=[
                html.Div([
                    html.Label("Nuevo Usuario:"),
                    dcc.Input(id="register-username", type="text", placeholder="Ingrese su usuario"),
                    html.Br(),
                    html.Label("Nueva Contraseña:"),
                    dcc.Input(id="register-password", type="password", placeholder="Ingrese su contraseña"),
                    html.Br(),
                    html.Button("Registrar", id="register-button"),
                    html.Div(id="register-error", style={"color": "red"})
                ])
            ])
        ])
    ]),
    
    # Elementos de la aplicación principal (inicialmente ocultos)
    html.Div(id="app-content", style={"display": "none"}, children=[
        html.H1("Ruta de Conexión entre Puntos sin Cobertura y el Nodo más Cercano con Cobertura de Agua", 
                style={'text-align': 'center', 'margin-top': '20px', 'margin-bottom': '20px'}),
        html.Div([
            html.Label("Selecciona un punto sin cobertura:", style={'font-weight': 'bold'}),
            dcc.Dropdown(
                id='punto-sin-cobertura', 
                options=opciones_sin_cobertura, 
                placeholder="Elige un punto sin cobertura",
                style={'width': '100%', 'margin': '10px 0'}
            ),
        ], style={'width': '80%', 'margin': '0 auto', 'padding': '10px'}),
        
        html.Div([
            html.Label("Costo por km (en soles):", style={'font-weight': 'bold'}),
            dcc.Input(id='costo-por-km', type='number', value=100000, style={'width': '100%', 'margin': '10px 0', 'color': 'black'}),
        ], style={'width': '80%', 'margin': '0 auto', 'padding': '10px', 'border': '2px solid #ccc', 'border-radius': '8px', 'background-color': '#f9f9f9'}),
        
        html.Div(id="distancia-resultante", style={
            'margin': '20px auto', 
            'width': '80%', 
            'text-align': 'center', 
            'font-size': '18px', 
            'font-weight': 'bold', 
            'color': '#000000',
            'padding': '10px', 
            'border': '2px solid #ccc', 
            'border-radius': '8px'
        }),
        
        # Mapa fuera del app-layout
        html.Div([
            dl.Map([
                dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
                dl.LayerGroup(id='puntos-cobertura'),
                dl.LayerGroup(id='puntos-sin-cobertura'),
                dl.LayerGroup(id='ruta-camino')
            ], 
            style={
                'width': '1000px', 
                'height': '800px',  # Aumentar la altura del mapa
                'margin': '0 auto',
                'border': '2px solid #ccc',
                'border-radius': '8px'  
            }, 
            center=[-13.5, -71.97], 
            zoom=8,
            id='mapa-principal')
        ], style={
            'width': '95%',  # Aumentar el ancho total del contenedor del mapa
            'margin': '20px auto',
            'padding': '10px'
        })
    ])
])

# Resto de los callbacks y funciones (sin cambios)
@app.callback(
    Output("register-error", "children"),
    Input("register-button", "n_clicks"),
    State("register-username", "value"),
    State("register-password", "value")
)
def register_user(n_clicks, username, password):
    if n_clicks:
        if not username or not password:
            return "El usuario y la contraseña no pueden estar vacíos."
        usuarios = pd.read_csv("data/usuarios.csv")
        if username in usuarios["username"].values:
            return "El usuario ya existe."
        nuevos_datos = pd.DataFrame({"username": [username], "password": [password]})
        nuevos_datos.to_csv("data/usuarios.csv", mode="a", header=False, index=False)
        return "Usuario registrado exitosamente."
    return ""

@app.callback(
    [Output("auth-layout", "style"), 
     Output("app-content", "style"), 
     Output("login-error", "children"),  
     Output("login-username", "value"),  
     Output("login-password", "value")], 
    [Input("login-button", "n_clicks")],
    [State("login-username", "value"), State("login-password", "value")]
)
def login_user(n_clicks, username, password):
    if n_clicks:
        usuarios = pd.read_csv("data/usuarios.csv")
        if username in usuarios["username"].values:
            if usuarios.loc[usuarios["username"] == username, "password"].values[0] == password:
                return {"display": "none"}, {"display": "block"}, "", "", ""
        return {"display": "block"}, {"display": "none"}, "Usuario o contraseña incorrectos.", username, ""   
    return {"display": "block"}, {"display": "none"}, "", username, password

@app.callback(
    [Output('puntos-cobertura', 'children'),
     Output('puntos-sin-cobertura', 'children')],
    [Input('mapa-principal', 'bounds')]
)
def mostrar_puntos(bounds):
    puntos_cobertura = [
        dl.CircleMarker(
            center=[row['Latitude'], row['Longitude']], 
            color='blue', 
            radius=5,
            children=dl.Tooltip(f"{row['DISTRITO']}")
        )
        for idx, row in df_cobertura.iterrows()
    ]
    
    puntos_sin_cobertura = [
        dl.CircleMarker(
            center=[row['Latitude'], row['Longitude']], 
            color='red', 
            radius=5,
            children=dl.Tooltip(f"{row['DISTRITO']}")
        )
        for idx, row in df_sin_cobertura.iterrows()
    ]
    
    return puntos_cobertura, puntos_sin_cobertura

def encontrar_nodo_mas_cercano(lat_inicio, lon_inicio):
    limite_distancia = 1500000  # Empezar con 15 km
    incremento = 500000  # Incremento de 5 km

    while True:
        distancias = df_cobertura.apply(
            lambda row: geodesic((lat_inicio, lon_inicio), (row['Latitude'], row['Longitude'])).meters, axis=1
        )
        
        nodos_cercanos = distancias[distancias <= limite_distancia]
        
        if not nodos_cercanos.empty:
            nodo_mas_cercano = nodos_cercanos.idxmin()
            distancia_mas_corta = nodos_cercanos.min()
            return nodo_mas_cercano, distancia_mas_corta
        
        limite_distancia += incremento

# Calcular la ruta, distancia y costo de conexión
@app.callback(
    [Output('ruta-camino', 'children'), Output('distancia-resultante', 'children')],
    [Input('punto-sin-cobertura', 'value'), Input('costo-por-km', 'value')]
)
def calcular_ruta(punto_sin_cobertura, costo_por_km):
    if punto_sin_cobertura is None or costo_por_km is None:
        return [], ""

    # Obtener las coordenadas del punto sin cobertura seleccionado
    lat_inicio = df_sin_cobertura.loc[punto_sin_cobertura, 'Latitude']
    lon_inicio = df_sin_cobertura.loc[punto_sin_cobertura, 'Longitude']
    distrito_sin_cobertura = df_sin_cobertura.loc[punto_sin_cobertura, 'DISTRITO']
    
    # Buscar el nodo de cobertura más cercano
    nodo_mas_cercano, distancia_mas_corta = encontrar_nodo_mas_cercano(lat_inicio, lon_inicio)
    
    # Obtener las coordenadas y el nombre del nodo más cercano
    nearest_coords = (df_cobertura.loc[nodo_mas_cercano, 'Latitude'], df_cobertura.loc[nodo_mas_cercano, 'Longitude'])
    nearest_distrito = df_cobertura.loc[nodo_mas_cercano, 'DISTRITO']
    
    # Crear la ruta en el mapa desde el punto sin cobertura al nodo de cobertura más cercano
    ruta = [dl.Polyline(positions=[(lat_inicio, lon_inicio), nearest_coords], color="green", weight=3)]
    
    # Calcular la distancia en kilómetros y el costo
    distancia_km = round(distancia_mas_corta / 1000, 2)
    costo_total = distancia_km * costo_por_km
    costo_total = round(costo_total, 2)

    # Texto de la información de conexión
    distancia_texto = (f"El punto de conexión más cercano para '{distrito_sin_cobertura}' "
                       f"es '{nearest_distrito}' y su distancia es de {distancia_km} km. "
                       f"El costo de conexión es de {costo_total} soles.")
    
    return ruta, distancia_texto

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True)