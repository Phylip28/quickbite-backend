class User:
    def __init__(
        self,
        id_cliente,
        nombre_cliente,
        apellido_cliente,
        direccion_cliente,
        telefono_cliente,
        correo_cliente,
        fecha_registro_cliente,
        contrasenia,
    ):
        self.id_cliente = id_cliente
        self.nombre_cliente = nombre_cliente
        self.apellido_cliente = apellido_cliente
        self.direccion_cliente = direccion_cliente
        self.telefono_cliente = telefono_cliente
        self.correo_cliente = correo_cliente
        self.fecha_registro_cliente = fecha_registro_cliente
        self.contrasenia = contrasenia  # hash de la contraseña

    def to_dict(self):
        return {
            "id_cliente": self.id_cliente,
            "nombre_cliente": self.nombre_cliente,
            "apellido_cliente": self.apellido_cliente,
            "direccion_cliente": self.direccion_cliente,
            "telefono_cliente": self.telefono_cliente,
            "correo_cliente": self.correo_cliente,
            "fecha_registro_cliente": str(self.fecha_registro_cliente),
            "contrasenia": self.contrasenia,
        }
