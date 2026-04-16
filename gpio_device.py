import gpiod
from gpiod.line import Direction, Value


class GPIOController:
    def __init__(self, chip_path='/dev/gpiochip0', pins=None):
        if pins is None:
            pins = [6, 13, 19, 21, 26]
        self.chip_path = chip_path
        self.pins = pins
        self.request = None

    # Function 1: 初始化並請求線路
    def init_gpio(self):
        try:
            # 請求多個線路並設定為輸出
            self.request = gpiod.request_lines(
                self.chip_path,
                consumer="imx93-controller",
                config={
                    tuple(self.pins): gpiod.LineSettings(
                        direction=Direction.OUTPUT,
                        output_value=Value.INACTIVE
                    )
                }
            )
            print(f"GPIO 資源已初始化: {self.pins}")
        except Exception as e:
            print(f"初始化失敗: {e}")
            return PermissionError

        return 0

    # Function 2: 設定單一腳位 High/Low
    def set_level(self, offset, is_high):
        if self.request is None:
            print("錯誤：請先呼叫 init_gpio()")
            return

        val = Value.ACTIVE if is_high else Value.INACTIVE
        self.request.set_value(offset, val)
        print(f"Offset {offset} 已設為 {'HIGH' if is_high else 'LOW'}")

    def set_multiple_levels(self, mapping):
        """
        傳入字典，例如: {6: True, 26: False}
        這會同時更新 6 號腳位為 High，26 號腳位為 Low
        """
        if not self.request:
            print("錯誤：請先初始化")
            return

        # 將布林值字典轉換為 libgpiod 的 Value 字典
        values_dict = {
            offset: (Value.ACTIVE if state else Value.INACTIVE)
            for offset, state in mapping.items()
        }

        self.request.set_values(values_dict)
        print(f"已同步更新狀態: {mapping}")

    def close(self):
        if self.request:
            self.request.release()
            print("GPIO 資源已釋放")
