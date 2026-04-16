# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from jbd4040 import JBD4040
import time
# 定義晶片路徑，i.MX93 的 GPIO5 通常對應 gpiochip4
CHIP_PATH = '/dev/gpiochip0'
# 定義 Offset (Line 編號)
LINES = [6, 13, 19, 21, 26]


I2C_BUS = 1

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print('JBD4040_CTL_V2')
    jbd4040 = JBD4040()
    jbd4040.turn_off_mipi_dsi_output()
    time.sleep(1)
    jbd4040.power_on_seq_jbd4040()
    time.sleep(2)
    jbd4040.init_registers()
    time.sleep(2)
    jbd4040.turn_on_panel()
    time.sleep(2)
    jbd4040.turn_on_mipi_dsi_output()

    while True:
        time.sleep(1)
        jbd4040.get_panel_temp(jbd4040.RED_PANEL_TAG)
        jbd4040.get_panel_temp(jbd4040.GREEN_PANEL_TAG)
        jbd4040.get_panel_temp(jbd4040.BLUE_PANEL_TAG)


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
