# Coordinación entre procesos en un Sistema Distribuido

La coordinación y la consistencia entre los procesos dentro de un sistema distribuido es de suma importancia para el mejor funcionamiento de una aplicación, pues la sincronización entre todos los procesos, permiten el buen funcionamiento del conjunto/sistema, permitiendo que cada proceso funcione en simultaneo o asincronicamente con los demas componentes del sistema, permitiendo acceder a distintas funcionalidades o actuar en el momento que se desee.

## Detalles del proyecto:

- **Materia:** Tópicos Especiales en Telemática - ST0263
- **Estudiantes:**
  - Alejandro Arango Mejía: aarangom1@eafit.edu.co
  - Thomas Rivera Fernández: triveraf@eafit.edu.co
- **Profesor:** Juan Carlos Montoya Mendoza: jcmontoy@eafit.edu.co

### 1. Descripcion:

Este proyecto intenta resolver algunas principales problematicas que son **Coordinación entre procesos**, **Fallas en los procesos** y **Consistencia en los datos a traves del tiempo** en un **sistema distribuido o aplicación**; Las fallas o problematicas se han solucionado con nuestro propia perspectiva del problema e hicimos nuestro propio algortimo sin necesidad de utilizar librerias, aún asi, se ha intentado abordar inspirandonos en un famoso algoritmo llamado Raft: [text](https://raft.github.io/raft.pdf) el cual nos permitio:
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
