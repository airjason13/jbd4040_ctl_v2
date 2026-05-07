import time

import smbus2
from smbus2 import i2c_msg
from global_def import log




class MockI2CDevice:
    def __init__(self, bus_number, device_address):
        self.bus = None
        self.address = None

    def write_32bit_data_block(self, reg_addr_24bit, data_32bit):
        pass

    def write_16bit_data_block(self, reg_addr_24bit, data_16bit):
        pass

    def write_32bit_data(self, reg_addr_24bit, data_32bit):
        pass

    def write_16bit_data(self, reg_addr_24bit, data_16bit):
        pass

    def read_32bit_data(self, reg_addr_24bit):
        return 0

    def read_16bit_data(self, reg_addr_24bit):
        return 0

