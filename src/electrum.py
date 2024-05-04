import hashlib
import json
from socket import socket, AF_INET, SOCK_STREAM
from threading import Lock 

class ElectrumProxy:
    transport = None
    io_lock = Lock() 
    def __init__(self, server='127.0.0.1', port=50001, connect="194.163.132.180", protocol='tcp'):
        self.transport = socket(AF_INET, SOCK_STREAM)
        self.transport.connect((server, port))

    def getinfo(self):
        return self.call('server.version', '2.7.11', '1.4')
    
    def get_transaction(self, txid):
        return self.call('blockchain.transaction.get', txid)

    def subscribe_address(self, address):
        address_hash = self.get_script_hash_from_address(address)
        return self.call('blockchain.scripthash.subscribe', address_hash)

    def read_line(self):
        self.io_lock.acquire()
        buffer = b''

        while True:
            data = self.transport.recv(1)
            buffer += data
            if data == b'\n':
                self.io_lock.release()
                return buffer

    def call(self, method, *args):
        self.transport.send('{'.encode('utf-8'))
        args = ', '.join([f'"{arg}"' for arg in args])
        self.transport.sendall(f'"jsonrpc": "2.0", "method": "{method}", "params": [{args}], "id": 1'.encode('utf-8'))
        self.transport.send('}\n'.encode('utf-8'))

        while True:
            res = self.read_line()

            if res == '':
                return None
            try:
                parsed_json = json.loads(res)
                # Skip notifications
                if "method" in parsed_json:
                    continue

                if 'error' in parsed_json or 'result' not in parsed_json:
                    print(f"{method}: Error: {parsed_json['error']}")
                    return None
                return parsed_json['result']
            except json.JSONDecodeError:
                print(f"{method}: Error parsing JSON: {res}")
                return None

    @classmethod
    def get_script_hash_from_address(self, address):
        from embit.script import address_to_scriptpubkey
        spk = address_to_scriptpubkey(address).serialize()[1::]

        hash = hashlib.sha256()
        hash.update(spk)

        hash = hash.digest()[::-1].hex()
        return hash

    # def subscribe_headers(self):
    #     self.transport.send('{"jsonrpc": "2.0", "method": "blockchain.headers.subscrib  e", "params": [], "id": 1}\n'.encode('utf-8'))
    #     return self.transport.recvmsg(1024)

    def get_history(self, address):
        address_hash = self.get_script_hash_from_address(address)
        return self.call('blockchain.scripthash.get_history', address_hash)

    def broadcast(self, tx: str) -> str:
        return self.call("blockchain.transaction.broadcast", tx)
