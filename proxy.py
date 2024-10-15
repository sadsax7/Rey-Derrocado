import threading
from concurrent import futures
import time
import grpc
import system_pb2
import system_pb2_grpc


followers_txt = "followers_vivos.txt"
def followers_txt_append(followers, file_name):
    """Cada follower en un archivo por si necesito ver quienes son y mandarles heartbeats"""
    with open(file_name, 'w') as f:
        for entry in followers:
            f.write(f"{entry}\n")

followers = {}
new_leader = False
leader_address = 'localhost:50052'
lock = threading.Lock()

class ProxyServiceServicer(system_pb2_grpc.ProxyServiceServicer):

    def RegisterFollower(self, request, context):
        global followers_txt
        # Agregar el seguidor a la lista de seguidores
        print(f"Follower: {request.address}\nCon conciencia: {request.awareness}\nIntentando registrarse...")
        followers[request.address] = request.awareness # {"puerto": conciencia}
        print("Registrado.")
        print(f"Followers: {followers}")
        followers_txt_append(followers, followers_txt)
        return system_pb2.RegisterResponse(message="Proxy: Registro exitoso")


    def Write(self, request, context):
        global new_leader_address
        global new_leader

        print("Escritura solicitada.")
        print(f"Datos recibidos para escritura: \n{request}")

        # Conectamos con el lider y le mandamos la solicitud de escritura
        if new_leader:
            with grpc.insecure_channel(new_leader_address) as channel:
                leader_stub = system_pb2_grpc.FollowerServiceStub(channel)
                response = leader_stub.Write(request)        
            return response
        else:
            with grpc.insecure_channel('localhost:50052') as channel:
                leader_stub = system_pb2_grpc.LeaderServiceStub(channel)
                response = leader_stub.Write(request)        
            return response


    def Read(self, request, context):
        print("Lectura Solicitada.")
        print(f"Solicitud de lectura recibida: {request.query}")
        # Conectar a un follower y redirigir la solicitud
        for follower, awareness in followers.items():
            if awareness == "vivo":
                print(f"Intentando enviar solicitud de lectura al follower: {follower}")
                try:    
                    with grpc.insecure_channel(follower) as channel:  # Puerto del follower
                        follower_stub = system_pb2_grpc.FollowerServiceStub(channel)
                        #Comprobar si el follower contiene data en el indice solicitado.
                        response = follower_stub.Read(request)  # Redirige la lectura al follower
                        if "fuera de rango" not in response.data: # Verficiamos si el indice si lo tenemos
                            print(f"Follower {follower} tiene informacion en el indice {request.index}.")
                            return response
                        else:
                            print(f"Follower {follower} no contiene informacion en el indice {request.index}.")
                except grpc.RpcError as error:
                    print(f"Error al intentar contactar con el {follower}\nError: {error}")
            else:
                # Si ningun follower tiene el indice solicitado, devuelve un mensaje de error
                return system_pb2.ReadResponse(data="Ningún follower tiene el índice solicitado.")
    

    def UpdateLeader(self, request, context):
        global new_leader_address
        global new_leader

        print(f"El lider ha muerto!")
        new_leader = True
        print(f"¡Ha llegado {request.leader_address} para destronarlo y volverse el lider!")
        new_leader_address = request.leader_address #actualizamos la direccion del nuevo lider
        return system_pb2.LeaderUpdateResponse(message="Líder actualizado exitosamente.")
    

    def HeartBeats(self, request, context):
        print(f"HeartBeat solicitado del cliente {request.id}.")
        print(request)
        print(f"Te enviare {request.beats} latidos.")
        for i in range(request.beats):
            latido_enviado = system_pb2.WriteResponse()
            latido_enviado.message = f"Oye {request.id} soy el ProxyApp llevo {i + 1} latidos"
            yield latido_enviado
            time.sleep(3)


    def ClienteVivo(self, request_iterator, context):
        latido_retrasado = system_pb2.LatidosRecibidos()
        for request in request_iterator:
            print("Cliente pidio escribir en el log.")
            print(request)
            latido_retrasado.request.append(request)
        
        latido_retrasado.message = f"Has mandado {len(latido_retrasado.request)} mensajes. Porfavor espera una respuesta mas lenta."
        return latido_retrasado


    def Bidireccional(self, request_iterator, context):
        for request in request_iterator:
            print("Escritura pedida, recibido.")
            print(request)

            enviar_mensaje = system_pb2.WriteResponse()
            enviar_mensaje.message = f"{request.name} --> {request.data}"

            yield enviar_mensaje


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    system_pb2_grpc.add_ProxyServiceServicer_to_server(ProxyServiceServicer(), server)
    server.add_insecure_port("localhost:50051")
    print(f"Proxy escuchando en el puerto 50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
