from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import zipfile
import os
from datetime import datetime
import json
import re
from elasticsearch import Elasticsearch

app = Flask(__name__)
app.secret_key = 'MateoBigdata'  # Cambia esto por una clave secreta segura

# Agregar la función now al contexto de la plantilla
@app.context_processor
def inject_now():
    return {'now': datetime.now}

# Versión de la aplicación
VERSION_APP = "Versión 2.0 del 1 de Diciembre del 2025"
CREATOR_APP = "MATEOMR97/https://github.com/MATEOMR97/BigDataapp_2025_S2"

mongo_uri = os.environ.get("MONGO_URI")
if not mongo_uri:
    mongo_uri = "mongodb+srv://dmoralesr1:Juanjose1996*@cluster0.bt85l81.mongodb.net/?appName=Cluster0"

# Constantes para gestión de usuarios
MONGO_DB = 'administracion'
MONGO_COLECCION = 'seguridad'

# Función para conectar a MongoDB
def connect_mongo():
    try:
        client = MongoClient(mongo_uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        print("Conexión exitosa a MongoDB!")
        return client
    except Exception as e:
        print(f"Error al conectar a MongoDB: {e}")
        return None

# Helpers de usuarios
def obtener_usuario_db(nombre_usuario):
    client = connect_mongo()
    if not client:
        return None
    try:
        db = client[MONGO_DB]
        col = db[MONGO_COLECCION]
        return col.find_one({'usuario': nombre_usuario})
    finally:
        client.close()

def crear_usuario_db(usuario, password, permisos):
    client = connect_mongo()
    if not client:
        return False
    try:
        db = client[MONGO_DB]
        col = db[MONGO_COLECCION]
        col.insert_one({
            'usuario': usuario,
            'password': password,
            'permisos': permisos
        })
        return True
    finally:
        client.close()

def actualizar_usuario_db(usuario_original, datos):
    client = connect_mongo()
    if not client:
        return False
    try:
        db = client[MONGO_DB]
        col = db[MONGO_COLECCION]
        result = col.update_one({'usuario': usuario_original}, {'$set': datos})
        return result.modified_count > 0
    finally:
        client.close()

def eliminar_usuario_db(usuario):
    client = connect_mongo()
    if not client:
        return False
    try:
        db = client[MONGO_DB]
        col = db[MONGO_COLECCION]
        result = col.delete_one({'usuario': usuario})
        return result.deleted_count > 0
    finally:
        client.close()

# Configuración de Elasticsearch
client_es = Elasticsearch(
    "https://9ad253341e18435fbdee621c70e570cd.us-central1.gcp.cloud.es.io:443",
    api_key="dExWaTNKb0I3dTdoME5BRGR1U0s6MWttUTgwdFVPa25pQVZrREg2QzZoQQ=="
)
INDEX_NAME = "ucentral_test_"

@app.route('/')
def index():
    return render_template('Index.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/about')
def about():
    return render_template('about.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        try:
            client = connect_mongo()
            if not client:
                return render_template('contacto.html', version=VERSION_APP, creador=CREATOR_APP,
                                       error_message="Error de conexión a la base de datos")

            db = client['administracion']
            collection = db['contactos']

            nombre = request.form.get('nombre')
            email = request.form.get('email')
            asunto = request.form.get('asunto')
            mensaje = request.form.get('mensaje')
            fecha = datetime.now()

            doc = {
                "nombre": nombre,
                "email": email,
                "mensaje": f"Asunto: {asunto}\nMensaje: {mensaje}",
                "fecha": fecha
            }

            collection.insert_one(doc)
            return render_template('contacto.html', version=VERSION_APP, creador=CREATOR_APP,
                                   success_message="Mensaje enviado con éxito.")
        except Exception as e:
            return render_template('contacto.html', version=VERSION_APP, creador=CREATOR_APP,
                                   error_message=f"Error al guardar el mensaje: {str(e)}")
        finally:
            if 'client' in locals():
                client.close()

    return render_template('contacto.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        client = connect_mongo()
        if not client:
            return render_template('login.html',
                                   error_message='Error de conexión con la base de datos. Por favor, intente más tarde.',
                                   version=VERSION_APP, creador=CREATOR_APP)
        try:
            db = client['administracion']
            security_collection = db['seguridad']
            usuario = request.form['usuario']
            password = request.form['password']

            user = security_collection.find_one({
                'usuario': usuario,
                'password': password
            })

            if user:
                session['usuario'] = usuario
                session['logged_in'] = True
                session['permisos'] = user.get('permisos', {})
                return redirect(url_for('gestion_proyecto'))
            else:
                return render_template('login.html',
                                       error_message='Usuario o contraseña incorrectos',
                                       version=VERSION_APP, creador=CREATOR_APP)
        except Exception as e:
            return render_template('login.html',
                                   error_message=f'Error al validar credenciales: {str(e)}',
                                   version=VERSION_APP, creador=CREATOR_APP)
        finally:
            client.close()

    return render_template('login.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/listar-usuarios')
def listar_usuarios():
    try:
        client = connect_mongo()
        if not client:
            return jsonify({'error': 'Error de conexión con la base de datos'}), 500

        db = client['administracion']
        security_collection = db['seguridad']

        usuarios = list(security_collection.find())
        for usuario in usuarios:
            usuario['_id'] = str(usuario['_id'])

        return jsonify(usuarios)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/gestor_usuarios')
def gestor_usuarios():
    if not session.get('logged_in'):
        flash('Por favor, inicia sesión para acceder a esta página', 'warning')
        return redirect(url_for('login'))

    permisos = session.get('permisos', {})
    if not permisos.get('admin_usuarios'):
        flash('No tiene permisos para gestionar usuarios', 'danger')
        return redirect(url_for('gestion_proyecto'))

    return render_template('gestor_usuarios.html',
                           usuario=session.get('usuario'),
                           permisos=permisos,
                           version=VERSION_APP,
                           creador=CREATOR_APP)

@app.route('/crear-usuario', methods=['POST'])
def crear_usuario():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos_sesion = session.get('permisos', {})
        if not permisos_sesion.get('admin_usuarios'):
            return jsonify({'success': False, 'error': 'No tiene permisos para crear usuarios'}), 403

        data = request.get_json()
        usuario = data.get('usuario')
        password = data.get('password')
        permisos_usuario = data.get('permisos', {})

        if not usuario or not password:
            return jsonify({'success': False, 'error': 'Usuario y password son requeridos'}), 400

        usuario_existente = obtener_usuario_db(usuario)
        if usuario_existente:
            return jsonify({'success': False, 'error': 'El usuario ya existe'}), 400

        resultado = crear_usuario_db(usuario, password, permisos_usuario)

        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Error al crear usuario'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/actualizar-usuario', methods=['POST'])
def actualizar_usuario():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos_sesion = session.get('permisos', {})
        if not permisos_sesion.get('admin_usuarios'):
            return jsonify({'success': False, 'error': 'No tiene permisos para actualizar usuarios'}), 403

        data = request.get_json()
        usuario_original = data.get('usuario_original')
        datos_usuario = data.get('datos', {})

        if not usuario_original:
            return jsonify({'success': False, 'error': 'Usuario original es requerido'}), 400

        usuario_existente = obtener_usuario_db(usuario_original)
        if not usuario_existente:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        nuevo_usuario = datos_usuario.get('usuario')
        if nuevo_usuario and nuevo_usuario != usuario_original:
            usuario_duplicado = obtener_usuario_db(nuevo_usuario)
            if usuario_duplicado:
                return jsonify({'success': False, 'error': 'Ya existe otro usuario con ese nombre'}), 400

        resultado = actualizar_usuario_db(usuario_original, datos_usuario)

        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Error al actualizar usuario'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/eliminar-usuario', methods=['POST'])
def eliminar_usuario():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos_sesion = session.get('permisos', {})
        if not permisos_sesion.get('admin_usuarios'):
            return jsonify({'success': False, 'error': 'No tiene permisos para eliminar usuarios'}), 403

        data = request.get_json()
        usuario = data.get('usuario')

        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario es requerido'}), 400

        usuario_existente = obtener_usuario_db(usuario)
        if not usuario_existente:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        if usuario == session.get('usuario'):
            return jsonify({'success': False, 'error': 'No puede eliminarse a sí mismo'}), 400

        resultado = eliminar_usuario_db(usuario)

        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Error al eliminar usuario'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/gestion_proyecto', methods=['GET', 'POST'])
def gestion_proyecto():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        client = connect_mongo()
        databases = client.list_database_names()
        system_dbs = ['admin', 'local', 'config']
        databases = [db for db in databases if db not in system_dbs]

        selected_db = request.form.get('database') if request.method == 'POST' else request.args.get('database')
        collections_data = []

        if selected_db:
            db = client[selected_db]
            collections = db.list_collection_names()
            for index, collection_name in enumerate(collections, 1):
                collection = db[collection_name]
                count = collection.count_documents({})
                collections_data.append({
                    'index': index,
                    'name': collection_name,
                    'count': count
                })

        return render_template('gestion/index.html',
                               databases=databases,
                               selected_db=selected_db,
                               collections_data=collections_data,
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])
    except Exception as e:
        return render_template('gestion/index.html',
                               error_message=f'Error al conectar con MongoDB: {str(e)}',
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])

@app.route('/crear-coleccion-form/<database>')
def crear_coleccion_form(database):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('gestion/crear_coleccion.html',
                           database=database,
                           usuario=session['usuario'],
                           version=VERSION_APP,
                           creador=CREATOR_APP)

@app.route('/crear-coleccion', methods=['POST'])
def crear_coleccion():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        database = request.form.get('database')
        collection_name = request.form.get('collection_name')
        zip_file = request.files.get('zip_file')

        if not all([database, collection_name, zip_file]):
            return render_template('gestion/crear_coleccion.html',
                                   error_message='Todos los campos son requeridos',
                                   database=database,
                                   usuario=session['usuario'],
                                   version=VERSION_APP,
                                   creador=CREATOR_APP)

        client = connect_mongo()
        if not client:
            return render_template('gestion/crear_coleccion.html',
                                   error_message='Error de conexión con MongoDB',
                                   database=database,
                                   usuario=session['usuario'],
                                   version=VERSION_APP,
                                   creador=CREATOR_APP)

        db = client[database]
        collection = db[collection_name]

        with zipfile.ZipFile(zip_file) as zip_ref:
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            zip_ref.extractall(temp_dir)

            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            try:
                                json_data = json.load(f)
                                if isinstance(json_data, list):
                                    collection.insert_many(json_data)
                                else:
                                    collection.insert_one(json_data)
                            except json.JSONDecodeError:
                                print(f"Error al procesar el archivo {file}")
                            except Exception as e:
                                print(f"Error al insertar datos del archivo {file}: {str(e)}")

            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(temp_dir)

        return redirect(url_for('gestion_proyecto', database=database))

    except Exception as e:
        return render_template('gestion/crear_coleccion.html',
                               error_message=f'Error al crear la colección: {str(e)}',
                               database=database,
                               usuario=session['usuario'],
                               version=VERSION_APP,
                               creador=CREATOR_APP)
    finally:
        if 'client' in locals():
            client.close()

@app.route('/ver-registros/<database>/llection>')
def ver_registros(database, collection):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        client = connect_mongo()
        if not client:
            return render_template('gestion/index.html',
                                   error_message='Error de conexión con MongoDB',
                                   version=VERSION_APP,
                                   creador=CREATOR_APP,
                                   usuario=session['usuario'])

        db = client[database]
        collection_obj = db[collection]

        records = list(collection_obj.find().limit(100))
        for record in records:
            record['_id'] = str(record['_id'])

        return render_template('gestion/ver_registros.html',
                               database=database,
                               collection_name=collection,
                               records=records,
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])
    except Exception as e:
        return render_template('gestion/index.html',
                               error_message=f'Error al obtener registros: {str(e)}',
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])
    finally:
        if 'client' in locals():
            client.close()

@app.route('/obtener-registros', methods=['POST'])
def obtener_registros():
    if 'usuario' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    try:
        database = request.form.get('database')
        collection = request.form.get('collection')
        limit = int(request.form.get('limit', 100))

        client = connect_mongo()
        if not client:
            return jsonify({'error': 'Error de conexión con MongoDB'}), 500

        db = client[database]
        collection_obj = db[collection]

        records = list(collection_obj.find().limit(limit))
        for record in records:
            record['_id'] = str(record['_id'])

        return jsonify({'records': records})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/crear-base-datos-form')
def crear_base_datos_form():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('gestion/crear_base_datos.html',
                           version=VERSION_APP,
                           creador=CREATOR_APP,
                           usuario=session['usuario'])

@app.route('/crear-base-datos', methods=['POST'])
def crear_base_datos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        database_name = request.form.get('database_name')
        collection_name = request.form.get('collection_name')

        valid_pattern = re.compile(r'^[a-zA-Z0-9_]+$')
        if not valid_pattern.match(database_name) or not valid_pattern.match(collection_name):
            return render_template('gestion/crear_base_datos.html',
                                   error_message='Los nombres no pueden contener tildes, espacios ni caracteres especiales',
                                   version=VERSION_APP,
                                   creador=CREATOR_APP,
                                   usuario=session['usuario'])

        client = connect_mongo()
        if not client:
            return render_template('gestion/crear_base_datos.html',
                                   error_message='Error de conexión con MongoDB',
                                   version=VERSION_APP,
                                   creador=CREATOR_APP,
                                   usuario=session['usuario'])

        db = client[database_name]
        collection = db[collection_name]

        collection.insert_one({})
        collection.delete_one({})

        return redirect(url_for('gestion_proyecto', database=database_name))

    except Exception as e:
        return render_template('gestion/crear_base_datos.html',
                               error_message=f'Error al crear la base de datos: {str(e)}',
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])
    finally:
        if 'client' in locals():
            client.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/elasticAdmin')
def elasticAdmin():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        index_info = client_es.indices.get(index=INDEX_NAME)
        doc_count = client_es.count(index=INDEX_NAME)['count']

        return render_template('gestion/ver_elasticAdmin.html',
                               index_name=INDEX_NAME,
                               doc_count=doc_count,
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])
    except Exception as e:
        return render_template('gestion/ver_elasticAdmin.html',
                               error_message=f'Error al conectar con Elasticsearch: {str(e)}',
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])

@app.route('/elastic-agregar-documentos', methods=['GET', 'POST'])
def elastic_agregar_documentos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            if 'zipFile' not in request.files:
                return render_template('gestion/elastic_agregar_documentos.html',
                                       error_message='No se ha seleccionado ningún archivo',
                                       index_name=INDEX_NAME,
                                       version=VERSION_APP,
                                       creador=CREATOR_APP,
                                       usuario=session['usuario'])

            zip_file = request.files['zipFile']
            if zip_file.filename == '':
                return render_template('gestion/elastic_agregar_documentos.html',
                                       error_message='No se ha seleccionado ningún archivo',
                                       index_name=INDEX_NAME,
                                       version=VERSION_APP,
                                       creador=CREATOR_APP,
                                       usuario=session['usuario'])

            temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
            os.makedirs(temp_dir, exist_ok=True)

            zip_path = os.path.join(temp_dir, zip_file.filename)
            zip_file.save(zip_path)

            with zipfile.ZipFile(zip_path) as zip_ref:
                zip_ref.extractall(temp_dir)

            success_count = 0
            error_count = 0

            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                json_data = json.load(f)
                                if isinstance(json_data, list):
                                    for doc in json_data:
                                        client_es.index(index=INDEX_NAME, document=doc)
                                        success_count += 1
                                else:
                                    client_es.index(index=INDEX_NAME, document=json_data)
                                    success_count += 1
                        except Exception as e:
                            error_count += 1
                            print(f"Error procesando {file}: {str(e)}")

            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(temp_dir)

            return render_template('gestion/elastic_agregar_documentos.html',
                                   success_message=f'Se indexaron {success_count} documentos exitosamente. Errores: {error_count}',
                                   index_name=INDEX_NAME,
                                   version=VERSION_APP,
                                   creador=CREATOR_APP,
                                   usuario=session['usuario'])

        except Exception as e:
            return render_template('gestion/elastic_agregar_documentos.html',
                                   error_message=f'Error al procesar el archivo: {str(e)}',
                                   index_name=INDEX_NAME,
                                   version=VERSION_APP,
                                   creador=CREADOR_APP,
                                   usuario=session['usuario'])

    return render_template('gestion/elastic_agregar_documentos.html',
                           index_name=INDEX_NAME,
                           version=VERSION_APP,
                           creador=CREATOR_APP,
                           usuario=session['usuario'])

@app.route('/elastic-listar-documentos')
def elastic_listar_documentos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        response = client_es.search(
            index=INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 100
            }
        )

        documents = response['hits']['hits']

        return render_template('gestion/elastic_listar_documentos.html',
                               index_name=INDEX_NAME,
                               documents=documents,
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])
    except Exception as e:
        return render_template('gestion/elastic_listar_documentos.html',
                               error_message=f'Error al obtener documentos: {str(e)}',
                               index_name=INDEX_NAME,
                               version=VERSION_APP,
                               creador=CREATOR_APP,
                               usuario=session['usuario'])

@app.route('/elastic-eliminar-documento', methods=['POST'])
def elastic_eliminar_documento():
    if 'usuario' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    try:
        doc_id = request.form.get('doc_id')
        if not doc_id:
            return jsonify({'error': 'ID de documento no proporcionado'}), 400

        response = client_es.delete(index=INDEX_NAME, id=doc_id)

        if response['result'] == 'deleted':
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Error al eliminar el documento'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/buscador', methods=['GET', 'POST'])
def buscador():
    if request.method == 'POST':
        try:
            search_type = request.form.get('search_type')
            search_text = request.form.get('search_text')
            fecha_desde = request.form.get('fecha_desde')
            fecha_hasta = request.form.get('fecha_hasta')

            if not fecha_desde:
                fecha_desde = "1500-01-01"
            if not fecha_hasta:
                fecha_hasta = datetime.now().strftime("%Y-%m-%d")

            query = {
                "query": {
                    "bool": {
                        "must": []
                    }
                },
                "aggs": {
                    "categoria": {
                        "terms": {
                            "field": "Categoria.keyword",
                            "size": 10,
                            "order": {"_key": "asc"}
                        }
                    },
                    "nombre": {
                        "terms": {
                            "field": "nombre.keyword",
                            "size": 10,
                            "order": {"_key": "asc"}
                        }
                    },
                    "Fecha": {
                        "date_histogram": {
                            "field": "fecha_generado",
                            "calendar_interval": "year",
                            "format": "yyyy"
                        }
                    }
                }
            }

            if search_type == 'texto':
                query["query"]["bool"]["must"].append({
                    "match_phrase": {
                        "texto": {
                            "query": search_text,
                            "slop": 1
                        }
                    }
                })
            else:
                search_text = '' + search_text + ''
                query["query"]["bool"]["must"].append(
                    {"match": {search_type: search_text}}
                )

            range_query = {
                "range": {
                    "fecha_generado": {
                        "format": "yyyy-MM-dd",
                        "gte": fecha_desde,
                        "lte": fecha_hasta
                    }
                }
            }
            query["query"]["bool"]["must"].append(range_query)

            response = client_es.search(
                index=INDEX_NAME,
                body=query
            )

            hits = response['hits']['hits']
            aggregations = response['aggregations']

            return render_template('buscador.html',
                                   version=VERSION_APP,
                                   creador=CREATOR_APP,
                                   hits=hits,
                                   aggregations=aggregations,
                                   search_type=search_type,
                                   search_text=search_text,
                                   fecha_desde=fecha_desde,
                                   fecha_hasta=fecha_hasta,
                                   query=query)

        except Exception as e:
            return render_template('buscador.html',
                                   version=VERSION_APP,
                                   creador=CREATOR_APP,
                                   error_message=f'Error en la búsqueda: {str(e)}')

    return render_template('buscador.html',
                           version=VERSION_APP,
                           creador=CREATOR_APP)

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        index_name = data.get('index', 'ucentral_test_')
        query = data.get('query')

        response = client_es.search(
            index=index_name,
            body=query
        )

        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
