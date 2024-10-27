# T.1 - Sistemas P2P

INE 5418 – Computação Distribuída - Universidade Federal de Santa Catarina

## Descrição do Trabalho

Este projeto implementa uma rede de compartilhamento de arquivos **peer-to-peer (P2P)** não estruturada. Em uma rede P2P, todos os peers possuem papéis equivalentes e podem compartilhar arquivos diretamente entre si, sem passar por um servidor central. Neste sistema, um peer pode iniciar uma busca por um arquivo utilizando o método de **flooding**, propagando a mensagem de busca através de seus vizinhos até o número máximo de saltos definido pelo **TTL (time-to-live)**.

Quando um peer possui o arquivo solicitado ou parte dele (um **chunk**), ele responde diretamente ao peer solicitante. Assim, o peer solicitante pode receber diferentes chunks de diferentes peers e, ao final da transferência, reconstruir o arquivo.

## Como Executar

Para iniciar o sistema, utilize o comando abaixo:

```bash
python3 main.py <metadados>.p2p
```

Estrutura:

```
P2P/
├── src/
│   ├── config_parser.py -> Ler entrada
│   └── peer_node.py -> Toda a logica de peers
├── .gitignore
├── config.txt
├── estado_inicial.png
├── <metadados>.p2p
├── main.py -> Cria processos e chama parsers
├── README.md
└── topologia.txt
```
