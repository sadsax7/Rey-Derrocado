import threading
from concurrent import futures
import grpc
import system_pb2
import system_pb2_grpc
import time

leader_alive = True # Leader vivo(True) o muerto(False)
current_term = 1 # Termino actual, puede ir cambiando
indice = 0 # Indice inical del log (una lista)
log_lock = threading.Lock()
log = [] # [(term, index, data)]
followers = {}

log_file_path = "leader_log.txt"
def write_log_to_file(log, file_name):
    """Cada ecritura la hace en un archivo txt y asi tener un log en disco."""
    with open(file_name, 'w') as f:
        for entry in log:
            term, index, data = entry
            f.write(f"{term}, {index}, {data}\n")


class LeaderServiceServicer(system_pb2_grpc.LeaderServiceServicer):

    def RegisterFollower(self, request, context):

        # Agregar el seguidor a la lista de seguidores
        print(f"Follower: {request.address}\nCon conciencia: {request.awareness}\nIntentando registrarse...")
        followers[request.address] = request.awareness # {"puerto": conciencia}
        print("Registrado.")
        print(f"Followers: {followers}")
        #escribo los followers
        return system_pb2.RegisterResponse(message="Registro exitoso")


    def Write(self, request, context):
        global indice
        consenso = False 
        confirmaciones = 0
        confirmaciones_denegadas = 0

        print(f"El Proxy me envio peticion de Escritura")
        print(f"por parte del cliente: {request.name}")
        print(f"Quiere guardar: {request.data}")
        escritura = (current_term, indice, request.data)
        #Escribir en el log y persistir en leader_log.txt
        with log_lock:
            log.append(escritura)
            write_log_to_file(log, log_file_path)
        print(f"Log modificado: {log}")

        #Replicar la escritura a los seguidores vivos y hacer un CONSENSO y COMPROMETER la entrada
        while not consenso:
            print("Se intentara llegar a un CONSENSO (mayoria de replicas en followers).")
            if followers:
                for follower, awareness in followers.items():
                    if awareness == "vivo":
                        print(f"Enviando peticion de replica al follower: {follower}")
                        try:
                            with grpc.insecure_channel(follower) as channel:
                                stub = system_pb2_grpc.FollowerServiceStub(channel)
                                replication_request = system_pb2.ReplicationRequest(name = request.name, term = current_term, index = indice, data = f"{request.data}")
                                response = stub.Replicate(replication_request)

                                #Verificamos si hay desincronizacion
                                if "Desincronizacion" in response.message:
                                    follower_index = response.follower_index
                                    print(f"Follower {follower} desincronizado, Iniciando proceso de sincronizacion...")
                                    sync_thread = threading.Thread(target=sync_follower, args=(follower, follower_index))
                                    sync_thread.start()
                                # follower sincronizado    
                                confirmaciones += 1
                                print(f"Replica exitosa con {follower}: {response.message}")
                                
                        except grpc.RpcError as error:
                            print(f"Error al intentar replicar con el {follower}\nError: {error}")
                    else:
                        confirmaciones_denegadas += 1
                        print(f"El follower {follower} está marcado como muerto. No se hace la replica.")

                if confirmaciones >= confirmaciones_denegadas:
                    print(f"(Confirmaciones) <---- {confirmaciones} >= {confirmaciones_denegadas} --- >(Confirmaciones Denegadas)")
                    print("CONSENSUS REACHED / CONSENSO ALCANZADO")
                    print("LOG COMPROMETIDO.")
                    consenso = True
                else:
                    print("No se llego a un CONSENSO/CONSENSUS.")
                    print(f"Solo se logo hacer la replica en {confirmaciones} followers")
                    print(f"Los {confirmaciones_denegadas} demas, no me enviaron confirmacion de replica (puede que esten muertos)")
                    consenso = True

            else:
                consenso = True
            
        indice += 1
        #Respuesta al cliente:
        message_reply = system_pb2.ReplicationResponse()
        message_reply.message = f"Escitura completada en el log: {log}"
        return message_reply
        

def sync_follower(follower, follower_index):
    """Función que se ejecuta en un hilo separado para sincronizar el log a un follower desincronizado."""
    global log

    print(f"Iniciando actualización del follower {follower}, que está desincronizado.")
    
    try:
        with grpc.insecure_channel(follower) as channel:
            stub = system_pb2_grpc.FollowerServiceStub(channel)
            # Enviar las entradas faltantes al follower desincronizado
            for i in range(follower_index, len(log)):
                with log_lock:
                    term, index, data = log[i]
                    replication_request = system_pb2.ReplicationRequest(
                        name="leader", 
                        term=term, 
                        index=index, 
                        data=data
                    )
                    response = stub.Replicate(replication_request)
                    #No se pudo sincronizar
                    if "Desincronizacion" in response.message:
                        print(f"Error de sincronización adicional con {follower}: {response.message}")
                        break
                    #Se pudo sincronizar
                    print(f"Replica exitosa de la entrada {i} al follower {follower}")

    except grpc.RpcError as error:
        print(f"Error durante la actualización del follower {follower}: {error}")
    
    print(f"Follower {follower} actualizado correctamente.")


def heartbeat_thread():
    """Envía heartbeats periódicamente a todos los followers vivos."""
    while leader_alive:
        if followers:
            for follower, awareness in followers.items():
                #print(f"{follower}: {awareness}")
                if awareness == "vivo":
                    #print(f"Enviando Heartbeat al follower {follower}")
                    try:
                        with grpc.insecure_channel(follower) as channel:
                            stub = system_pb2_grpc.FollowerServiceStub(channel)
                            heartbeat_message = system_pb2.HeartBeat(beats_request = "<3..BOOM..BOOM..<3 del lider", leader_state = True)
                            stub.ReceiveHeartBeats(heartbeat_message)
                    except grpc.RpcError as error:
                        print(f"Error al enviar heartbeat al follower {follower}: {error}")
        time.sleep(3)  # Heartbeat cada 3 segundos



def manage_followers_and_leader():
    """Permite al líder cambiar la conciencia de los followers y de si mismo manualmente."""
    global leader_alive
    while True:
        if followers:
            print(f"Followers actuales y su estado: {followers}\n")
            follower_address = input("...EN CUALQUIER MOMENTO PUEDES...\n -Matar o revirir algun follower: ('localhost:puerto')\n -Morirte: ('renuncio')\n -Revivir: ('revivo')\n...Cuando tu quieras...\n ")

            if follower_address == "renuncio":
                #Envio mi ultimo latido, para avisar que he muerto
                for follower, awareness in followers.items():
                    #print(f"{follower}: {awareness}")
                    if awareness == "vivo":
                        #print(f"Enviando Heartbeat al follower {follower}")
                        try:
                            with grpc.insecure_channel(follower) as channel:
                                stub = system_pb2_grpc.FollowerServiceStub(channel)
                                heartbeat_message = system_pb2.HeartBeat(beats_request = "x_x Leader </3 muerto x_x" , leader_state = False)
                                stub.ReceiveHeartBeats(heartbeat_message)
                        except grpc.RpcError as error:
                            print(f"Error al enviar heartbeat al follower {follower}: {error}")

                leader_alive = False #muero
                print("Estoy muerto x_x. Mis latidos pararan...")

            elif follower_address == "revivo":
                leader_alive = True #revivo
                heartbeat_thread_obj = threading.Thread(target=heartbeat_thread)
                heartbeat_thread_obj.daemon = True
                heartbeat_thread_obj.start()
                print("!BOOM-BOOM! !BOOM_BOOM¡\nMi <3 late nuevamente! \nEnviare a los followers mis latidos...")

            elif follower_address in followers:
                new_state = input(f"¿Nuevo estado para {follower_address}? (vivo/muerto): ")
                followers[follower_address] = new_state
                print(f"Estado de {follower_address} cambiado a {new_state}.")

            else:
                print("Follower no encontrado.")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    system_pb2_grpc.add_LeaderServiceServicer_to_server(LeaderServiceServicer(), server)
    server.add_insecure_port("localhost:50052")
    print("Lider escuchando en el puerto 50052")

    # Iniciar el envío de heartbeats en un hilo separado
    heartbeat_thread_obj = threading.Thread(target=heartbeat_thread)
    heartbeat_thread_obj.daemon = True
    heartbeat_thread_obj.start()

    # Iniciar la gestión manual de followers en otro hilo
    manage_followers_thread = threading.Thread(target=manage_followers_and_leader)
    manage_followers_thread.daemon = True
    manage_followers_thread.start()

    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()