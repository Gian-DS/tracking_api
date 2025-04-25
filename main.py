from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
import time
import threading
import random
from datetime import datetime

# Configuración de la base de datos
db_config = {
    'user': 'pm2isU7CVpPA21R.root',
    'password': '81uWxd9JC7mJsrg6',
    'host': 'gateway01.us-east-1.prod.aws.tidbcloud.com',
    'port': 4000,
    'database': 'test'
}

# Modelos Pydantic
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    telefono: str
    placa: str
    tipo_vehiculo: str

class UserUpdate(BaseModel):
    email: str
    password: str
    telefono: str
    placa: str
    tipo_vehiculo: str
    oldEmail: str

class UserDelete(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    telefono: str
    placa: str
    tipo_vehiculo: str

# Configuración de FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Conexión a la base de datos
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Función para generar datos de metadata aleatorios
def generate_metadata(user_id: int):
    while True:
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 1. Verificar si existe metadata previa para este usuario
            cursor.execute("""
                SELECT id FROM metadata 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            existing_record = cursor.fetchone()
            
            # Generar nuevos datos aleatorios
            latitud = 4.7110 + random.uniform(-0.1, 0.1)
            longitud = -74.0721 + random.uniform(-0.1, 0.1)
            velocidad = random.uniform(0, 120)
            inclinacion = random.uniform(-30, 30)
            contaminacion = random.uniform(0, 500)
            hora = datetime.now().strftime("%H:%M:%S")
            fecha = datetime.now().strftime("%Y-%m-%d")
            
            if existing_record:
                # 2. ACTUALIZAR el registro existente
                update_query = """
                UPDATE metadata 
                SET latitud = %s,
                    longitud = %s,
                    velocidad = %s,
                    inclinacion = %s,
                    contaminacion = %s,
                    hora = %s,
                    fecha = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                cursor.execute(update_query, (
                    latitud,
                    longitud,
                    velocidad,
                    inclinacion,
                    contaminacion,
                    hora,
                    fecha,
                    existing_record['id']
                ))
                print(f"Registro ACTUALIZADO para usuario {user_id}")
            else:
                # 3. CREAR un nuevo registro solo si no existe ninguno
                insert_query = """
                INSERT INTO metadata 
                (user_id, latitud, longitud, velocidad, inclinacion, contaminacion, hora, fecha)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    user_id,
                    latitud,
                    longitud,
                    velocidad,
                    inclinacion,
                    contaminacion,
                    hora,
                    fecha
                ))
                print(f"Nuevo registro CREADO para usuario {user_id}")
            
            connection.commit()
            
        except Exception as e:
            print(f"Error en generate_metadata: {str(e)}")
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
        
        # Esperar 2 minutos (120 segundos)
        time.sleep(120)
# Endpoints
@app.post("/login")
def login(user: UserLogin):
    print("\n=== PETICIÓN LOGIN RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (user.email, user.password))
        result = cursor.fetchone()

        if result:
            return {
                "message": "Login exitoso",
                "user": {
                    "id": result["id"],
                    "email": result["email"],   
                    "telefono": result["telefono"],
                    "placa": result["placa"],
                    "tipo_vehiculo": result["tipo_vehiculo"].decode('utf-8') if isinstance(result["tipo_vehiculo"], bytes) else result["tipo_vehiculo"]
                }
            }
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        connection.close()

@app.post("/register")
def register(user: UserRegister):
    print("\n=== PETICIÓN REGISTRO RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
        INSERT INTO users (email, password, telefono, placa, tipo_vehiculo)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            user.email,
            user.password,
            user.telefono,
            user.placa,
            user.tipo_vehiculo
        ))
        connection.commit()

        if cursor.rowcount == 1:
            return {"message": "Usuario registrado exitosamente"}
        raise HTTPException(status_code=400, detail="Error al registrar usuario")
    
    except mysql.connector.Error as err:
        if err.errno == 1062:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        raise HTTPException(status_code=500, detail=str(err))
    
    finally:
        cursor.close()
        connection.close()

@app.put("/update")
def update(user: UserUpdate):
    print("\n=== PETICIÓN ACTUALIZACIÓN RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
        UPDATE users 
        SET email = %s, 
            password = %s,
            telefono = %s,
            placa = %s,
            tipo_vehiculo = %s
        WHERE email = %s
        """
        cursor.execute(query, (
            user.email,
            user.password,
            user.telefono,
            user.placa,
            user.tipo_vehiculo,
            user.oldEmail
        ))
        connection.commit()

        if cursor.rowcount == 1:
            return {"message": "Usuario actualizado exitosamente"}
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    except mysql.connector.Error as err:
        if err.errno == 1062:
            raise HTTPException(status_code=400, detail="El nuevo email ya está registrado")
        raise HTTPException(status_code=500, detail=str(err))
    
    finally:
        cursor.close()
        connection.close()

@app.get("/show")
def show():
    print("\n=== PETICIÓN SHOW RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = "SELECT id, email, telefono, placa, tipo_vehiculo FROM users"
        cursor.execute(query)
        users = cursor.fetchall()
        
        return {
            "message": "Lista de usuarios obtenida exitosamente",
            "users": users
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        connection.close()

@app.delete("/delete")
def delete_user(user: UserDelete):
    print(f"\n=== SOLICITUD DE ELIMINACIÓN PARA: {user.email} ===")
    
    connection = None
    cursor = None
    
    try:
        # 1. Establecer conexión con la base de datos
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 2. Verificar que el usuario existe
        cursor.execute("SELECT email, password FROM users WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()
        
        if not db_user:
            print(f"Usuario no encontrado: {user.email}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "El usuario no existe en nuestro sistema"
                }
            )
        
        # 3. Verificar contraseña (sin hash)
        if user.password != db_user['password']:
            print("Contraseña incorrecta")
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "message": "Contraseña incorrecta"
                }
            )
        
        # 4. Eliminar el usuario
        cursor.execute("DELETE FROM users WHERE email = %s", (user.email,))
        connection.commit()
        
        # 5. Verificar que se eliminó correctamente
        if cursor.rowcount == 1:
            print(f"Usuario eliminado: {user.email}")
            
            # Eliminar tokens asociados si existen
            try:
                cursor.execute("DELETE FROM password_tokens WHERE email = %s", (user.email,))
                connection.commit()
                print("Tokens asociados eliminados")
            except Exception as token_error:
                print(f"Error eliminando tokens: {str(token_error)}")
            
            return {
                "status": "success",
                "message": "Cuenta eliminada permanentemente"
            }
        else:
            print("No se pudo eliminar el usuario")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "No se pudo completar la eliminación"
                }
            )
            
    except mysql.connector.Error as db_error:
        print(f"Error de base de datos: {str(db_error)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Error en la base de datos",
                "error": str(db_error)
            }
        )
        
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Error interno del servidor",
                "error": str(e)
            }
        )
        
    finally:
        # Cerrar conexiones siempre
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("Conexión a BD cerrada")

@app.get("/")
def read_root():
    return {"message": "API de gestión de usuarios"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)