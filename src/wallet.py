import embit
from embit.transaction import TransactionOutput, Transaction, TransactionInput, Witness, SIGHASH
from embit.bip32 import HDKey
from embit.script import p2wpkh, p2pkh

class Wallet:
    coins = []
    transactions: list[Transaction] = []
    xpub: HDKey = None
    internal_key_index: int = 0
    external_key_index: int = 0

    def xpubs(self) -> list[HDKey]:
        ''' Returns both keys in our internal and external keychains '''
        return [
            self.xpub.derive(f"m/84'/1'/0'/0").to_public().to_string(),
            self.xpub.derive(f"m/84'/1'/0'/1").to_public().to_string()
        ]

    def __init__(self, seed):
        self.coins = []
        self.transactions = []
        self.xpub = HDKey.from_seed(seed)

    def get_balance(self):
        return sum([coin[2].value for coin in self.coins])

    def get_new_address(self):
        pubkey = self.xpub.derive(f"m/84'/1'/0'/0/{self.external_key_index}").key
        self.external_key_index += 1
        return embit.script.p2wpkh(pubkey).address(network=embit.networks.NETWORKS["signet"])

    def get_change_address(self):
        pubkey = self.xpub.derive(f"m/84'/1'/0'/1/{self.internal_key_index}").key
        self.internal_key_index += 1
        return embit.script.p2wpkh(pubkey).address(network=embit.networks.NETWORKS["signet"])

    def derive_at_path(self, path):
        return self.xpub.derive(path)

    def get_nth_internal_key(self, n):
        return self.get_address_at_path(f"m/84'/1'/0'/1/{n}")

    def get_nth_external_key(self, n):
        return self.get_address_at_path(f"m/84'/1'/0'/0/{n}")

    def get_address_at_path(self, path):
        pubkey = self.derive_at_path(path).key
        return embit.script.p2wpkh(pubkey).address(network=embit.networks.NETWORKS["signet"])

    def add_transaction(self, tx: Transaction):
        self.transactions.append(tx)
        addresses = []
        for i in range(0, 10):
            addresses.append(self.get_address_at_path(f"m/84'/1'/0'/0/{i}"))

        for i in range(len(tx.vout)):
            address = tx.vout[i].script_pubkey.address(network=embit.networks.NETWORKS["signet"])
            if address in addresses:
                idx = addresses.index(address)
                self.coins.append((tx.txid(), i, tx.vout[i], idx))

        for inp in tx.vin:
            for coin in self.coins:
                if inp.txid == coin[0] and inp.vout == coin[1]:
                    self.coins.remove(coin)
                    break

    def estimate_fee(self, tx: Transaction, fee_rate=1):
        return len(tx.serialize() + 36 + 73 + 33) * fee_rate

    def get_coins(self) -> list[str]:
        return [f'{coin[0].hex()}:{coin[1]}' for coin in self.coins]

    def get_transactions(self):
        return self.transactions

    def pay(self, address, amount, fee=500):
        tx = Transaction()
        inputs = []
        budget = 0
        keys = []
        amount_with_fee = amount + fee
        for coin in self.coins:
            inputs.append(coin)
            budget += coin[2].value
            keys.append(self.xpub.derive(f"m/84'/1'/0'/0/{coin[3]}").key)
            if budget >= amount_with_fee:
                break

        if budget < amount:
            raise Exception("Not enough funds")

        for i in inputs:
            tx.vin.append(TransactionInput(i[0], i[1], embit.script.Script(), 0))


        tx.vout.append(TransactionOutput(amount, embit.script.Script.from_address(address)))
        change = budget - amount_with_fee

        for i in range(0, len(inputs)):
            value = inputs[i][2].value
            sighash = tx.sighash_segwit(i, p2pkh(keys[i]), value, sighash=SIGHASH.ALL)
            sig = keys[i].sign(sighash, grind=False)

            tx.vin[i].witness = embit.script.witness_p2wpkh(sig, keys[i])
            assert keys[i].verify(sig, sighash)

        return tx
