# Relatório T1 Computação Distribuída - P2P - UFSC

## Nicolas Elias SantAna e Enzo Gomes Sônego

## main.py script principal para inicialização de Rede P2P

Este script inicializa a rede P2P, configurando e executando processos independentes para cada peer (nodo) usando as configurações definidas.

---

## Classe Config_Parser

A classe `Config_Parser` realiza a leitura e interpretação de três arquivos essenciais para a configuração de uma rede P2P:

- **read_topology**: Lê o arquivo `topology.txt`, que define a topologia da rede, mapeando cada nó aos seus vizinhos.
- **read_config**: Lê o arquivo `config.txt`, que contém a configuração dos nós, incluindo IP, porta UDP e capacidade de envio de dados de cada nó.
- **read_metadata**: Lê o arquivo `<metadata>.p2p`, que fornece informações de metadados, como o nome do arquivo, total de chunks, TTL e o nó solicitante. Aqui tem uma coisa diferente do exemplo do professor, em que adicionamos mais uma linha informando qual nodo da topologia ta solicitando o arquivo.

---

## peer_node(node_id, config, topology, metadata)

Este é o método principal para iniciar um nodo (peer) na rede. Ele configura as portas UDP e TCP do peer para ouvir requisições de busca e transferência de chunks. Inicializa threads para o recebimento de mensagens de flooding e conexões TCP.

---

## receive_flooding

Escuta o socket UDP para receber e processar mensagens de outros peers na rede. As mensagens podem ser do tipo `search`, indicando uma busca por chunks do arquivo, ou `response`, indicando a disponibilidade de chunks em outro peer.

- **Mensagem de busca**: Verifica os chunks disponíveis e envia uma resposta se tiver algum chunk do arquivo solicitado.
- **Propagação**: Caso o TTL da mensagem seja maior que zero, propaga para os vizinhos. Cada mensagem é armazenada em `visited_messages` para evitar reprocessamento.
- **Solicitação inicial**: Apenas o peer solicitante trata as respostas recebidas e armazena as informações sobre os peers e chunks disponíveis.
- **Menssagem de resposta**: Aqui foi adotado uma solução em que so vamos de fato ir para o envio e recebimento dos chunks apos encontrar todos eles, logo temos uma estrutura em que cada chunks apos mapear quais chunks ele possui envia nessa menssagem de reposta qual seu ip e porta e quais chunks ele possui, e o nodo solicitante vai adicionando nessa estrutura `chunks_available` e faz uma verificação if `required_chunks.issubset(chunks_available[file_name].keys()):` para dai sim iniciar o processo de envio e recebimento dos chunks. logo não implementamos parciais, ou constroi tudo, ou nada.

---

## forward_message(node_id, topology, udp_socket, config, message, message_id)

Propaga a mensagem de busca para todos os vizinhos do peer, reduzindo o TTL a cada envio. É interrompida quando o TTL chega a zero, impedindo a propagação infinita da mensagem.

- **Controle de TTL**: Essencial para evitar sobrecarga na rede e garantir que a busca não se propague indefinidamente.

---

## handle_tcp_connections

Escuta conexões TCP de peers que solicitam chunks. Quando uma conexão é aceita, processa o pedido do chunk específico e chama `send_chunk` para enviar o chunk solicitado ao peer.

- **Solicitação de chunk**: Recebe o nome do chunk solicitado e chama `send_chunk` para iniciar a transferência.

---

## send_chunk(conn, node_id, chunk_name)

Envia um chunk de arquivo via conexão TCP. Após verificar a existência do chunk, envia o tamanho do chunk e os dados em pacotes, até completar a transferência.

- **Verificação de Existência**: Verifica se o chunk solicitado existe no diretório do peer.
- **Envio por Pacotes**: Garante que os dados são enviados em partes, respeitando a capacidade do nodo.

---

## receive_chunk(conn, node_id, file_name, chunk_id, total_chunks)

Recebe um chunk de arquivo via TCP e o salva no diretório do peer. Exibe o progresso da transferência e mantém o rastreamento dos bytes recebidos.

- **Controle de Progresso**: Calcula e exibe a porcentagem de bytes recebidos em tempo real, ajudando no monitoramento da transferência.
- **Armazenamento Ordenado**: Salva cada chunk com um identificador, facilitando a montagem posterior.

---

## request_chunks_sequentially(file_name, total_chunks)

Solicita chunks de forma sequencial após todos terem sido localizados realizados na etapa de flooding. Verifica quais chunks ainda não foram recebidos e os solicita ao peer que possui o chunk.

- **Seleção de Peer**: Prioriza o primeiro peer da lista que possui o chunk, otimizando a busca por chunks.

---

## request_chunk(peer_ip, peer_port, chunk_name, file_name, chunk_id, total_chunks)

Conecta-se ao peer via TCP para solicitar um chunk específico e chama `receive_chunk` para realizar o recebimento.

- **Verificação Completa**: Checa se todos os chunks foram recebidos e, caso afirmativo, chama `concatenate_chunks` para montar o arquivo final.

---

## concatenate_chunks(file_name, total_chunks, node_id)

Concatena todos os chunks recebidos para formar o arquivo completo. Salva o arquivo final no diretório do peer e exibe uma mensagem de conclusão.

- **Montagem Final**: Ordena e une os chunks na sequência correta.
- **Indicação de Sucesso**: Exibe uma mensagem clara indicando que o arquivo foi montado com sucesso e sua localização.

---
