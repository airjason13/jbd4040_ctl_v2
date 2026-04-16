import sys
import time

from gpio_device import GPIOController
from i2c_device import I2CDevice
from gamma import *

class JBD4040:
    red_i2c_sa = 0x59
    green_i2c_sa = 0x5A
    blue_i2c_sa = 0x5B
    all_i2c_sa = 0x58

    RED_PANEL_TAG = 'Red'
    GREEN_PANEL_TAG = 'Green'
    BLUE_PANEL_TAG = 'Blue'
    ALL_PANEL_TAG = 'All'

    panels_i2c_sa_map = {
        'Red': 0x59,
        'Green': 0x5A,
        'Blue': 0x5B,
        'All': 0x58
    }

    lines = [6, 13, 19, 21, 26]

    lines_map = {
        "DVDD": 6,
        "VDDI": 19,
        "AVDD": 13,
        "AVEE": 26,
        "RESET": 21
    }

    def __init__(self, _gpio_chip_path='/dev/gpiochip0', _i2c_bus=0 ):
        self.gpio_chip_path = _gpio_chip_path
        self.i2c_bus = _i2c_bus
        print(f"self.i2c_bus: {self.i2c_bus}")
        # step.1 get gpio controller first
        self.gpio_ctrl = None
        self.gpio_ctrl = self.get_gpio_ctrl()

        if self.gpio_ctrl is None:
            print("Cannot get gpio ctrl! Exit!")
            sys.exit()

        # step.2 get smbus2 controller
        self.red_i2c_device = I2CDevice(self.i2c_bus, self.red_i2c_sa)
        self.green_i2c_device = I2CDevice(self.i2c_bus, self.green_i2c_sa)
        self.blue_i2c_device = I2CDevice(self.i2c_bus, self.blue_i2c_sa)
        self.all_i2c_device = I2CDevice(self.i2c_bus, self.all_i2c_sa)
        print(f"self.all_i2c_device bus :{self.all_i2c_device.bus}")
        print(f"self.all_i2c_device address :{self.all_i2c_device.address}")
        self.rgb_devices = [
            (self.red_i2c_device, "Red"),
            (self.green_i2c_device, "Green"),
            (self.blue_i2c_device, "Blue")
        ]

    def get_gpio_ctrl(self):
        ctrl = GPIOController(chip_path=self.gpio_chip_path, pins=self.lines)
        ret = ctrl.init_gpio()
        if ret != 0:
            print("Exit with gpio init")
            return None
        return ctrl


    def power_on_seq_jbd4040(self):
        print('power_seq_jbd4040')
        self.gpio_ctrl.set_multiple_levels({self.lines_map.get("DVDD"): False,
                                  self.lines_map.get("VDDI"): False,
                                  self.lines_map.get("AVDD"): False,
                                  self.lines_map.get("AVEE"): False,
                                  self.lines_map.get("RESET"): False})

        time.sleep(0.01)
        self.gpio_ctrl.set_level(self.lines_map.get("DVDD"), True)

        time.sleep(0.01)
        self.gpio_ctrl.set_level(self.lines_map.get("VDDI"), True)

        # time.sleep(0.01)
        self.gpio_ctrl.set_level(self.lines_map.get("AVDD"), True)

        time.sleep(0.02)
        self.gpio_ctrl.set_level(self.lines_map.get("RESET"), True)
        time.sleep(0.02)
        self.gpio_ctrl.set_level(self.lines_map.get("RESET"), False)
        time.sleep(0.01)
        self.gpio_ctrl.set_level(self.lines_map.get("RESET"), True)

    def init_registers(self):
        # --- Interrupt Mask Registers ---
        self.all_i2c_device.write_32bit_data(0x201044, 0x0000ffff)
        self.all_i2c_device.write_32bit_data(0x20104c, 0x0000ffff)
        self.all_i2c_device.write_32bit_data(0x201054, 0x0000ffff)
        self.all_i2c_device.write_32bit_data(0x20105c, 0x0000ffff)
        self.all_i2c_device.write_32bit_data(0x201064, 0x0000ffff)
        self.all_i2c_device.write_32bit_data(0x20106c, 0x0000ffff)
        self.all_i2c_device.write_16bit_data(0x200b0a, 0xffff)

        # --- MIPI Initialization ---
        self.all_i2c_device.write_32bit_data(0x201004, 0x00000001)  # enable dsi
        self.all_i2c_device.write_32bit_data(0x20100c, 0x00000000)  # enable eotp feature
        self.all_i2c_device.write_32bit_data(0x201028, 0x0000000f)  # cmd mode valid virtual channel [cite: 3]
        # device.write_32bit_data(0x20102c, 0x00000008)  # internal clk dividers [cite: 6]
        self.all_i2c_device.write_32bit_data(0x20102c, 0x00000004)  # internal clk dividers [cite: 6]

        self.all_i2c_device.write_32bit_data(0x202000, 0x0000007d)  # enable dphy
        # device.write_32bit_data(0x2021e0, 0x0000000e)  # THS-Settle [cite: 6]
        self.all_i2c_device.write_32bit_data(0x2021e0, 0x00000008)  # THS-Settle [cite: 6]
        self.all_i2c_device.write_32bit_data(0x201038, 0x000004a0)  # VID Tx Delay
        self.all_i2c_device.write_32bit_data(0x202128, 0x0000000f)  # enable continuous clock mode
        self.all_i2c_device.write_32bit_data(0x2021f4, 0x00000027)  # enable dphy trigger feature

        # --- Panel Initialization ---
        self.all_i2c_device.write_16bit_data(0x200100, 0x0022)  # pixel current ori 0x32
        # device.write_16bit_data(0x200a00, 0x000c)  # sf bit 10 with refresh frequency 240Hz
        # self.all_i2c_device.write_16bit_data(0x200a00, 0x0008)  # sf bit 10 with refresh frequency 60Hz
        self.all_i2c_device.write_16bit_data(0x200a00, 0x000C)  # sf bit 10 with refresh frequency 240Hz
        self.all_i2c_device.write_16bit_data(0x200a02, 0x0001)
        self.all_i2c_device.write_16bit_data(0x200a04, 0x0002)  # enable panel data load
        self.all_i2c_device.write_16bit_data(0x200a14, 0x1388)  # luminance ori 0x1388
        self.all_i2c_device.write_16bit_data(0x200a1c, 0x0000)  # X-axis start coordinate
        self.all_i2c_device.write_16bit_data(0x200a1e, 0x017b)  # X-axis end coordinate
        self.all_i2c_device.write_16bit_data(0x200a20, 0x0000)  # Y-axis start coordinate [cite: 10]
        self.all_i2c_device.write_16bit_data(0x200a22, 0x01f3)  # Y-axis end coordinate
        self.all_i2c_device.write_16bit_data(0x200a24, 0x0a06)  # offset settings [cite: 10]
        self.all_i2c_device.write_16bit_data(0x200b06, 0x0000)  # 1'b0: cmd mode [cite: 10]

        # --- Algorithm Initialization ---
        self.all_i2c_device.write_16bit_data(0x200d30, 0x0002)  # demura setting
        self.all_i2c_device.write_16bit_data(0x200d34, 0x80a1)  # demura setting [cite: 11]
        self.all_i2c_device.write_16bit_data(0x200204, 0x03ff)  # demura setting

        # update Gamma
        for dev, name in self.rgb_devices:
            self.update_panel_gamma(dev, name)

        # --- Load Gamma and Demura ---
        self.all_i2c_device.write_16bit_data(0x200200, 0x0100)  # gamma enable
        # self.all_i2c_device.write_16bit_data(0x200202, 0x0100)  # demura enable

        # --- Video mode ---
        self.all_i2c_device.write_16bit_data(0x200b06, 0x0001)  # 1'b0: cmd mode [cite: 10]

        # --- Frame Sync ---
        self.all_i2c_device.write_16bit_data(0x200a04, 0x000f)  # self refresh enable + frame sync [cite: 12]

        '''self.red_i2c_device.write_16bit_data(0x200100, 0x005a)  # pixel current ori 0x32
        self.green_i2c_device.write_16bit_data(0x200100, 0x0041)  # pixel current ori 0x32
        self.blue_i2c_device.write_16bit_data(0x200100, 0x0041)  # pixel current ori 0x32
        self.red_i2c_device.write_16bit_data(0x200a14, 0x01f4)  # lumi 0x1388
        self.green_i2c_device.write_16bit_data(0x200a14, 0xfa)  # lumi 0x1388
        self.blue_i2c_device.write_16bit_data(0x200a14, 0x7d)  # lumi 0x1388'''

        self.red_i2c_device.write_16bit_data(0x20020e, 0x0000)
        self.green_i2c_device.write_16bit_data(0x20020e, 0x0001)
        self.blue_i2c_device.write_16bit_data(0x20020e, 0x0000)

    def update_panel_gamma(self, device, name):
        print(f"正在寫入 {name} 面板 Gamma LUT...")
        for index, val in enumerate(gamma_2_2_data):
            # 每個地址對應 2-byte 資料，位址需以 2 遞增
            addr = START_ADDR + (index * 2)
            try:
                device.write_16bit_data(addr, val)
            except Exception as e:
                print(f"{name} 面板於位址 {hex(addr)} 寫入失敗: {e}")
                return False

        # 2. 寫入完成後，啟用該面板的 Gamma 功能
        # 設定 bit[8]=1 以 Enable Gamma
        device.write_16bit_data(GAMMA_EN_REG, 0x0100)
        print(f"{name} 面板 Gamma 1.0 寫入並啟用完成。")
        return True

    def turn_on_panel(self):
        time.sleep(2)
        self.gpio_ctrl.set_level(self.lines_map.get("AVEE"), True)

    def get_panel_temp(self, color_tag):
        for dev, name in self.rgb_devices:
            if name == color_tag:
                dev.write_16bit_data(0x200402, 0x0003)

                temp_ctrl = dev.read_16bit_data(0x200402)
                # print(f"{name} Temperature: {temp_ctrl:#x}")
                time.sleep(1)
                if temp_ctrl == 0x0003:
                    temp_register_value = dev.read_16bit_data(0x200404)
                    temp_val = self.calculate_temperature(temp_register_value)
                    if temp_val is not None:
                        # print(f"Red temp_register_value: {temp_register_value:#x}")
                        print(f"{name} 計算出的溫度: {temp_val:.2f} °C")
                dev.write_16bit_data(0x200402, 0x0000)



    def calculate_temperature(self, reg_value):
        """
        將 JBD4040 暫存器 0x20_0404 的原始值轉換為攝氏溫度

        :param reg_value: 從暫存器讀取到的 16-bit 數值 (int)
        :return: 攝氏溫度 (float) 或 None (若資料無效)
        """

        # 1. 檢查有效位 (Bit 12: PVT_DONE / Valid)
        is_valid = (reg_value >> 12) & 0x01
        if not is_valid:
            print("警告: 溫度資料尚未準備好 (Valid bit 為 0)")
            return None

        # 2. 提取原始碼 (Bit 11:0: PVT_DATA_OUT)
        code = reg_value & 0x0FFF

        # 3. 手冊定義的四次多項式係數
        a4 = -1.08168e-13
        a3 = 1.73665e-09
        a2 = -1.48650e-05
        a1 = 9.32829e-02
        a0 = -5.45788e+01

        # 4. 套用公式: Temp = a4*x^4 + a3*x^3 + a2*x^2 + a1*x + a0
        temp_c = (a4 * pow(code, 4)) + \
                 (a3 * pow(code, 3)) + \
                 (a2 * pow(code, 2)) + \
                 (a1 * code) + \
                 a0

        return temp_c


    def turn_off_mipi_dsi_output(self):
        target_path = "/sys/class/drm/card0-DSI-1/status"

        # 使用 Python 原生寫入，這等同於 shell 的 echo off > ...
        with open(target_path, 'w') as f:
            f.write('off')

        time.sleep(1)

        # 讀取結果
        with open(target_path, 'r') as f:
            status = f.read().strip()

        print(f"turn_off_mipi_dsi_output status: {status}")

    def turn_on_mipi_dsi_output(self):
        target_path = "/sys/class/drm/card0-DSI-1/status"

        # 使用 Python 原生寫入，這等同於 shell 的 echo off > ...
        with open(target_path, 'w') as f:
            f.write('on')

        time.sleep(1)

        # 讀取結果
        with open(target_path, 'r') as f:
            status = f.read().strip()

        print(f"turn_off_mipi_dsi_output status: {status}")