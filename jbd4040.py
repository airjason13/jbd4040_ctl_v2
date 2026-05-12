import os
import platform
import re
import sys
import time
from pathlib import Path
import random

from PyQt5.QtCore import QTimer

from global_def import *
from gpio_device import GPIOController
from i2c_device import I2CDevice
from gamma import *
from pathlib import Path

from mock_i2c_device import MockI2CDevice


def get_oe_params_folder_path():
    # 取得目前檔案的絕對路徑
    current_file = Path(__file__).resolve()

    # 取得該檔案所在的資料夾路徑
    oe_dir_path = current_file.parent / "oe_params"

    log.debug(f"oe_dir_path: {oe_dir_path}")
    return oe_dir_path


class JBD4040:
    red_i2c_sa = 0x59
    green_i2c_sa = 0x5A
    blue_i2c_sa = 0x5B
    all_i2c_sa = 0x58

    RED_PANEL_TAG = 'Red'
    GREEN_PANEL_TAG = 'Green'
    BLUE_PANEL_TAG = 'Blue'
    ALL_PANEL_TAG = 'All'

    RGB_PANEL_TAG_LIST = [
        RED_PANEL_TAG,
        GREEN_PANEL_TAG,
        BLUE_PANEL_TAG,
        ALL_PANEL_TAG]

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

    R_LUMINANCE_DEFAULT_VALUE = 512
    G_LUMINANCE_DEFAULT_VALUE = 512
    B_LUMINANCE_DEFAULT_VALUE = 512

    R_CURRENT_DEFAULT_VALUE = 50
    G_CURRENT_DEFAULT_VALUE = 50
    B_CURRENT_DEFAULT_VALUE = 50

    R_H_OFFSET_DEFAULT_VALUE = 10
    G_H_OFFSET_DEFAULT_VALUE = 10
    B_H_OFFSET_DEFAULT_VALUE = 10

    R_V_OFFSET_DEFAULT_VALUE = 6
    G_V_OFFSET_DEFAULT_VALUE = 6
    B_V_OFFSET_DEFAULT_VALUE = 6

    def __init__(self, _gpio_chip_path='/dev/gpiochip0', _i2c_bus=0 ):
        if platform.machine() == 'x86_64':
            self.gpio_chip_path = _gpio_chip_path
            self.i2c_bus = _i2c_bus

            # step.1 get gpio controller first
            self.gpio_ctrl = None

            # get smbus2 controller
            self.red_i2c_device = MockI2CDevice(self.i2c_bus, self.red_i2c_sa)
            self.green_i2c_device = MockI2CDevice(self.i2c_bus, self.green_i2c_sa)
            self.blue_i2c_device = MockI2CDevice(self.i2c_bus, self.blue_i2c_sa)
            self.all_i2c_device = MockI2CDevice(self.i2c_bus, self.all_i2c_sa)

            self.rgb_devices = [
                (self.red_i2c_device, "Red"),
                (self.green_i2c_device, "Green"),
                (self.blue_i2c_device, "Blue")
            ]

            self.rgb_devices_map = {
                "Red": self.red_i2c_device,
                "Green": self.green_i2c_device,
                "Blue": self.blue_i2c_device
            }

        else:
            self.gpio_chip_path = _gpio_chip_path
            self.i2c_bus = _i2c_bus

            # step.1 get gpio controller first
            self.gpio_ctrl = None
            self.gpio_ctrl = self.get_gpio_ctrl()

            if self.gpio_ctrl is None:
                log.error("Cannot get gpio ctrl! Exit!")
                sys.exit()

            # get smbus2 controller
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

            self.rgb_devices_map = {
                "Red": self.red_i2c_device,
                "Green": self.green_i2c_device,
                "Blue": self.blue_i2c_device
            }



        # get persist path
        # persist folder
        self.path_persist = Path(PERSIST_CONFIG_URI_PATH)
        self.path_persist.mkdir(parents=True, exist_ok=True)

        # persist files
        self.path_lumin_r = self.path_persist / "persis_le_lumin_r"
        self.path_lumin_g = self.path_persist / "persis_le_lumin_g"
        self.path_lumin_b = self.path_persist / "persis_le_lumin_b"

        self.path_current_r = self.path_persist / "persis_le_current_r"
        self.path_current_g = self.path_persist / "persis_le_current_g"
        self.path_current_b = self.path_persist / "persis_le_current_b"

        self.path_flip = self.path_persist / "persis_le_flip"
        self.path_mirror = self.path_persist / "persis_le_mirror"

        self.path_offset_r = self.path_persist / "persis_le_offset_r"
        self.path_offset_g = self.path_persist / "persis_le_offset_g"
        self.path_offset_b = self.path_persist / "persis_le_offset_b"

        self.path_persist_params = [
            self.path_lumin_r,
            self.path_lumin_g,
            self.path_lumin_b,

            self.path_current_r,
            self.path_current_g,
            self.path_current_b,

            self.path_flip,
            self.path_mirror,

            self.path_offset_r,
            self.path_offset_g,
            self.path_offset_b,
        ]

        # 檢查預設參數檔案是否存在,不存在直接建立
        self.init_persist_params()

        # 檢查fake sysfs
        oe_params_path = get_oe_params_folder_path()

        # sysfs nodes
        self.sysfs_luminance = oe_params_path / "luminance"
        self.sysfs_current = oe_params_path / "current"
        self.sysfs_temperature = oe_params_path / "temperature"
        self.sysfs_flip = oe_params_path / "flip"
        self.sysfs_mirror = oe_params_path / "mirror"
        self.sysfs_offset = oe_params_path / "offset"
        self.oe_params_paths = [
            self.sysfs_luminance,
            self.sysfs_current,
            # self.sysfs_temperature, # Do not monitor temperature
            self.sysfs_flip,
            self.sysfs_mirror,
            self.sysfs_offset,
        ]
        self.check_oe_params_exist()

        # Timer inside controller
        self.temperature_timer = QTimer()
        self.temperature_timer.setInterval(2)
        self.temperature_timer.timeout.connect(self.get_panels_max_temperature_and_sync_sysfs)

        QTimer.singleShot(0, self.temperature_timer.start)

    def check_oe_params_exist(self):
        for p in self.oe_params_paths:
            if not p.exists():
                p.touch(exist_ok=True)



    def get_oe_params_paths_with_list_str(self) ->list[str]:
        return list(map(str, self.oe_params_paths))

    def get_gpio_ctrl(self):
        ctrl = GPIOController(chip_path=self.gpio_chip_path, pins=self.lines)
        ret = ctrl.init_gpio()
        if ret != 0:
            log.error("Exit with gpio init")
            return None
        return ctrl

    def power_on_seq_jbd4040(self):
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform power_on_seq_jbd4040")
            return
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

    def power_off_seq_jbd4040(self):
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform power_on_seq_jbd4040")
            return
        time.sleep(0.01)
        self.gpio_ctrl.set_level(self.lines_map.get("VDDI"), False)

        # time.sleep(0.01)
        self.gpio_ctrl.set_level(self.lines_map.get("AVDD"), False)

        time.sleep(0.01)
        self.gpio_ctrl.set_level(self.lines_map.get("DVDD"), False)



    def init_registers(self):
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform init_registers")
            return
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

        self.red_i2c_device.write_16bit_data(0x20020e, 0x0000)
        self.green_i2c_device.write_16bit_data(0x20020e, 0x0001)
        self.blue_i2c_device.write_16bit_data(0x20020e, 0x0000)


    def test_luminance_current(self):
        log.debug("Do not use this function!")
        pass
        self.all_i2c_device.write_16bit_data(0x200a14, 0x200)
        self.red_i2c_device.write_16bit_data(0x200100, 0x5a)
        self.green_i2c_device.write_16bit_data(0x200100, 0x32)
        self.blue_i2c_device.write_16bit_data(0x200100, 0x19)

    def read_fmc_register_range(self):
        """
        讀取從 0x200c00 到 0x200c28 的 16-bit 暫存器資料
        """
        if platform.machine() == 'x86_64':
            log.debug("x84_64 平台跳過暫存器讀取")
            return

        start_addr = 0x200c00
        end_addr = 0x200c28

        print(f"--- 開始讀取暫存器範圍: {hex(start_addr)} 到 {hex(end_addr)} ---")

        # 使用 range(start, stop, step)，stop 需 +2 以包含 0x200c28
        for addr in range(start_addr, end_addr + 2, 2):
            try:
                data = self.all_i2c_device.read_16bit_data(addr)
                print(f"Address: {hex(addr)} | Data: {hex(data)}")
            except Exception as e:
                print(f"讀取位址 {hex(addr)} 失敗: {e}")

        print("--- 讀取完成 ---")

    def read_efuse_register_range(self):
        """
        讀取從 0x200c00 到 0x200c28 的 16-bit 暫存器資料
        """
        if platform.machine() == 'x86_64':
            log.debug("x84_64 平台跳過暫存器讀取")
            return

        start_addr = 0x200d00
        end_addr = 0x200d42

        print(f"--- 開始讀取暫存器範圍: {hex(start_addr)} 到 {hex(end_addr)} ---")

        # 使用 range(start, stop, step)，stop 需 +2 以包含 0x200c28
        for addr in range(start_addr, end_addr + 2, 2):
            try:
                data = self.all_i2c_device.read_16bit_data(addr)
                print(f"Address: {hex(addr)} | Data: {hex(data)}")
            except Exception as e:
                print(f"讀取位址 {hex(addr)} 失敗: {e}")

        print("--- 讀取完成 ---")


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
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform turn_on_panel")
            return
        time.sleep(2)
        self.gpio_ctrl.set_level(self.lines_map.get("AVEE"), True)

    def turn_off_panel(self):
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform turn_on_panel")
            return
        time.sleep(2)
        self.gpio_ctrl.set_level(self.lines_map.get("AVEE"), False)

    def get_panels_max_temperature_and_sync_sysfs(self):
        panels_temp = {}
        for dev, name in self.rgb_devices:
            dev.write_16bit_data(0x200402, 0x0003)

            temp_ctrl = dev.read_16bit_data(0x200402)
            if platform.machine() == 'x86_64':
                raw_val = random.uniform(10, 50)
                result = f"{raw_val:.3f}"
                panels_temp[name] = result
            else:
                time.sleep(1)
                if temp_ctrl == 0x0003:
                    temp_register_value = dev.read_16bit_data(0x200404)
                    temp_val = self.calculate_temperature(temp_register_value)
                    if temp_val is not None:
                        print(f"{name} 計算出的溫度: {temp_val:.2f} °C")
                        panels_temp[name] = temp_val
                dev.write_16bit_data(0x200402, 0x0000)

        max_temp_val = max(panels_temp.values())
        self.sysfs_temperature.write_text(str(max_temp_val))
        os.sync()

    def get_panel_temp(self, color_tag):
        panel_temp = {}
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
                        panel_temp[name] = temp_val
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
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform turn_off_mipi_dsi_output")
            return
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
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform turn_on_mipi_dsi_output")
            return
        target_path = "/sys/class/drm/card0-DSI-1/status"

        # 使用 Python 原生寫入，這等同於 shell 的 echo off > ...
        with open(target_path, 'w') as f:
            f.write('on')

        time.sleep(1)

        # 讀取結果
        with open(target_path, 'r') as f:
            status = f.read().strip()

        print(f"turn_off_mipi_dsi_output status: {status}")

    def _touch_if_missing(self, path: Path) -> None:
        try:
            if not path.exists():
                path.touch()
        except Exception as e:
            log.warning(f"[LE] touch failed {path}: {e}")

    def _safe_read(self, path: Path) -> str:
        try:
            return path.read_text().strip()
        except Exception:
            return ""

    def _safe_write(self, path: Path, text: str) -> bool:
        """
        write sysfs. return True if wrote, False if skipped/failed
        """
        try:
            if not path.exists():
                return False
            path.write_text(text)
            return True
        except Exception as e:
            log.warning(f"[LE] write failed {path}: {e}")
            return False

    # -------------------------
    # Restore / Persist helpers
    # -------------------------
    def init_persist_params(self):
        # handle luminance
        for p in [
            self.path_lumin_r, self.path_lumin_g, self.path_lumin_b,
        ]:
            log.debug(f"init_persist_params luminance: {p}")
            log.debug(f"init_persist_params luminance _safe_read: {self._safe_read(p)}")
            log.debug(f"init_persist_params luminance read_text: {p.read_text()}")
            if not p.exists() or self._safe_read(p) == '':
                self._touch_if_missing(p)
                log.debug("init_persist_params luminance")
                if 'r'.lower() in p.name.lower():
                    p.write_text(str(self.R_LUMINANCE_DEFAULT_VALUE))
                elif 'g'.lower() in p.name.lower():
                    p.write_text(str(self.G_LUMINANCE_DEFAULT_VALUE))
                elif 'b'.lower() in p.name.lower():
                    p.write_text(str(self.B_LUMINANCE_DEFAULT_VALUE))
                with open(p, 'r+') as f:
                    os.fsync(f.fileno())
        # handle current
        for p in [
            self.path_current_r, self.path_current_g, self.path_current_b,
        ]:
            log.debug(f"init_persist_params current: {p}")
            if not p.exists() or self._safe_read(p) == '':
                self._touch_if_missing(p)
                if 'r'.lower() in p.name.lower():
                    p.write_text(str(self.R_CURRENT_DEFAULT_VALUE))
                elif 'g'.lower() in p.name.lower():
                    p.write_text(str(self.G_CURRENT_DEFAULT_VALUE))
                elif 'b'.lower() in p.name.lower():
                    p.write_text(str(self.B_CURRENT_DEFAULT_VALUE))
                with open(p, 'r+') as f:
                    os.fsync(f.fileno())

        # handle offset
        for p in [
            self.path_offset_r, self.path_offset_g, self.path_offset_b,
        ]:
            log.debug(f"init_persist_params offset: {p}")
            if not p.exists() or self._safe_read(p) == '':
                self._touch_if_missing(p)
                if 'r'.lower() in p.name.lower():
                    r_offset_str = f"1,{self.R_H_OFFSET_DEFAULT_VALUE},{self.R_V_OFFSET_DEFAULT_VALUE}"
                    p.write_text(r_offset_str)
                elif 'g'.lower() in p.name.lower():
                    g_offset_str = f"1,{self.G_H_OFFSET_DEFAULT_VALUE},{self.G_V_OFFSET_DEFAULT_VALUE}"
                    p.write_text(g_offset_str)
                elif 'b'.lower() in p.name.lower():
                    b_offset_str = f"1,{self.B_H_OFFSET_DEFAULT_VALUE},{self.B_V_OFFSET_DEFAULT_VALUE}"
                    p.write_text(b_offset_str)
                with open(p, 'r+') as f:
                    os.fsync(f.fileno())

        os.sync()

    def sync_oe_current_with_persist(self) -> None:
        current_map = {}
        for p in [
            self.path_current_r, self.path_current_g, self.path_current_b,
        ]:
            content = p.read_text().strip()
            # 取得檔名最後一個字母作為 Key (r, g, b)
            key = p.name.split('_')[-1]
            current_map[key] = content
        log.debug(f"sync_oe_current_with_persist: {current_map}")
        target_oe_params_current_str = (f"R:{current_map.get('r')}\n"
                                        f"G:{current_map.get('g')}\n"
                                        f"B:{current_map.get('b')}")
        self.sysfs_current.write_text(target_oe_params_current_str)

    def sync_oe_luminance_with_persist(self) -> None:
        luminance_map = {}
        for p in [
            self.path_lumin_r, self.path_lumin_g, self.path_lumin_b,
        ]:
            content = p.read_text().strip()
            # 取得檔名最後一個字母作為 Key (r, g, b)
            key = p.name.split('_')[-1]
            luminance_map[key] = content
        log.debug(f"sync_oe_luminance_with_persist: {luminance_map}")
        target_oe_params_luminance_str = (f"R:{luminance_map.get('r')}\n"
                                        f"G:{luminance_map.get('g')}\n"
                                        f"B:{luminance_map.get('b')}")
        self.sysfs_luminance.write_text(target_oe_params_luminance_str)

    def sync_oe_offset_with_persist(self) -> None:
        offset_map = {}
        for p in [
            self.path_offset_r, self.path_offset_g, self.path_offset_b,
        ]:
            raw_data = p.read_text().strip().split(',')

            # 取得結尾字母作為 Key (r, g, b)
            key = p.name.split('_')[-1]

            # 存成巢狀字典，方便後續調用
            offset_map[key] = {
                'enable': 'enabled' if raw_data[0] == '1' else 'disabled',
                'x_offset': raw_data[1],
                'v_offset': raw_data[2]
            }
        color_names = {'r': 'R', 'g': 'G', 'b': 'B'}
        result_lines = []
        # 按照 R, G, B 的順序處理 (確保輸出順序固定)
        for c_key in ['r', 'g', 'b']:
            if c_key in offset_map:
                vals = offset_map[c_key]
                # 依照格式組合成字串
                # R(enabled) H:16 V:11
                line = f"{color_names[c_key]}({vals['enable']}) H:{vals['x_offset']} V:{vals['v_offset']}"
                result_lines.append(line)

        # 將列表用換行符號連接起來
        target_oe_params_offset_str = "\n".join(result_lines)

        self.sysfs_offset.write_text(target_oe_params_offset_str)

    def sync_oe_params_with_persist_params(self) -> None:
        self.sync_oe_current_with_persist()
        self.sync_oe_luminance_with_persist()
        self.sync_oe_offset_with_persist()
        log.debug("mirror/flip are not implemented")


    def write_oe_params_with_persist_params_dep(self) -> None:
        # ensure persist files exist
        for p in [
            self.path_lumin_r, self.path_lumin_g, self.path_lumin_b,
            self.path_current_r, self.path_current_g, self.path_current_b,
            self.path_flip, self.path_mirror,
            self.path_offset_r, self.path_offset_g, self.path_offset_b,
        ]:
            self._touch_if_missing(p)

        # brightness restore
        self._restore_simple_rgb(self.path_lumin_r, self.sysfs_luminance, "r")
        self._restore_simple_rgb(self.path_lumin_g, self.sysfs_luminance, "g")
        self._restore_simple_rgb(self.path_lumin_b, self.sysfs_luminance, "b")

        # current restore
        self._restore_simple_rgb(self.path_current_r, self.sysfs_current, "r")
        self._restore_simple_rgb(self.path_current_g, self.sysfs_current, "g")
        self._restore_simple_rgb(self.path_current_b, self.sysfs_current, "b")

        # flip / mirror restore
        self._restore_flag(self.path_flip, self.sysfs_flip)
        self._restore_flag(self.path_mirror, self.sysfs_mirror)

        # offset restore
        self._restore_offset(self.path_offset_r, self.sysfs_offset, "r")
        self._restore_offset(self.path_offset_g, self.sysfs_offset, "g")
        self._restore_offset(self.path_offset_b, self.sysfs_offset, "b")

    def _restore_simple_rgb(self, persist: Path, sysfs: Path, ch: str) -> None:
        value = self._safe_read(persist)
        if not value:
            return
        self._safe_write(sysfs, f"{ch} {value}")

    def _restore_flag(self, persist: Path, sysfs: Path) -> None:
        # sysfs may not exist on some build -> skip
        if not sysfs.exists():
            return
        value = self._safe_read(persist)
        if value not in ("0", "1"):
            return
        self._safe_write(sysfs, f"r {value}")

    def _restore_offset(self, persist: Path, sysfs: Path, ch: str) -> None:
        if not sysfs.exists():
            return
        value = self._safe_read(persist)
        if not value:
            return
        try:
            en, h, v = [x.strip() for x in value.split(",", 2)]
        except ValueError:
            return
        if en and h and v:
            self._safe_write(sysfs, f"{ch} {en} {h} {v}")

    def parse_panels_luminance(self, r_reg_value: str, g_reg_value: str, b_reg_value: str) -> str:
        '''
        :param reg_value: str type, decimal
        :return: R: $r_luminance
                 G: $g_luminance
                 B: $b_luminance
        '''
        r_luminance = int(r_reg_value, 0)
        g_luminance = int(g_reg_value, 0)
        b_luminance = int(b_reg_value, 0)
        ret_str = f"R:{r_luminance}\nG:{g_luminance}\nB:{b_luminance}"
        return ret_str

    def _read_luminance_from_register(self, color_tag: str) -> str:
        dev = self.rgb_devices_map.get(color_tag)
        if not dev:
            return "0"
        return str(dev.read_16bit_data(0x200a14))

    def parse_panels_current(self, r_reg_value: str, g_reg_value: str, b_reg_value: str) -> str:
        '''
        :param reg_value: str type, decimal
        :return: R: $r_current
                 G: $g_current
                 B: $b_current
        '''
        r_current = int(r_reg_value, 0)
        g_current = int(g_reg_value, 0)
        b_current = int(b_reg_value, 0)

        ret_str = f"R:{r_current}\nG:{g_current}\nB:{b_current}"
        return ret_str

    def _read_current_from_register(self, color_tag: str) -> str:
        dev = self.rgb_devices_map.get(color_tag)
        if not dev:
            return "0"
        return str(dev.read_16bit_data(0x200100))

    def parse_panels_offset(self, enable: bool, r_reg_value: str, g_reg_value: str, b_reg_value: str) -> str:
        '''
        :param reg_value: str type, decimal
        :return: R($enabled): H:$r_x_offset, V:$r_y_offset
                 G($enabled): H:$g_x_offset, V:$g_y_offset
                 B($enabled): H:$b_x_offset, V:$b_y_offset
        '''

        r_total_offset = int(r_reg_value, 0)
        r_x_offset = (r_total_offset >> 8) & 0x1F
        r_y_offset = (r_total_offset) & 0x1F

        g_total_offset = int(g_reg_value, 0)
        g_x_offset = (g_total_offset >> 8) & 0x1F
        g_y_offset = (g_total_offset) & 0x1F

        b_total_offset = int(b_reg_value, 0)
        b_x_offset = (b_total_offset >> 8) & 0x1F
        b_y_offset = (b_total_offset) & 0x1F

        enabled = "enabled" if enable else "disabled"

        ret_str = (f"R({enabled}) H:{r_x_offset} V:{r_y_offset}\n"
                   f"G({enabled}) H:{g_x_offset} V:{g_y_offset}\n"
                   f"B({enabled}) H:{b_x_offset} V:{b_y_offset}")
        return ret_str


    def parse_single_panel_offset(self, reg_value: str) -> str:
        '''
        :param reg_value: str type, decimal
        :return: H:$x_offset, V:$y_offset

        x_offset = reg_value[12:8], range[0,20]
        y_offset = reg_value[4:0], range[0,12]
        '''
        total_offset = int(reg_value, 0)
        x_offset = (total_offset >> 8) & 0x1F
        y_offset = (total_offset) & 0x1F

        ret_str = f"H:{x_offset:02}, V:{y_offset:02}"
        return ret_str



    def _read_offset_from_register(self, color_tag: str) -> str:
        dev = self.rgb_devices_map.get(color_tag)
        if not dev:
            return "0"

        return str(dev.read_16bit_data(0x200a24))

    def oe_params_current_changed(self):
        '''
        :return:None
        read the new current value and write direct to the register
        '''
        rgb_data = {}
        # 定義正規表達式：匹配 字母(R/G/B) + 冒號 + 數字
        pattern = re.compile(r'([RGB]):\s*(\d+)')

        try:
            with open(self.sysfs_current, 'r', encoding='utf-8') as f:
                content = f.read()
                # 尋找所有匹配項
                matches = pattern.findall(content)

                # 將結果轉換為字典，例如 {'R': 512, 'G': 512, 'B': 512}
                rgb_data = {key: int(value) for key, value in matches}

                r_current = rgb_data.get('R')
                g_current = rgb_data.get('G')
                b_current = rgb_data.get('B')
                log.debug(f"r_current: {r_current}, g_current: {g_current}, b_current: {b_current}")


                self.red_i2c_device.write_16bit_data(0x200100, r_current)
                self.path_current_r.write_text(str(r_current))
                self.green_i2c_device.write_16bit_data(0x200100, g_current)
                self.path_current_g.write_text(str(g_current))
                self.blue_i2c_device.write_16bit_data(0x200100, b_current)
                self.path_current_b.write_text(str(b_current))
        except FileNotFoundError:
            log.error("錯誤：找不到檔案")
        except Exception as e:
            log.error(f"發生意外錯誤: {e}")

    def oe_params_luminance_changed(self):
        '''
        :return:None
        read the new current value and write direct to the register
        '''
        rgb_data = {}
        # 定義正規表達式：匹配 字母(R/G/B) + 冒號 + 數字
        pattern = re.compile(r'([RGB]):\s*(\d+)')

        try:
            with open(self.sysfs_luminance, 'r', encoding='utf-8') as f:
                content = f.read()
                # 尋找所有匹配項
                matches = pattern.findall(content)

                # 將結果轉換為字典，例如 {'R': 512, 'G': 512, 'B': 512}
                rgb_data = {key: int(value) for key, value in matches}

                r_luminance = rgb_data.get('R')
                g_luminance = rgb_data.get('G')
                b_luminance = rgb_data.get('B')
                log.debug(f"r_luminance: {r_luminance},g_luminance: {g_luminance}, b_luminance: {b_luminance}")

                if platform.machine() == 'x86_64':
                    pass
                else:
                    self.red_i2c_device.write_16bit_data(0x200a14, r_luminance)
                    self.path_lumin_r.write_text(str(r_luminance))
                    self.green_i2c_device.write_16bit_data(0x200a14, g_luminance)
                    self.path_lumin_g.write_text(str(g_luminance))
                    self.blue_i2c_device.write_16bit_data(0x200a14, b_luminance)
                    self.path_lumin_b.write_text(str(b_luminance))
        except FileNotFoundError:
            print("錯誤：找不到檔案")
        except Exception as e:
            print(f"發生意外錯誤: {e}")

    def oe_params_offset_changed(self):
        offsets = {}
        # 正規表達式解析：
        # ([RGB])          -> 捕捉顏色標籤
        # \((\w+)\)        -> 捕捉括號內的狀態 (enabled/disabled)
        # \s*H:(\d+)\s*V:(\d+) -> 捕捉 H 和 V 後面跟著的數字
        pattern = re.compile(r'([RGB])\((\w+)\)\s*H:(\d+)\s*V:(\d+)')

        try:
            with open(self.sysfs_offset, 'r', encoding='utf-8') as f:
                content = f.read()
                for match in pattern.finditer(content):
                    color, status, h_val, v_val = match.groups()
                    offsets[color] = {
                        'status': status,
                        'H': int(h_val),
                        'V': int(v_val)
                    }
        except FileNotFoundError:
            print(f"錯誤：找不到檔案 {self.sysfs_offset}")
        except Exception as e:
            print(f"解析時發生意外錯誤: {e}")

        for color, vals in offsets.items():
            # 根據你的 parse_panels_offset 邏輯：
            # H 位移在 bit[12:8]，V 位移在 bit[4:0]
            reg_value = (vals['H'] << 8) | (vals['V'])
            # 取得對應的 I2C 設備並寫入 0x200a24
            dev = self.rgb_devices_map.get(color)
            if dev and platform.machine() != 'x86_64':
                dev.write_16bit_data(0x200a24, reg_value)
            if color == 'R':
                r_offset_persist_str = f"1,{offsets[color]['H']},{offsets[color]['V']}"
                if "disable" in offsets[color]['status']:
                    r_offset_persist_str = f"0,{offsets[color]['H']},{offsets[color]['V']}"
                self.path_offset_r.write_text(r_offset_persist_str)
            elif color == 'G':
                g_offset_persist_str = f"1,{offsets[color]['H']},{offsets[color]['V']}"
                if "disable" in offsets[color]['status']:
                    g_offset_persist_str = f"0,{offsets[color]['H']},{offsets[color]['V']}"
                self.path_offset_g.write_text(g_offset_persist_str)
            elif color == 'B':
                b_offset_persist_str = f"1,{offsets[color]['H']},{offsets[color]['V']}"
                if "disable" in offsets[color]['status']:
                    b_offset_persist_str = f"0,{offsets[color]['H']},{offsets[color]['V']}"
                self.path_offset_b.write_text(b_offset_persist_str)

            log.debug(f"Updated {color} Offset: {hex(reg_value)}")

    def oe_params_flip_changed(self):
        log.warn("Not Implemented yet")

    def oe_params_mirror_changed(self):
        log.warn("Not Implemented yet")

    def init_sysfs_from_register(self):
        # handle the offset
        target_sysfs_offset_str = self.parse_panels_offset(True,
                                                           self._read_offset_from_register(self.RED_PANEL_TAG),
                                                           self._read_offset_from_register(self.GREEN_PANEL_TAG),
                                                           self._read_offset_from_register(self.BLUE_PANEL_TAG))
        log.debug(f"target_sysfs_offset_str: {target_sysfs_offset_str}")
        self._safe_write(self.sysfs_offset, target_sysfs_offset_str)

        #handle the current
        target_sysfs_current_str = self.parse_panels_current(self._read_current_from_register(self.RED_PANEL_TAG),
                                                             self._read_current_from_register(self.GREEN_PANEL_TAG),
                                                             self._read_current_from_register(self.BLUE_PANEL_TAG))
        log.debug(f"target_sysfs_current_str: {target_sysfs_current_str}")
        self._safe_write(self.sysfs_current, target_sysfs_current_str)

        # handle the luminance
        target_sysfs_luminance_str = self.parse_panels_luminance(self._read_luminance_from_register(self.RED_PANEL_TAG),
                                                                 self._read_luminance_from_register(self.GREEN_PANEL_TAG),
                                                                 self._read_luminance_from_register(self.BLUE_PANEL_TAG))
        log.debug(f"target_sysfs_luminance: {target_sysfs_luminance_str}")
        self._safe_write(self.sysfs_luminance, target_sysfs_luminance_str)

        log.debug("flip and mirror need to be implemented")
