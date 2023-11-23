import os
import sqlite3
import eventlet
from eventlet import wsgi, websocket
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit, leave_room, send
import db
import bcrypt
import logging
import datetime
import plotly.graph_objs as go
import plotly.offline as pyo
from models import Usuarios, Pedidos, Productos, MyServerProtocol

logger = logging.getLogger(__name__)
app = Flask(__name__)
app.config["SECRET_KEY"] = 'secret'
socketio = SocketIO(app)


# variables del carrito, era necesario que fueran globales
productosCarrito = []
total = []
totalFinal = sum(total)


"""A continuacion tenemos una funcion que nos servira para rellenar la base de datos un poco, con usuarios y ejemplos de productos. Tambien se creara
el usuario Administrador. A continuacion te muestro los usuarios creados y sus contraseñas:
Usuario: Pedro --> Contraseña: 123 (Cliente)
Usuario: Maria --> Contraseña: 123 (Cliente)
Usuario: Jaime --> Contraseña: 123 (Proveedor)
Usuario: admin --> Contraseña: 123 (Administrador)

"""

def crear_ejemplos():
    passwordU = "123"
    key = bcrypt.hashpw(passwordU.encode('utf8'), bcrypt.gensalt())
    user1 = Usuarios(usuario="Pedro", contrasena=key, nombreCompleto="Pedro Alvarez", tipoUsuario="cliente")
    user2 = Usuarios(usuario="Maria", contrasena=key, nombreCompleto="Maria Diaz", tipoUsuario="cliente")
    userProveedor = Usuarios(usuario="Jaime", contrasena=key, nombreCompleto="Jaime Gutierrez",
                             tipoUsuario="proveedor")
    admin = Usuarios(usuario="admin", contrasena=key, nombreCompleto="Admin", tipoUsuario="admin")
    producto1 = Productos(nombre="Patata",
                          descripcion="Especie herbácea, perenne por sus tubérculos pero cultivada de forma normal como planta anual",
                          precio=3, stock=1000, ID_relacionadoProducto=3)
    producto2 = Productos(nombre="Lechuga",
                          descripcion="La lechuga es una hortaliza formada por grandes hojas que se disponen unas sobre otras formando en algunos casos un repollo.",
                          precio=1, stock=1000, ID_relacionadoProducto=3)
    producto3 = Productos(nombre="Tomate",
                          descripcion="El fruto del tomate es una baya, gruesa y carnosa con dos o más segmentos, de diferentes formas y colores según la variedad.",
                          precio=2, stock=1000, ID_relacionadoProducto=3)
    db.session.add(user1)
    db.session.add(user2)
    db.session.add(userProveedor)
    db.session.add(admin)
    db.session.add(producto1)
    db.session.add(producto2)
    db.session.add(producto3)
    db.session.commit()


@app.route('/', methods=['GET', 'POST'])
def home():
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM usuarios")
    fullPedidos = cursor.fetchall()
    print(fullPedidos)
    if len(fullPedidos) == 0:
        crear_ejemplos()
    return render_template("index.html")

#Esta funcion nos servira para crear las graficas que vayamos necesitando a lo largo de la aplicacion.
@app.route("/grafica/<product>")
def create_bar_chart(product):
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute(f"SELECT * FROM pedidos WHERE producto= '{product}'")
    todos = cursor.fetchall()
    productosSeparados = []
    previa = []
    if todos:
        previa.append(todos[0])
        for i in range(1, len(todos)):
            if todos[i][4][5:7] == previa[-1][4][5:7]:
                previa.append(todos[i])
            else:
                productosSeparados.append(previa)
                previa = [todos[i]]
        productosSeparados.append(previa)
    todosLosMeses = []
    for item in productosSeparados:
        totalMes = []
        for pis in range(0, len(item)):
            mes = item[pis][2]
            totalMes.append(mes)
        totalMes = sum(totalMes)
        todosLosMeses.append(totalMes)
    # Obtener los meses en los que se realizaron los pedidos
    meses = set([pedido[4][5:7] for pedido in todos])
    meses_ordenados = sorted(meses, key=lambda mes: int(mes))
    # Generar la lista de los nombres de los meses
    nombres_meses = []
    for mes in meses_ordenados:
        fecha = datetime.datetime.strptime(f'2023-{mes}-01', '%Y-%m-%d')
        nombre_mes = fecha.strftime('%B')
        nombres_meses.append(nombre_mes)
    x = todosLosMeses
    # Crear objeto de gráfica de barras
    data = [go.Bar(x=x, y=nombres_meses, orientation='h')]
    # Diseño del gráfico
    layout = go.Layout(title='KG/Mes', xaxis_title='Cantidad', yaxis_title='Meses')
    # Crear figura
    fig = go.Figure(data=data, layout=layout)
    # Guardar figura en un archivo HTML en la carpeta 'static'
    path = os.path.join('static', 'bar_chart.html')
    pyo.plot(fig, filename=path, auto_open=False)
    # Leer el contenido del archivo HTML
    with open(path, encoding='utf-8') as f:
        content = f.read()
    # Renderizar la plantilla con el archivo HTML creado en la carpeta 'static'
    return content

#ESta funcion de aqui nos activara los diversos badges que tenemos
def mostrarBadge(idUser):
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute(f"SELECT * FROM productos WHERE ID_relacionadoProducto ='{idUser}' ")
    todos = cursor.fetchall()
    mostrar_badge = True
    for item in todos:
        if item[4] < 11:
            mostrar_badge = False
            return mostrar_badge
    return mostrar_badge


@app.route('/crearNuevoUser/')
def crearNuevoUserCliente():
    return render_template("newUser.html")


@app.route('/redirigirProducto/<idUser>', methods=["GET", "POST"])
def redirigirProducto(idUser):
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    mBadge = mostrarBadge(idUser)
    return render_template("nuevoProducto.html", usuario=usuario, mBadge=mBadge)


def separarPedidos(lista):
    pedidosSeparados = []
    previa = []
    if lista:
        previa.append(lista[0])
        for i in range(1, len(lista)):
            if lista[i][4] == previa[-1][4]:
                previa.append(lista[i])
            else:
                pedidosSeparados.append(previa)
                previa = [lista[i]]
        pedidosSeparados.append(previa)
    return pedidosSeparados


#La funcion sortedKey era necesaria para poder ordenar los pedidos en la siguiente funcion
def sortedKey(item):
    return item[4]


@app.route('/pedidosUsuario/<idUser>', methods=['POST', 'GET'])
def redirigirPedidosHechos(idUser):
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM pedidos")
    fullPedidos = cursor.fetchall()
    pedidosUsuario = []
    for pedido in fullPedidos:
        if pedido[3] == int(idUser):
            pedidosUsuario.append(pedido)
    pedidosUsuario = sorted(pedidosUsuario, key=sortedKey)
    pedidosUsuario = separarPedidos(pedidosUsuario)
    return render_template("pedidosHechos.html", usuario=usuario, todosLosPedidos=pedidosUsuario)


# esta es para la pestaña de nuevo pedido
@app.route('/nuevoPedido/<idUser>', methods=['POST', 'GET'])
def nuevoPedido(idUser):
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos")
    fullProductos = cursor.fetchall()
    fullProductos = sorted(fullProductos, key=lambda x: x[1])
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    return render_template("cliente.html", usuario=usuario, listaProductos=fullProductos)

#Aqui crearemos un usuario nuevo. En caso que parte de la informacion no sea correcta, o este incompleta, saltariamos al error provocado, enviandonos
# a un html especifico, advirtiendo del fallo, y permitiendo que el usuario pueda volver a intentarlo
@app.route('/nuevoUsuario/', methods=['POST', 'GET'])
def NuevoUser():
    if request.form['FCPass'] != request.form["FCpassAgain"]:
        return render_template("newUserError.html")
    else:
        while True:
            try:
                passwordU = request.form['FCPass']
                key = bcrypt.hashpw(passwordU.encode('utf8'), bcrypt.gensalt())
                usuario = Usuarios(usuario=request.form['userNameFc'], contrasena=key,
                                   nombreCompleto=request.form['FCFullName'], tipoUsuario=request.form['selectClienteProve'])
                db.session.add(usuario)
                db.session.commit()
                return render_template("index.html")
            except KeyError:
                return render_template("newUserError.html")

#Sencilla funcion que comprobara el nombre de usuario y el pass
@app.route("/comprobarPass/", methods=['GET', 'POST'])
def comprobarPass():
    while True:
        try:
            nombreU = request.form["nombreUsuario"]
            contrasenaU = request.form['contrasenaUsuario']
            usuario = db.session.query(Usuarios).filter_by(usuario=nombreU).first()
            valid = bcrypt.checkpw(contrasenaU.encode('utf-8'), usuario.contrasena)
            if valid:
                return redirigir(usuario.idUser, usuario.tipoUsuario)
            return render_template('index.html')
        except AttributeError:
            return render_template('index.html')

#Una funcion, que dependiendo del tipo de usuario que tengamos, nos enviara a un html o a otro, con toda la informacion relacionada necesaria
def redirigir(idUser, userTipe):
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM pedidos")
    fullPedidos = cursor.fetchall()
    if userTipe == "cliente":
        usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
        conexion = sqlite3.connect("database/huerto.db")
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM productos")
        fullProductos = cursor.fetchall()
        fullProductos=sorted(fullProductos, key=lambda x: x[1])
        return render_template('cliente.html', usuario=usuario, listaPedidos=fullPedidos,
                               listaProductos=fullProductos, productosCarrito=productosCarrito, totalFinal=totalFinal)
    if userTipe == "admin":
        return listaTodos("2")
    else:
        mBadge = mostrarBadge(idUser)
        return stock(idUser)


@app.route("/pedido/<idUser>/<totalFinal>", methods=["POST", "GET"])
def guardar_pedido(idUser, totalFinal):
    for item in productosCarrito:
        nombre = item[0]
        cantidad = item[2]
        precio = totalFinal
        fecha = datetime.datetime.today().replace(microsecond=0)
        sale = Pedidos(producto=nombre, cantidad=cantidad, ID_pedido=idUser, horaFecha=fecha, precioPedido=totalFinal)
        db.session.add(sale)
        productoRestar = db.session.query(Productos).filter(Productos.nombre == nombre).first()
        productoRestar.stock = (productoRestar.stock) - int(cantidad)
        db.session.commit()
        db.session.close()
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos")
    fullProductos = cursor.fetchall()
    return render_template('cliente.html', usuario=usuario, listaProductos=fullProductos), reinicio()

#Funcion necesaria para el funcionamiento del carrito
def reinicio():
    productosCarrito.clear()
    total.clear()


@app.route("/nuevoProducto/<idUser>", methods=["POST", "GET"])
def crearProducto(idUser):
    producto = Productos(nombre=request.form["nombreProducto"], descripcion=request.form["descripcionProducto"],
                         precio=request.form["precioProducto"], stock=request.form["stockProducto"], ID_relacionadoProducto=idUser)
    print(request.form['stockProducto'])
    db.session.add(producto)
    db.session.commit()
    db.session.close()
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    mBadge = mostrarBadge(idUser)
    return render_template('stock.html', usuario=usuario, mBadge=mBadge)


@app.route("/anadirCarrito/<idUser>", methods=["POST", "GET"])
def anadirProductoCarrito(idUser):
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    nombre = request.form["nombreProducto"]
    precio = request.form["precioProducto"]
    cantidad = request.form["kilos"]
    productosCarrito.append((nombre, precio, cantidad))
    kilosTotales = int(cantidad)
    while kilosTotales > 0:
        total.append(int(precio))
        kilosTotales -= 1
    totalFinal = sum(total)
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos")
    fullProductos = cursor.fetchall()
    print(totalFinal)
    return render_template('cliente.html', productosCarrito=productosCarrito, totalFinal=totalFinal, usuario=usuario,
                           listaProductos=fullProductos)


@app.route("/eliminarProductoCarrito/<idUser>/<producto>", methods=["POST", "GET"])
def eliminarElementoCarrito(idUser, producto):
    for articulo in productosCarrito:
        if producto in articulo:
            menus = int(articulo[1])
            kilosMenos = int(articulo[2])
            while kilosMenos > 0:
                total.remove(menus)
                kilosMenos -= 1
            productosCarrito.remove(articulo)
            totalFinal = sum(total)
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos")
    fullProductos = cursor.fetchall()
    return render_template('cliente.html', usuario=usuario, productosCarrito=productosCarrito, totalFinal=totalFinal,
                           listaProductos=fullProductos)

@app.route('/stock/<idUser>', methods=["POST", "GET"])
def stock(idUser):
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    cursor.execute(f"SELECT * FROM productos WHERE ID_relacionadoProducto ='{idUser}' ")
    fullProductos = cursor.fetchall()
    fullProductos=sorted(fullProductos, key=lambda x: x[1])
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    mBadge = mostrarBadge(idUser)
    return render_template("stock.html", usuario=usuario, listaStock=fullProductos, mBadge=mBadge)

@app.route("/anadirStock/<idUser>", methods=["POST", "GET"])
def anadirStock(idUser):
    productoParaAnadir = request.form["producto"]
    cantidadAnadir= request.form["cantidadProducto"]
    if cantidadAnadir == 0 or cantidadAnadir.isdigit()==False:
        return stock(idUser)
    else:
        anadicion = db.session.query(Productos).filter_by(nombre=productoParaAnadir).first()
        anadicion.stock = anadicion.stock + int(cantidadAnadir)
        db.session.commit()
        db.session.close()
        return stock(idUser)


#Funcion para el administrador, en la cual dependiendo del tipo de dato numerico, sera redirecionado a un html u a otro, y en cada caso envia la informacion
# necesaria para la visualizacion de tal
@app.route("/todos/<dato>")
def listaTodos(dato):
    conexion = sqlite3.connect("database/huerto.db")
    cursor = conexion.cursor()
    if dato == "1" or dato == "4":
        cursor.execute("SELECT * FROM usuarios")
        all = cursor.fetchall()
    if dato == "2":
        cursor.execute("SELECT * FROM productos")
        all = cursor.fetchall()
    if dato == "3":
        cursor.execute("SELECT * FROM pedidos")
        all= cursor.fetchall()
    pos = 1
    listLen = len(all)
    for i in range(0, listLen):
        for j in range(0, listLen - i - 1):
            if (all[j][pos] > all[j + 1][pos]):
                temp = all[j]
                all[j] = all[j + 1]
                all[j + 1] = temp
    if dato == "1":
        return render_template("todosLosUsers.html", full=all)
    if dato == "2":
        print(all)
        return render_template("todosLosProducts.html", full=all)
    if dato == "3":
        pedidosUsuario = sorted(all, key=sortedKey)
        pedidosUsuario = separarPedidos(pedidosUsuario)
        cursor.execute("SELECT * FROM usuarios")
        todosUsuarios = cursor.fetchall()
        return render_template("todosLosPedidos.html", full=pedidosUsuario, todosUsers=todosUsuarios)
    else:
        return render_template("mensajes.html", full=all)

#Funcion tambien para el Admin, que nos permitira eliminar los datos deseados
@app.route("/eliminar/<dato>/<tipoDato>")
def eliminar(dato, tipoDato):
    if tipoDato == "1":
        userEliminado = db.session.query(Usuarios).filter_by(idUser=dato).delete()
        db.session.commit()
        return listaTodos("1")
    if tipoDato == "2":
        productEliminado = db.session.query(Productos).filter_by(idProducto=dato).delete()
        db.session.commit()
        return listaTodos("2")
    else:
        pedidoEliminado =db.session.query(Pedidos).filter_by(horaFecha=dato).delete()
        db.session.commit()
        return listaTodos("3")


@app.route("/chats/<idUser>/<tipoUser>")
def salaChats(idUser, tipoUser):
    usuario = db.session.query(Usuarios).filter_by(idUser=idUser).first()
    socketid = usuario.idUser
    nombre = usuario.nombreCompleto
    if tipoUser == "1":
        return render_template("salaChats.html", socketid=socketid, nombre=nombre, idUser=idUser)
    if tipoUser == "0":
        return render_template("salaChatUsuario.html", socketid=socketid, usuario=nombre, idUser=idUser)
    else:
        mBadge = mostrarBadge(idUser)
        return render_template("salaChatProveedor.html", socketid=socketid, usuario=nombre, idUser=idUser, mBadge=mBadge)


@socketio.on('message')
def handleMessage(msg):
    send(msg, broadcast=True)

@socketio.on('connect')
def on_connect():
    print('Usuario conectado')
    room = request.sid
    join_room(room)

@socketio.on('disconnect')
def on_disconnect():
    print('Usuario desconectado')

@socketio.on('mensajePrivado')
def on_mensaje_privado(data):
    id_usuario = data['idUsuario']
    mensaje = data['mensaje']
    emit('mensajePrivado', {'idUsuario': id_usuario, 'mensaje': mensaje}, room=id_usuario)

@socketio.on('join_room')
def on_join_room(data):
    id_usuario = data['idUsuario']
    room = id_usuario
    join_room(room)

@socketio.on('leave_room')
def on_leave_room(data):
    id_usuario = data['idUsuario']
    room = id_usuario
    leave_room(room)


if __name__ == '__main__':

    db.Base.metadata.create_all(db.engine)  # Creamos la tablas de la base de datos
    wsgi.server(eventlet.listen(('localhost', 5000)), app)
    websocket.serve(MyServerProtocol, 'localhost', 9000)


