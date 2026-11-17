"""BLE peripheral advertising the MAXINE vitals service (MicroPython bluetooth)."""
import bluetooth
from ble_protocol import SERVICE_UUID, VITALS_CHAR_UUID, COMMAND_CHAR_UUID

_IRQ_CONNECT, _IRQ_DISCONNECT = 1, 2
_NOTIFY, _READ, _WRITE = 0x10, 0x02, 0x08


def _adv(name):
    n = name.encode()
    return bytes([2, 1, 6, len(n) + 1, 9]) + n


class VitalsPeripheral:
    def __init__(self, name):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)
        svc = (bluetooth.UUID(SERVICE_UUID), (
            (bluetooth.UUID(VITALS_CHAR_UUID), _READ | _NOTIFY),
            (bluetooth.UUID(COMMAND_CHAR_UUID), _WRITE),
        ))
        ((self.vitals, self.command),) = self.ble.gatts_register_services((svc,))
        self.conns = set()
        self.name = name
        self.ble.gap_advertise(500000, _adv(name))

    def _irq(self, event, data):
        if event == _IRQ_CONNECT:
            self.conns.add(data[0])
        elif event == _IRQ_DISCONNECT:
            self.conns.discard(data[0])
            self.ble.gap_advertise(500000, _adv(self.name))

    def send(self, packet):
        self.ble.gatts_write(self.vitals, packet)
        for c in self.conns:
            self.ble.gatts_notify(c, self.vitals)
