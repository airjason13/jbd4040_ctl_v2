import time

import smbus2
from smbus2 import i2c_msg
from global_def import log




class I2CDevice:
    def __init__(self, bus_number, device_address):
        self.bus = smbus2.SMBus(bus_number)
        self.address = device_address

    def write_32bit_data_block(self, reg_addr_24bit, data_32bit):
        """
        對應 Figure 3-23: Single address data write
        reg_addr_24bit: 24位暫存器位址 (例如 0x010203)
        data_16bit: 16位資料 (例如 0xABCD)
        """
        # 拆解 24-bit 位址為 3 個 bytes
        addr_bytes = [
            (reg_addr_24bit >> 16) & 0xFF,
            (reg_addr_24bit >> 8) & 0xFF,
            reg_addr_24bit & 0xFF
        ]

        # 拆解 32-bit 數據
        data_bytes = [
            data_32bit & 0xFF,
            (data_32bit >> 8) & 0xFF,
            (data_32bit >> 16) & 0xFF,
            (data_32bit >> 24) & 0xFF
        ]

        # 合併位址與數據進行發送
        payload = addr_bytes + data_bytes
        self.bus.write_i2c_block_data(self.address, payload[0], payload[1:])

    def write_16bit_data_block(self, reg_addr_24bit, data_16bit):
        try:
            """
            對應 Figure 3-23: Single address data write
            reg_addr_24bit: 24位暫存器位址 (例如 0x010203)
            data_16bit: 16位資料 (例如 0xABCD)
            """
            # 拆解 24-bit 位址為 3 個 bytes
            addr_bytes = [
                (reg_addr_24bit >> 16) & 0xFF,
                (reg_addr_24bit >> 8) & 0xFF,
                reg_addr_24bit & 0xFF
            ]

            # 拆解 16-bit 數據 (根據圖示 WDT[7:0] 先傳, WDT[15:8] 後傳)
            data_bytes = [
                data_16bit & 0xFF,  # Low byte
                (data_16bit >> 8) & 0xFF  # High byte
            ]

            # 合併位址與數據進行發送

            payload = addr_bytes + data_bytes

            self.bus.write_i2c_block_data(self.address, payload[0:2], payload[3:])
        except Exception as e:
            print(e)

    def write_32bit_data(self, reg_addr_24bit, data_32bit):
        try:
            # 1. 準備 56-bit 位址
            addr_bytes = [
                (reg_addr_24bit >> 16) & 0xFF,
                (reg_addr_24bit >> 8) & 0xFF,
                reg_addr_24bit & 0xFF,
                data_32bit & 0xFF,
                (data_32bit >> 8) & 0xFF,
                (data_32bit >> 16) & 0xFF,
                (data_32bit >> 24) & 0xFF,
            ]

            write = i2c_msg.write(self.address, addr_bytes)
            self.bus.i2c_rdwr(write)
        except Exception as e:
            log.error(e)

    def write_16bit_data(self, reg_addr_24bit, data_16bit):
        try:
            # 1. 準備 40-bit 位址
            addr_bytes = [
                (reg_addr_24bit >> 16) & 0xFF,
                (reg_addr_24bit >> 8) & 0xFF,
                reg_addr_24bit & 0xFF,
                data_16bit & 0xFF,
                (data_16bit >> 8) & 0xFF,
            ]
            # print(f"addr_bytes[0:]:{addr_bytes[0:]}")
            write = i2c_msg.write(self.address, addr_bytes)
            self.bus.i2c_rdwr(write)
        except Exception as e:
            log.error(e)

    def read_32bit_data(self, reg_addr_24bit):
        """
        對應 Figure 3-24: Single address data read
        包含一個 Write 週期來指定位址，緊接著一個 Read 週期
        """
        data_32bit = 0
        try:
        # 1. 準備 24-bit 位址
            addr_bytes = [
                (reg_addr_24bit >> 16) & 0xFF,
                (reg_addr_24bit >> 8) & 0xFF,
                reg_addr_24bit & 0xFF
            ]

            write = i2c_msg.write(self.address, addr_bytes)
            self.bus.i2c_rdwr(write)

            # 3. 第二次 rdwr: 讀取 2 位元組 (自動從 START 開始)
            read = i2c_msg.read(self.address, 4)
            self.bus.i2c_rdwr(read)

            # 組合回 16-bit 數值 (根據圖示 RDT[7:0] 先到, RDT[15:8] 後到)
            results = list(read)
            data_32bit = (results[1] << 24) | (results[1] << 16) |(results[1] << 8) | results[0]
        except Exception as e:
            log.error(e)
        finally:
            return data_32bit

    def read_16bit_data(self, reg_addr_24bit):
        """
        對應 Figure 3-24: Single address data read
        包含一個 Write 週期來指定位址，緊接著一個 Read 週期
        """
        data_16bit = 0
        try:
        # 1. 準備 24-bit 位址
            addr_bytes = [
                (reg_addr_24bit >> 16) & 0xFF,
                (reg_addr_24bit >> 8) & 0xFF,
                reg_addr_24bit & 0xFF
            ]

            write = i2c_msg.write(self.address, addr_bytes)
            self.bus.i2c_rdwr(write)

            # 3. 第二次 rdwr: 讀取 2 位元組 (自動從 START 開始)
            read = i2c_msg.read(self.address, 2)
            self.bus.i2c_rdwr(read)

            # 組合回 16-bit 數值 (根據圖示 RDT[7:0] 先到, RDT[15:8] 後到)
            results = list(read)
            data_16bit = (results[1] << 8) | results[0]
        except Exception as e:
            log.error(e)
        finally:
            return data_16bit


