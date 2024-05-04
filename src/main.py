import floresta
import threading
import inquirer
import electrum
import embit

from wallet import Wallet
from time import sleep

stop_signal = False

def update_wallet_task(wallet, server):
    global stop_signal
    while not stop_signal:
        update_wallet(wallet, server)
        sleep(1)

def update_wallet(wallet, server):
    for i in range(10):
        address = wallet.get_nth_external_key(i)
        history = server.get_history(address)
        if history is None:
            continue

        wallet_transactions = wallet.get_transactions()

        for tx in history:
            if tx['tx_hash'] in [t.txid().hex() for t in wallet_transactions]:
                continue
            tx = server.get_transaction(tx['tx_hash'])
            wallet.add_transaction(embit.transaction.Transaction.from_string(tx))
    for i in range(10):
        address = wallet.get_nth_internal_key(i)
        history = server.get_history(address)
        if history is None:
            continue

        wallet_transactions = wallet.get_transactions()

        for tx in history:
            if tx['tx_hash'] in [t.txid().hex() for t in wallet_transactions]:
                continue
            tx = server.get_transaction(tx['tx_hash'])
            wallet.add_transaction(embit.transaction.Transaction.from_string(tx))

def setup_wallet(wallet, server):
    for i in range(10):
        address = wallet.get_nth_external_key(i)
        server.subscribe_address(address)

    for i in range(10):
        address = wallet.get_nth_internal_key(i)
        server.subscribe_address(address)

def main():
    wallet = Wallet(b'0001')
    config = floresta.Config(
                    False,
                    [],
                    False,
                    json_rpc_address="127.0.0.1:8080",
                    network=floresta.Network.SIGNET,
                    wallet_xpub=wallet.xpubs(),
                    data_dir="/home/erik/Desktop/floresta/"
                )

    daemon = floresta.Florestad.from_config(config)
    daemon.start()
    server = electrum.ElectrumProxy()
    setup_wallet(wallet, server)

    threading.Thread(target=update_wallet_task, args=(wallet, server)).start()

    while True:
        question = inquirer.List('action', message="What do you want to do?", choices=['Quit', 'Send', 'Receive', 'Balance', 'Transactions', "Coins"])
        answer = inquirer.prompt([question])

        if answer['action'] == 'Send':
            address = input("Enter the address you want to send to: ")
            amount = int(input("Enter the amount you want to send: "))
            tx = wallet.pay(address, amount)
            print(f'txid={server.broadcast(tx.serialize().hex())}')

        if answer['action'] == 'Receive':
            print(wallet.get_new_address())

        if answer['action'] == 'Balance':
            print(wallet.get_balance())

        if answer['action'] == 'Coins':
            print(wallet.get_coins())

        if answer['action'] == 'Quit':
            print("Quitting...")
            daemon.stop()
            global stop_signal
            stop_signal = True
            exit()

if __name__ == "__main__":
    main()
