"""BLE central: finds the wearable by name and subscribes to vitals."""
import bluetooth
from ble_protocol import VITALS_CHAR_UUID

_SCAN_RESULT, _SCAN_DONE, _CONNECT, _DISCONNECT = 5, 6, 7, 8
_CHAR_RESULT, _NOTIFY = 11, 18


class VitalsCentral:
    def __init__(self, name, on_packet):
        self.name = name.encode()
        self.on_packet = on_packet
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)
        self.conn = None

    def start(self):
        self.ble.gap_scan(0, 30000, 30000, True)

    def _irq(self, event, data):
        if event == _SCAN_RESULT and self.conn is None:
            addr_type, addr, _, _, adv = data
            if self.name in bytes(adv):
                self.ble.gap_scan(None)
                self.ble.gap_connect(addr_type, bytes(addr))
        elif event == _CONNECT:
            self.conn = data[0]
            self.ble.gattc_discover_characteristics(self.conn, 1, 0xFFFF)
        elif event == _CHAR_RESULT:
            conn, _, value_handle, _, uuid = data
            if uuid == bluetooth.UUID(VITALS_CHAR_UUID):
                # enable notifications on the CCCD that follows the value handle
                self.ble.gattc_write(conn, value_handle + 1, b"\x01\x00", 1)
        elif event == _NOTIFY:
            self.on_packet(bytes(data[2]))
        elif event == _DISCONNECT:
            self.conn = None
            self.start()
