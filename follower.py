import threading
from concurrent import futures
import grpc
import system_pb2
import system_pb2_grpc
import random
import time

#Por si el follwer se vuelve lider
current_term = 0
current_follower_port = ""
quorum = False
election_in_progress = False

# Variables para el manejo de latidos y timeout
leader_alive = True  # Inicialmente asumimos que el líder está vivo
timeout_interval = random.uniform(15, 40)  # Timeout aleatorio entre 150ms y 300ms
last_heartbeat_time = time.time()

# Datos replicados 
log_replicated = []
log_lock = threading.Lock()

#lista de puertos usados por cada follower que se conecta.
puertos_usados = []

log_file_path = "leader_log.txt"
def write_log_to_file(log, file_name):
    """Cada ecritura la hace en un archivo txt y asi tener un log en disco."""
    with open(file_name, 'w') as f:
        for entry in log:
            term, index, data = entry
            f.write(f"{term}, {index}, {data}\n")

def load_log_from_file(file_name):
    global current_term
    fresh_log = []
    try:
        with open(file_name, 'r') as f:
            for line in f:
                term, index, data = line.strip().split(',')
                fresh_log.append((int(term), int(index), data))
    except FileNotFoundError:
        print("Error: ERROR DE LECTURA DE ARCHIVO")

    if fresh_log:
        current_term = fresh_log[-1][0] # actualizo el ultimo term que habia en el log del lider
    else:
        current_term = 0 

    return fresh_log


lista_followers = 'followers_vivos.txt'
def load_followers(file_name):
    otros_followers = []
    try:
        with open(file_name, 'r') as f:
            for line in f:
                address = line.strip().split(',')
                otros_followers.append(address)
    except FileNotFoundError:
        print("Error: ERROR DE LECTURA DE ARCHIVO")

    return otros_followers


class FollowerServiceServicer(system_pb2_grpc.FollowerServiceServicer):

    def Write(self, request, context):
        global indice
        global log_replicated
        global lista_followers

        indice = len(log_replicated)
        consenso = False 
        confirmaciones = 0
        confirmaciones_denegadas = 0

        print(f"El Proxy me envio peticion de Escritura")
        print(f"por parte del cliente: {request.name}")
        print(f"Quiere guardar: {request.data}")
        escritura = (current_term, len(log_replicated) + 1, request.data)
        #Escribir en el log y persistir en leader_log.txt
        with log_lock:
            log_replicated.append(escritura)
            write_log_to_file(log_replicated, log_file_path)
        print(f"Log modificado: {log_replicated}")

        lista_de_followers = load_followers(lista_followers)

        #Replicar la escritura a los seguidores vivos y hacer un CONSENSO y COMPROMETER la entrada
        while not consenso:
            print("Se intentara llegar a un CONSENSO (mayoria de replicas en followers).")
            if lista_de_followers:
                for puerto in lista_de_followers:
                    if puerto[0] != f"localhost:{current_follower_port}":
                        print(f"Enviando peticion de replica al follower: {puerto}")
                        try:
                            with grpc.insecure_channel(puerto[0]) as channel:
                                stub = system_pb2_grpc.FollowerServiceStub(channel)
                                replication_request = system_pb2.ReplicationRequest(name = request.name, term = current_term, index = indice, data = f"{request.data}")
                                response = stub.Replicate(replication_request)

                                #Verificamos si hay desincronizacion
                                if "Desincronizacion" in response.message:
                                    follower_index = response.follower_index
                                    print(f"Follower {puerto} desincronizado, Iniciando proceso de sincronizacion...")
                                    sync_thread = threading.Thread(target=sync_follower, args=(puerto[0], follower_index))
                                    sync_thread.start()
                                # follower sincronizado    
                                confirmaciones += 1
                                print(f"Replica exitosa con {puerto}: {response.message}")
                                
                        except grpc.RpcError as error:
                            print(f"Error al intentar replicar con el {puerto}\nError: {error}")

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
        message_reply.message = f"Escitura completada en el log: {log_replicated}"
        return message_reply
        

    def Read(self, request, context):
        with log_lock:
            print("El proxy me esta pidiendo Leer datos.")
            print(f"peticion: {request}")
            print(f"Desea ver {request.query} del indice {request.index}")

            # Lectura de datos
            if 0 <= request.index < len(log_replicated):
                log_entry = log_replicated[request.index]
                print(f"Lo que hay en log_replicated[{request.index}] = {log_entry}")
                response = system_pb2.ReadResponse(data = f"{log_entry}")
            else:
                response = system_pb2.ReadResponse(data = f"Indice fuera de rango del Log.")

        return response
    
    
    def Replicate(self, request, context): 
        #Tenemos el log mas fresco desde el disco
        freshest_log = load_log_from_file(file_name = 'leader_log.txt')
        
        #Replica del log --> follower por follower
        with log_lock:
            print("El lider me envio una solicitud de replicacion del log")
            print(f"Datos recibidos de {request.name}: {request.data}")
            print(f"Datos para replicar: {request}")

            #Verificar si el indice del follower esta desincronizado
            if request.index != len(log_replicated):
                print(f"Log del leader: {freshest_log}")
                print(f"Log mio: {log_replicated}")
                print(f"Intentando replicar entrada: {freshest_log[request.index]}...")
                error_message = f"Desincronizacion detectada. Mi log tiene índice {len(log_replicated)} pero el líder quiere replicar índice {request.index}."
                print(error_message)
                return system_pb2.ReplicationResponse(message=error_message, follower_index = len(log_replicated))
            
            #Agregar la entrada replicada al log de Follower
            log_replicated.append((request.term, request.index, request.data))
            print(f"Replica del log: {log_replicated}")
            #Responder al lider: Replicacion exitosapo
            response = system_pb2.ReplicationResponse(message="Replicacion exitosa en follower.")
        return response
    
    
    def ReceiveHeartBeats(self, request, context):
        global last_heartbeat_time
        global election_in_progress
        global leader_alive

        # Verificar si el latido llegó
        if not request.beats_request:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Mensaje vacío recibido.")
            return system_pb2.HeartBeatsResponse(beats_received="Error: No me llego un latido del LEADER.")

        print(f"Latido recibido del líder: {request.beats_request}, {request.leader_state}")
        
        last_heartbeat_time = time.time() #reincio cronometro cada vez que llega latido
        leader_alive = request.leader_state  # Monitoreo del utlimo latido
        if not leader_alive:
            election_in_progress = False #No hay lider, no hay elecciones, veamos si se comienza una

        return system_pb2.HeartBeatsResponse(beats_received="Heartbeat recibido correctamente")
    

    def VoteRequest(self, request, context):
        global current_term
        global log_replicated
        global leader_alive

        # Si ya hay un líder establecido, no se concede el voto.
        print(f"Estado del lider: {leader_alive}")
        if leader_alive:
            print("Ya hay un líder. No puedo conceder votos.")
            return system_pb2.Vote(vote=0)
        
        print(f"Solicitud de voto recibida. Longitud del log del candidato: {request.len_log}, mi log: {len(log_replicated)}")
        # Si el log del candidato es más actualizado o igual, voto a favor
        if request.len_log >= len(log_replicated):
            response = system_pb2.Vote(vote=1)
            print("Voto concedido.")
        else:
            response = system_pb2.Vote(vote=0)
            print("Voto rechazado, mi log es más actualizado.")
        
        return response


def sync_follower(follower, follower_index):
    """Función que se ejecuta en un hilo separado para sincronizar el log a un follower desincronizado."""
    global log_replicated

    print(f"Iniciando actualización del follower {follower}, que está desincronizado.")
    
    try:
        with grpc.insecure_channel(follower) as channel:
            stub = system_pb2_grpc.FollowerServiceStub(channel)
            # Enviar las entradas faltantes al follower desincronizado
            for i in range(follower_index, len(log_replicated)):
                with log_lock:
                    term, index, data = log_replicated[i]
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



def send_heartbeats():
    """Función para enviar heartbeats a los followers."""
    global leader_alive
    global puertos_usados
    global lista_followers


    while leader_alive:
        lista_txt_followers = load_followers(lista_followers)
        for puerto in lista_txt_followers:
            if puerto[0] != f"localhost:{current_follower_port}":
                try:
                    with grpc.insecure_channel(puerto[0]) as channel:
                        stub = system_pb2_grpc.FollowerServiceStub(channel)
                        heartbeat = system_pb2.HeartBeat(beats_request=f"<3 {current_follower_port} <3 NUEVO <3 LIDER <3", leader_state=True)
                        response = stub.ReceiveHeartBeats(heartbeat)
                        #print(f"Heartbeat enviado a {puerto}: {response.beats_received}")
                except grpc.RpcError as error:
                    print(f"Error enviando heartbeat a {puerto}: {error}")
        time.sleep(2.2)  # Intervalo entre heartbeats

def election_timeout():
    """Función para manejar el timeout y detectar/monitorear la muerte del líder."""
    global leader_alive
    global timeout_interval
    global last_heartbeat_time
    global election_in_progress

    while True:
        current_time = time.time()
        time_since_last_heartbeat = current_time - last_heartbeat_time

        if leader_alive:
            election_in_progress = True

        if time_since_last_heartbeat >= timeout_interval and not election_in_progress:
            print("Timeout alcanzado, parece que el líder ha muerto.")
            leader_alive = False
            start_election()

        time.sleep(0.07)


def start_election():
    global puertos_usados
    global leader_alive
    global current_term
    global quorum
    global election_in_progress
    global lista_followers

    lista_de_followers = load_followers(lista_followers)
    print(f"followers que tengo que pedir el voto: {lista_de_followers}")

    if election_in_progress:
        print("Ya hay una eleccion de nuevo lider en progreso...")
        return "ya hay lider."

    election_in_progress = True
    
    current_term += 1  # Incrementa el término actual al convertirse en candidato
    votes_received = 1  # Empieza votando por sí mismo
    print(f"El líder ha muerto. Iniciando elección en el término {current_term}.")

    # Enviar solicitudes de voto a todos los demás seguidores
    for puerto in lista_de_followers:
        #print(f"{puerto} - localhost:{current_follower_port}")
        if puerto[0] != f"localhost:{current_follower_port}":
            try:
                # aca deberia de mandar heartbeat para avisar que es candidato
                with grpc.insecure_channel(puerto[0]) as channel:
                    stub = system_pb2_grpc.FollowerServiceStub(channel)
                    heartbeat_message = system_pb2.HeartBeat(beats_request = f"-_-{current_follower_port}-_- <3 Candidato a lider <3 NUEVO <3 " , leader_state = True)
                    stub.ReceiveHeartBeats(heartbeat_message)

            except grpc.RpcError as error:
                print(f"Error al enviar heartbeat al follower {puerto}: {error}")

            try:
                with grpc.insecure_channel(puerto[0]) as channel:
                    stub = system_pb2_grpc.FollowerServiceStub(channel)
                    request = system_pb2.LenLog(len_log=len(lista_de_followers))  # Enviar longitud del log
                    response = stub.VoteRequest(request)

                    if response.vote == 1:  # Si el follower vota a favor
                        votes_received += response.vote
                        print(f"Voto recibido de {puerto}")
            except grpc.RpcError as error:
                print(f"Error solicitando voto de {puerto}: {error}")

    # Verificar si se obtuvo la mayoría de votos
    if votes_received >= len(lista_de_followers) // 2:
        # Iniciar el envío de heartbeats en un hilo separado
        #threading.Thread(target=send_heartbeats, daemon=True).start()  # Iniciar el hilo de heartbeats
        leader_alive = True
        print("aca se deberia de inciar el hilo de heartbeats")
        heartbeat_thread_obj = threading.Thread(target=send_heartbeats)
        heartbeat_thread_obj.daemon = True
        heartbeat_thread_obj.start()
        
        print("Se ha llegado a un QUORUM")
        print(f"Votos recibidos <--- {votes_received} >= { len(lista_de_followers) // 2 } ---> La Mayoria de Followers")
        print(f"Soy el nuevo líder en el término {current_term} con {votes_received} votos.")
        # Aquí puedes añadir la lógica para que el follower se convierta en líder
        # 1. Notificamos al proxy del nuevo lider
        proxy_has_a_leader  = notify_proxy_new_leader()
        if proxy_has_a_leader:
            print("Definitivamente ya soy el lider, wow.")
    else:
        print("No se obtuvo la mayoría de votos. Permaneceré como follower.")
        time.sleep(random.uniform_(1, 3))
        election_in_progress = False


def notify_proxy_new_leader():
    print("Intentado notificar al proxy que he derrocado al anterior lider...")
    try:
        # Crear una conexión con el Proxy
        with grpc.insecure_channel('localhost:50051') as channel:
            proxy_stub = system_pb2_grpc.ProxyServiceStub(channel)
            # Crear el mensaje con la nueva dirección del líder
            leader_info = system_pb2.LeaderInfo(leader_address=f"localhost:{current_follower_port}")
            # Enviar la actualización del líder al Proxy
            response = proxy_stub.UpdateLeader(leader_info)
            print(f"Respuesta del Proxy al actualizar el líder: {response.message}")
            return True
    except grpc.RpcError as error:
        print(f"Error registrandome con el Proxy: {error}")
        return False   



def register_with_leader_and_proxy(port):
    puerto = f"localhost:{port}"
    conciencia = input("¿Estas vivo o muerto?: ").lower()

    try:
        # Registro con el lider
        print(f"Follower con puerto {puerto} intentando conectarse al lider...")
        with grpc.insecure_channel('localhost:50052') as channel:  # Puerto del líder
            stub = system_pb2_grpc.LeaderServiceStub(channel)
            request = system_pb2.RegisterRequest(address = puerto, awareness = conciencia)  # Dirección del follower 50053
            response = stub.RegisterFollower(request)
            print(f"Registro en el líder: {response.message}")
    except grpc.RpcError as error:
        print(f"Error registrandome con el lider: {error}")
    
    try:
        # Registro con el Proxy 
        print(f"Follower con puerto {puerto} intentando conectarse al Proxy...")
        with grpc.insecure_channel('localhost:50051') as channel:  # Puerto del líder
            stub = system_pb2_grpc.ProxyServiceStub(channel)
            request = system_pb2.RegisterRequest(address = puerto, awareness = conciencia)  # Dirección del follower 50053
            response = stub.RegisterFollower(request)
            print(f"Registro en el Proxy: {response.message}")
    except grpc.RpcError as error:
        print(f"Error registrandome con el Proxy: {error}")


def serve():
    global current_follower_port
    global leader_alive
    global puertos_usados

    #Primero cada follower se registra con el lider y el Proxy
    print("Puertos disponibles para ingresar a la red con el Lider y Proxy: (50053, 50054, 50055, ...., 60000)")
    current_follower_port = input("Ingrese el puerto o direccion suya:  ")  
    while current_follower_port in puertos_usados:
        print("Ese puerto ya esta en uso.")
        current_follower_port = input("Ingrese el puerto o direccion: (50053, 50054, 50055, ...., 60000):  ")
    print(f"current_follower_port: {current_follower_port}")
    #Con este puerto, nos registramos en el Lider y el Proxy
    register_with_leader_and_proxy(current_follower_port)
    # Solo después de un registro exitoso, agregamos el puerto a puertos_usados
    puertos_usados.append(f"localhost:{current_follower_port}")
    print(f"Puertos utilizado por followers: {puertos_usados}")
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    system_pb2_grpc.add_FollowerServiceServicer_to_server(FollowerServiceServicer(), server)
    server.add_insecure_port(f"localhost:{current_follower_port}")  # Puerto para el follower
    print(f"Seguidor escuchando en el puerto {current_follower_port}")

    # Iniciar el hilo de detección de timeout
    timeout_thread = threading.Thread(target=election_timeout)
    timeout_thread.daemon = True
    timeout_thread.start()

    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()