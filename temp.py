import bcrypt
import getpass  # Para ingresar la contraseña de forma más segura


def hash_password(password_str):
    """
    Genera un hash bcrypt para la contraseña dada.
    """
    password_bytes = password_str.encode("utf-8")
    # Generar salt y hashear la contraseña
    # El costo (rounds) por defecto de bcrypt.gensalt() suele ser 12, lo cual es bueno.
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode("utf-8")  # Devolver como string


if __name__ == "__main__":
    print("Generador de Hash Bcrypt para Contraseñas")
    # Usar getpass para que la contraseña no se muestre en la terminal al escribirla
    new_password = getpass.getpass("Ingresa la nueva contraseña para el repartidor: ")
    confirm_password = getpass.getpass("Confirma la nueva contraseña: ")

    if new_password == confirm_password:
        if not new_password:
            print("La contraseña no puede estar vacía.")
        else:
            hashed = hash_password(new_password)
            print("\nContraseña hasheada con Bcrypt:")
            print(hashed)
            print("\nCopia este hash para actualizarlo en la base de datos.")
    else:
        print("Las contraseñas no coinciden. Inténtalo de nuevo.")
