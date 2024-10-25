import socket
import time
import threading
import json
import os

class Peer_Node:
    @staticmethod
    def peer_node(node_id, config, topology, all_total_chunks):
        """
        Função que roda cada peer. Abre os sockets UDP e TCP e escuta por requisições.
        :param node_id: ID do nodo.
        :param config: Dicionário de configuração do nodo.
        :param topology: Dicionário de topologia indicando os vizinhos de cada nodo.
        """
        ip = config[node_id]['ip']
        udp_port = config[node_id]['udp_port']
        tcp_port = config[node_id]['udp_port']  # Usando a mesma porta para TCP
        capacity = config[node_id]['capacity']
        
        # Iniciando o socket UDP
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((ip, udp_port))
        print(f"Peer {node_id} ouvindo requisições UDP na porta {udp_port}")

        # Iniciando o socket TCP para enviar e receber chunks
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind((ip, tcp_port))
        tcp_socket.listen(5)
        print(f"Peer {node_id} ouvindo requisições TCP para transferência de chunks na porta {tcp_port}")

        received_chunks = 0 # Contador para acompanhar o número de chunks recebidos
        all_total_chunks = all_total_chunks # Dicionário com o total de chunks para cada arquivo


        visited_messages = set()  # Conjunto para armazenar mensagens já visitadas

        def receive_flooding():
            while True:
                try:
                    data, addr = udp_socket.recvfrom(1024)
                    message = json.loads(data.decode())
                    print(f"Peer {node_id} recebeu mensagem UDP de {addr}: {message}")
                    
                    message_id = f"{message['file_name']}-{message['tcp_port']}"
                    
                    if message_id in visited_messages:
                        print(f"Mensagem '{message_id}' já processada. Ignorando.")
                        continue

                    visited_messages.add(message_id)

                    if message['type'] == 'search':
                        file_name = message['file_name']
                        if node_id == 0:
                            print(f"PEER 0 TEM O ARQUIVO? {os.path.exists(f"{node_id}/{file_name}")}")
                        if os.path.exists(f"{node_id}/{file_name}"):
                            print(f"Peer {node_id} tem o arquivo '{file_name}', notificando o peer solicitante")
                            response_message = {
                                'type': 'response',
                                'file_name': file_name,
                                'peer_ip': config[node_id]['ip'],
                                'tcp_port': config[node_id]['udp_port'],
                                'total_chunks': all_total_chunks[file_name]
                            }
                            udp_socket.sendto(json.dumps(response_message).encode(), addr)
                            forward_message(node_id, topology, udp_socket, config, message)

                        elif message['ttl'] > 0:
                            print(f"Peer {node_id} processando busca de arquivo '{file_name}' com TTL {message['ttl']}")
                            forward_message(node_id, topology, udp_socket, config, message)

                    elif message['type'] == 'response':
                        print(f"Peer {node_id} recebeu resposta: O peer {message['peer_ip']} tem o arquivo '{message['file_name']}'")
                        total_chunks = message['total_chunks']
                        for chunk_id in range(total_chunks):
                            request_chunk(
                                peer_ip=message['peer_ip'],
                                peer_port=message['tcp_port'],
                                chunk_name=f"{message['file_name']}.ch{chunk_id}",
                                file_name=message['file_name'],
                                chunk_id=chunk_id,
                                total_chunks=total_chunks
                            )
                except Exception as e:
                    print(f"Erro no peer {node_id} ao receber UDP: {e}")

        def forward_message(node_id, topology, udp_socket, config, message):
            if message.get('file_found', False):
                print(f"Arquivo '{message['file_name']}' já foi encontrado. Não propagar mais.")
                return

            message['ttl'] -= 1
            if message['ttl'] <= 0:
                return

            time.sleep(1)
            for neighbor in topology[node_id]:
                neighbor_ip = config[neighbor]['ip']
                neighbor_port = config[neighbor]['udp_port']
                udp_socket.sendto(json.dumps(message).encode(), (neighbor_ip, neighbor_port))
                print(f"Peer {node_id} enviou mensagem para Peer {neighbor}")


        def handle_tcp_connections():
            while True:
                conn, addr = tcp_socket.accept()
                print(f"Peer {node_id} aceitou conexão TCP de {addr}")
                
                # Receber o nome completo do chunk solicitado
                requested_chunk = conn.recv(1024).decode().strip()
                if requested_chunk:
                    print(f"Peer {node_id} recebeu pedido para o chunk: {requested_chunk}")
                    
                    # Enviar o chunk solicitado
                    send_chunk(conn, node_id, requested_chunk)
                else:
                    print(f"Erro: Nome do chunk recebido está vazio")

        def send_chunk(conn, node_id, chunk_name):
            """
            Envia um chunk de arquivo.
            :param conn: Conexão TCP.
            :param node_id: ID do peer.
            :param chunk_name: Nome do chunk a ser enviado.
            """
            chunk_path = f"{node_id}/{chunk_name}"  # Diretório com o ID do peer

            if not os.path.exists(chunk_path):
                conn.send(b'CHUNK_NOT_FOUND')
                conn.close()
                return

            print(f"Peer {node_id} começou a enviar o chunk {chunk_name} para o peer solicitante.")

            total_size = os.path.getsize(chunk_path)  # Calcula o tamanho total do arquivo
            conn.send(f"{total_size}".encode()) # Envia o tamanho total do arquivo

            with open(chunk_path, 'rb') as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    conn.send(data)
                    # verificar esse sleep aqui ta muito lento
                    # time.sleep(1)

            print(f"Peer {node_id} terminou de enviar o chunk {chunk_name}")
            conn.close()

        def receive_chunk(conn, node_id, file_name, chunk_id, total_chunks):
            """
            Recebe um chunk de arquivo via TCP e salva no diretório do peer.
            :param conn: Conexão TCP.
            :param node_id: ID do peer.
            :param file_name: Nome do arquivo que está sendo transferido.
            :param chunk_id: ID do chunk recebido.
            :param total_chunks: Total de chunks esperados para este arquivo.
            """
            directory = f"{node_id}/received_chunks"
            os.makedirs(directory, exist_ok=True)  # Cria o diretório, se necessário
            chunk_path = f"{directory}/{file_name}.ch{chunk_id}"

            # Recebe o tamanho total do chunk do remetente
            total_size = int(conn.recv(1024).decode())
            total_received = 0  # Rastreia o número total de bytes recebidos

            print(f"Peer {node_id} começou a receber o chunk {chunk_id + 1}/{total_chunks} do arquivo '{file_name}'.")

            with open(chunk_path, 'wb') as f:
                while total_received < total_size:  # Continua até receber o tamanho total
                    data = conn.recv(1024)
                    if not data:
                        break
                    f.write(data)
                    total_received += len(data)

                    # Calcula e exibe o progresso do chunk atual
                    progress = (total_received / total_size) * 100
                    print(f"Progresso: {progress:.2f}% ({total_received}/{total_size} bytes) recebidos")

            print(f"Peer {node_id} terminou de receber o chunk {chunk_id + 1}/{total_chunks} do arquivo '{file_name}' e o salvou em '{chunk_path}'.")
            conn.close()

        def concatenate_chunks(file_name, total_chunks):
            """
            Função para concatenar todos os chunks recebidos e formar o arquivo final.
            :param file_name: Nome do arquivo que está sendo montado.
            :param total_chunks: Total de chunks que foram recebidos.
            """
            final_directory = f"{node_id}/received_files"
            os.makedirs(final_directory, exist_ok=True)  # Cria o diretório final, se necessário
            final_path = f"{final_directory}/{file_name}"

            with open(final_path, 'wb') as final_file:
                for chunk_id in range(total_chunks):
                    chunk_path = f"received_chunks/{file_name}.ch{chunk_id}"
                    with open(chunk_path, 'rb') as chunk_file:
                        final_file.write(chunk_file.read())

            print(f"Arquivo {file_name} montado com sucesso a partir dos {total_chunks} chunks.")
        
        def print_transfer_progress(current_chunk, total_chunks):
            """
            Função para imprimir o progresso da transferência.
            :param current_chunk: O número atual de chunks recebidos.
            :param total_chunks: O total de chunks a serem recebidos.
            """
            progress = (current_chunk / total_chunks) * 100
            print(f"Progresso da transferência: {current_chunk}/{total_chunks} chunks recebidos ({progress:.2f}%)")

        def request_chunk(peer_ip, peer_port, chunk_name, file_name, chunk_id, total_chunks):
            """
            Função para solicitar um chunk via TCP e recebê-lo.
            :param peer_ip: IP do peer que tem o chunk.
            :param peer_port: Porta TCP do peer que tem o chunk.
            :param chunk_name: Nome do chunk solicitado.
            :param file_name: Nome do arquivo principal.
            :param chunk_id: ID do chunk solicitado.
            :param total_chunks: Total de chunks esperados.
            """
            try:
                tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_conn.connect((peer_ip, peer_port))
                print(f"Conexão TCP estabelecida com o peer {peer_ip}:{peer_port}")

                # Solicita o chunk enviando seu nome
                tcp_conn.sendall(chunk_name.encode())
                print(f"Solicitando chunk {chunk_name}")

                # Receber e salvar o chunk
                receive_chunk(tcp_conn, node_id, file_name, chunk_id, total_chunks)                
                tcp_conn.close()

                # Atualiza o progresso
                nonlocal received_chunks
                received_chunks += 1
                print_transfer_progress(received_chunks, total_chunks)

                # Verifica se todos os chunks foram recebidos para montar o arquivo final
                if received_chunks == total_chunks:
                    concatenate_chunks(file_name, total_chunks)

            except Exception as e:
                print(f"Erro ao solicitar o chunk {chunk_name}: {e}")

        # Iniciando a thread para receber mensagens de busca
        threading.Thread(target=receive_flooding).start()

        # Iniciando a thread para lidar com conexões TCP
        threading.Thread(target=handle_tcp_connections).start()

        # Simulação da busca de arquivo iniciada por este nodo
        # Apenas para teste, o peer 1 inicia a busca de um arquivo
        if node_id == 1:
            message = {
                'type': 'search',
                'file_name': 'file.txt',
                'ttl': 4,
                'tcp_port': tcp_port,
            }
            forward_message(node_id, topology, udp_socket, config, message)
