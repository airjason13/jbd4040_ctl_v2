import sys
import time
from pathlib import Path
from global_def import *
from gpio_device import GPIOController
from i2c_device import I2CDevice
from gamma import *
from pathlib import Path


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
        if platform.machine() == 'x86_64':
            self.gpio_chip_path = _gpio_chip_path
            self.i2c_bus = _i2c_bus

            # step.1 get gpio controller first
            self.gpio_ctrl = None

            # get smbus2 controller
            self.red_i2c_device = None
            self.green_i2c_device = None
            self.blue_i2c_device = None
            self.all_i2c_device = None

            self.rgb_devices = [
                (self.red_i2c_device, "Red"),
                (self.green_i2c_device, "Green"),
                (self.blue_i2c_device, "Blue")
            ]
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
            self.sysfs_temperature,
            self.sysfs_flip,
            self.sysfs_mirror,
            self.sysfs_offset,
        ]
        self.check_oe_params_exist()

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
        self.check_persist_params_exist()

        # 將persist params 寫入 oe params
        self.write_oe_params_with_persist_params()

    def check_persist_params_exist(self):
        for p in self.path_persist_params:
            if not p.exists():
                p.touch(exist_ok=True)

    def write_oe_params_with_persist_params(self):
        log.warn("Should check params content later")



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
        if platform.machine() == 'x86_64':
            log.debug(f"x84_64 platform turn_on_panel")
            return
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
    def restore_all(self) -> None:
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