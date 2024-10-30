# Coordinación entre procesos en un Sistema Distribuido

La coordinación y la consistencia entre los procesos dentro de un sistema distribuido es de suma importancia para el mejor funcionamiento de una aplicación, pues la sincronización entre todos los procesos, permiten el buen funcionamiento del conjunto/sistema, permitiendo que cada proceso funcione en simultaneo o asincronicamente con los demas componentes del sistema, permitiendo acceder a distintas funcionalidades o actuar en el momento que se desee.

## Detalles del proyecto:

- **Materia:** Tópicos Especiales en Telemática - ST0263
- **Estudiantes:**
  - Alejandro Arango Mejía: aarangom1@eafit.edu.co
  - Thomas Rivera Fernández: triveraf@eafit.edu.co
- **Profesor:** Juan Carlos Montoya Mendoza: jcmontoy@eafit.edu.co
- **Video explicativo:** https://eafit.sharepoint.com/sites/alejo/_layouts/15/stream.aspx?id=%2Fsites%2Falejo%2FDocumentos%20compartidos%2FGeneral%2FRecordings%2FAlgoritmo%20Raft%2D20241030%5F150820%2DGrabaci%C3%B3n%20de%20la%20reuni%C3%B3n%2Emp4&referrer=StreamWebApp%2EWeb&referrerScenario=AddressBarCopied%2Eview%2E091e07cb%2D426f%2D4a7c%2D905b%2D3400b0920f94

### 1. Descripcion:

Este proyecto intenta resolver algunas principales problematicas que son **Coordinación entre procesos**, **Fallas en los procesos** y **Consistencia en los datos a traves del tiempo** en un **sistema distribuido o aplicación**; Las fallas o problematicas se han solucionado con nuestro propia perspectiva del problema e hicimos nuestro propio algortimo sin necesidad de utilizar librerias, aún asi, se ha intentado abordar inspirandonos en un famoso algoritmo llamado Raft: (https://raft.github.io/raft.pdf) el cual nos permitio:
- *coordinar* los procesos Proxy, Leader y Followers --> mecanismo:(**CONSENSO**)
- *tolerar caidas* de Leader o Followers --> mecanismo:(**VOTACIÓN DEL LIDER o REVIVIR LIDER/FOLLOWER**)
- **datos consistentes/persistentes** ya que estan replicados por el sistema en los follower con un --> datos:(**LOG**)


#### 1.1. Aspectos Logrados:
  - Aplicación **Cliente** que se comunica con un Proxy para hacer operaciones de escritura se realizan en el lider y las operaciones de lectura se hacen contra los followers.
  -  Aplicación **Proxy** a nivel de aplicación que intercepta las solicitudes de la aplicación cliente y las dirige a los procesos encargados del almacenamiento(lider) y la replicaciónn de datos(followers)
  - Aplicación **Leader** el cual es el lider de la base de datos y de coordinar las operaciones de escritura para asegurar la consistencia de los datos.
  -Aplicación **Follower**, son procesos los cuales mantienen las réplicas mas frescas del estado de la base de datos respondiendo a la solicitud del lider para replicar las actualizaciones en su base de datos, ademas, tambien proporcionan informacion al cliente accediendo a la base de datos.
  - El sistema es capaz de detectar la falla del líder de manera automática.
  - El sistema es capaz de detectar la falla de algun follower de manera automática.
  - **Tolerancia a fallos** en el sistema. En caso de que el proceso ́líder falle, uno y solo uno de los followers asume el rol de líder para asegurar la continuidad del servicio, garantizando la consistencia en la replicación de la base de datos.
  - El nuevo líder asumie su rol sin perder las solicitudes del cliente y sin comprometer la consistencia de los datos.
  - La elección de un nuevo líder es manera automática y coordinada entre los followers restantes, ademas, esta elección es democratica.
  - Capacidad de **Simulación de fallos** para demostraciones ante caidas de procesos.

#### 1.2. Aspectos NO Logrados
  - Despliegue en AWS.
  - Caida del Proxy.

### 2. Información general de diseño:
  - **Diseño**
    - Cliente **--> envia** peticiones a un **Proxy** (peticiones de **escritura** o **lectura** de la DB).
    - Proxy **--> reedirige** las peticiones a --> Leader(escritura)/Follower(lectura).
    - Leader **-->** recibe la petición de escritura, **guarda la informacion en un log/base de datos y replica la información con los followers**.
    - Follower **-->** recibe la petición de lectura, **accede a los datos que el cliente quiere ver de la base de datos y se los muestra**.

  - **Arquitectura**
    - **Leader/Follower P2P**: La aplicacion leader no comparte las funcionalidades de la del follower, pero las del follower si tiene sus propias funcionalidades, ademas de las del lider en caso de alguna falla, para el follower poder reemplazarlo.
    - **Cliente/Servidor**: Cliente hace peticiones a un Proxy el cual es un intermediario entre el cliente y el lider/follower y estos le proporcionan el serivio de escritura/lectura en/de la base de datos, esta relacion podria decirse que es Cliente/Servidor

- **Mejores practicas utilizadas**
  - **gRPC para Comunicación**: Utilización de gRPC para implementar las interfaces cliente-servidor de manera eficiente, facilitando la comunicación entre nodos.
  - **Protobuf**: Para la serialización de datos en la comunicación entre nodos, lo que permite transferir estructuras complejas.
  - **Concurrencia**: El lider/follower utilizan threading para manejar múltiples solicitudes al mismo tiempo o sincronizarse para el tener los datos mas actualizados.
  - **Resiliencia y Escalabilidad**: Los followers/lideres se unen o se retiran sin generar interrupciones en el servicio


## Tecnologias usadas:

- **Python**: Lenguaje de programación.
- **gRPC**: Permite la comunicación entre nodos.
- **Protocol Buffers (Protobuf)**: Serializa datos estructurados.

## Estructura del proyecto

```bash
.
├── Reinado              
├── __pycache__                       
│   ├── node_pb2_grpc.cpython-311.pyc                
│   └── node_pb2.cpython-311.pyc                
├── design                       
│   ├── Arquitectura.png                
│   └── Estructura del proyecto.pdf               
├── client.py
├── proxy.py
├── leader.py
├── follower.py
├── system_pb2_grpc.py
├── system_pb2_grpc.py
├── system_pb2.py
├── node.proto
└── README.md                    
```

## Setup e Instalación
# Ambiente de Desarrollo:
  - **Lenguaje**: Python 3.9
  - **Librerías y Paquetes**:
    - **grpcio** (version 1.39.0)
    - **protobus** (version 3.17.3)
    - **threading**: Para la ejecución en paralelo de hilos.
    - **time**: Para coordinar procesos

### 1. Clonar el repositorio

```bash
git clone [text](https://github.com/sadsax7/Rey-Derrocado.git)
cd Reinado
```

### 2. Instalar python y las dependecias
- Descargar **python** desde: [text](https://www.python.org/downloads/)
- **Dependencias**:
```bash
pip install grpcio grpcio-tools protobuf
```

### 3. Compilar archivos generados por **protobuf**

Estando en la ruta del proyecto desde la terminal, ejecutar:

```bash
cd Reinado
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. node.proto
```

### 4. Ejecutar con el comando:

- **Cliente**
```bash
python client.py
```
- **ProxyApp**
```bash
python proxy.py
```
- **Leader/King**
```bash
python leader.py
```

Para ingresar a 'n' follower, asigna un nuevo puerto para cada follower (ejemplo: `50053`, `50054`, .... , `60000`).
- **Follower**
```bash
python follower.py
```
puerto --> 50053
conciencia --> (vivo/muerto)

### 5. Unir a la red otro follower. (Hacer para cada follower que se quiera agregar, pero en distintas terminales)

```bash
python follower.py
```
puerto --> 50054
conciencia --> (vivo/muerto)


### 6. Escritura o Lectura de la base de datos desde el cliente:

Al estar en cualquiera de los clientes creados, surgira el siguiente menú:
Oprimir la que quiera hacer: (1/2)
```
-----------------------------------
| 1: Operación de escritura       |
| 2: Operación de lectura         |
-----------------------------------
```

### Referencias
- (https://www.youtube.com/watch?v=WB37L7PjI5k)
- (https://raft.github.io/raft.pdf)
- Visualización de funcionamiento del algoritmo: (https://raft.github.io/)
- Video de youtube del los creadores del **algoritmo Raft**: (https://www.youtube.com/watch?v=YbZ3zDzDnrw), (https://www.youtube.com/watch?v=vYp4LYbnnW8)
- (https://www.youtube.com/watch?v=IujMVjKvWP4)


