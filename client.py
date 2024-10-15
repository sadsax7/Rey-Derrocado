import system_pb2_grpc
import system_pb2
import time
import grpc


def mandar_varias_peticiones_de_escritura():

    while True:
        nombre = input("Ingresa tu nombre o identificador(o nada y dele a 'ENTER' para parar peticiones): ")

        if nombre == "":
            break

        datos = input("Que datos quieres registrar en el log?:\n")
        peticion = system_pb2.WriteRequest(name = nombre, data = datos)
        yield peticion
        time.sleep(1)


def run():

    operar = True
    while operar:
        with grpc.insecure_channel('localhost:50051') as channel:
            #port = input("Ingrese el puerto al cual se quiere conectar (50051, 50052, 50053 hasta el 50061):\n")
            #channel = system_pb2_grpc.insecure_channel(f'localhost:{port}')
            stub = system_pb2_grpc.ProxyServiceStub(channel) # stub es un intermediario para llamar metodos del Proxyservice
            print("¿Qué desea hacer?")
            print("1. Operacion de escritura.")
            print("2. Operacion de lectura.")
            """
            print("3. HearBeat del Server - proxy envia latidos en streaming al cliente.")
            print("4. HearBeat del Cliente - cliente envia latidos en streaming al proxy.")
            print("5. Bidireccional - Ambos se envian latidos en streaming.")
            """
            
            accion = input("¿ Que decidiste hacer? #")

            if accion == '1':
                nombre = input("Ingresa tu id o nombre:\n")
                data = input("Que datos quieres registrar en el log?\n")
                datos = system_pb2.WriteRequest(name = nombre, data = data)
                respuestas = stub.Write(datos)
                print(f"Respuesta del proxy recivida: {respuestas}")

            elif accion == '2':
                indice = int(input("Indice al cual desea acceder: "))
                lectura = input("Que desea ver de la base de datos?: [todo/nada] ")
                read_request = system_pb2.ReadRequest(index = indice, query = lectura)
                respuesta = stub.Read(read_request)
                print(f"Respuesta del proxy-->follower: {respuesta.data}")

            elif accion == '3':
                beats_pedidos = int(input("Ingresa el numero de beats que quieres recibir del proxy: "))
                id_nombre = input("Ingresa tu id o nombre: ")
                latido_solicitado = system_pb2.Beats(id = id_nombre, beats = beats_pedidos)
                respuestas = stub.HeartBeats(latido_solicitado)
                
                for respuesta_del_latido in respuestas:
                    print("Latido del proxy recibido.")
                    print(respuesta_del_latido)

            elif accion == '4':
                señal_de_conexion = stub.ClienteVivo(mandar_varias_peticiones_de_escritura())

                print("Ya no quiero madnar mas cosas. ")
                print(f"Esto fue lo que mande:\n{señal_de_conexion}")
            
            elif accion == "5":
                respuestas = stub.Bidireccional(mandar_varias_peticiones_de_escritura())
                for respuesta in respuestas:
                    print("LatidosBidireccionales solicitados.")
                    print(respuesta)

            else:
                print("Acción no válida")
                comando = True
                while comando:
                    operar = input("¿ Desea seguir haciendo operaciones de (escritura/lectura) ?: \nResponda con [y/n]")
                    if operar in ["y", "n"]:
                        if operar  == "y":
                                comando = False
                                continue
                        else:
                            operar = False
                    else:
                        print("No se reconoce ese comando\nIntente de nuevo.")


if __name__ == '__main__':
    run()