from autobahn.asyncio import WebSocketServerProtocol
import db
from sqlalchemy import Column, Integer, String, ForeignKey


class MyServerProtocol(WebSocketServerProtocol):

    def onConnect(self, request):
        print("Cliente conectado")

    def onOpen(self):
        print("Conexión abierta")

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Mensaje binario recibido")
        else:
            print("Mensaje de texto recibido")

        self.sendMessage(payload, isBinary)

    def onClose(self, wasClean, code, reason):
        print("Conexión cerrada")


class Usuarios(db.Base):
    __tablename__ = "usuarios"
    idUser = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String(40), nullable=False)
    contrasena = Column(String(400), nullable=False)
    nombreCompleto = Column(String(60), nullable=False)
    tipoUsuario = Column(String, nullable=False)

    def __init__(self, usuario, contrasena, nombreCompleto, tipoUsuario):
        self.usuario = usuario
        self.contrasena = contrasena
        self.nombreCompleto = nombreCompleto
        self.tipoUsuario = tipoUsuario

    def __repr_(self):
        return "holi"

    def __str__(self):
        return "Hola {}".format(self.nombreCompleto)


class Pedidos(db.Base):
    __tablename__ = "pedidos"
    idPedido = Column(Integer, primary_key=True, autoincrement=True)
    producto = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False)
    ID_pedido = Column(Integer, ForeignKey(Usuarios.idUser))
    horaFecha = Column(String, nullable=False)
    precioPedido = Column(Integer, nullable=False)

    def __init__(self, producto, cantidad, ID_pedido, horaFecha, precioPedido):
        self.producto = producto
        self.cantidad = cantidad
        self.ID_pedido = ID_pedido
        self.horaFecha = horaFecha
        self.precioPedido = precioPedido

    def __repr_(self):
        return "holi"

    def __str__(self):
        return "Hola"


class Productos(db.Base):
    __tablename__ = "productos"
    idProducto = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    precio = Column(Integer, nullable=False)
    stock = Column(Integer, nullable=False)
    ID_relacionadoProducto = Column(Integer, ForeignKey(Usuarios.idUser))

    def __init__(self, nombre, descripcion, precio, stock, ID_relacionadoProducto):
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.stock = stock
        self.ID_relacionadoProducto = ID_relacionadoProducto

    def __str__(self):
        return "Hola"


db.Base.metadata.create_all(db.engine)
