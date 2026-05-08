import signal
import sys
import time

from PyQt5.QtCore import QCoreApplication, QTimer
from global_def import *
from jbd4040 import JBD4040
from oe_params_monitor import OEParamsMonitor





def main():
    log.debug(f"Welcome to JBD4040 ctl {Version}")
    # 使用 Non-GUI 的核心應用程式
    app = QCoreApplication(sys.argv)

    # ==========================================
    # 【新增】處理 Ctrl+C 的機制
    # ==========================================
    # 建立一個定時器，每 500 毫秒觸發一次（什麼都不做）。
    # 這是為了強迫 Qt 事件迴圈定期喚醒 Python 直譯器，這樣才能捕捉到 signal。
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    # 定義接收到 Ctrl+C 時要做的動作
    def sigint_handler(signum, frame):
        log.debug("接收到 Ctrl+C (KeyboardInterrupt)，準備結束程式...")
        app.quit()  # 觸發 app 結束事件迴圈

    # 註冊 SIGINT (Ctrl+C) 訊號
    signal.signal(signal.SIGINT, sigint_handler)
    # ==========================================

    jbd4040 = None # 先宣告，方便 finally 區塊判斷

    # Init JBD4040
    try:
        jbd4040 = JBD4040()
        jbd4040.turn_off_mipi_dsi_output()
        time.sleep(1)
        jbd4040.power_on_seq_jbd4040()
        time.sleep(1)
        jbd4040.init_registers()
        time.sleep(1)
        jbd4040.init_sysfs_from_register()
        # jbd4040.write_oe_params_with_persist_params()
        
        jbd4040.turn_on_panel()
        time.sleep(1)
        jbd4040.turn_on_mipi_dsi_output()

        if platform.machine() == 'x86_64':
            pass
        else:
            jbd4040.test_luminance_current()
            jbd4040.read_fmc_register_range()
            log.debug("########################################################")
            jbd4040.read_efuse_register_range()

        # 設定想要監控的檔案路徑（可以是多個）
        target_files = jbd4040.get_oe_params_paths_with_list_str()

        # 初始化監控物件
        monitor = OEParamsMonitor(target_files)
        monitor.install_slots(jbd4040.oe_params_current_changed,
                              jbd4040.oe_params_luminance_changed,
                              jbd4040.oe_params_offset_changed,
                              jbd4040.oe_params_flip_changed,
                              jbd4040.oe_params_mirror_changed)

        log.debug("檔案監控服務已啟動...")

        jbd4040.sync_oe_params_with_persist_params()

        '''
        TEST Start
        '''
        if platform.machine() == 'x86_64':
            pass
        else:
            # 測試讀取luminance/current
            for panel_tag in jbd4040.RGB_PANEL_TAG_LIST:
                log.debug(f"pantl_tag: {panel_tag}")
                log.debug(f"luminance of {panel_tag} : {jbd4040._read_luminance_from_register(panel_tag)}")

            luminance_file_str = jbd4040.parse_panels_luminance(
                jbd4040._read_luminance_from_register(jbd4040.RGB_PANEL_TAG_LIST[0]),
                jbd4040._read_luminance_from_register(jbd4040.RGB_PANEL_TAG_LIST[1]),
                jbd4040._read_luminance_from_register(jbd4040.RGB_PANEL_TAG_LIST[2]))
            log.debug(f" parse liminance : {luminance_file_str}")

            for panel_tag in jbd4040.RGB_PANEL_TAG_LIST:
                log.debug(f"luminance of {panel_tag} : {jbd4040._read_current_from_register(panel_tag)}")

            current_file_str = jbd4040.parse_panels_current(
                jbd4040._read_luminance_from_register(jbd4040.RGB_PANEL_TAG_LIST[0]),
                jbd4040._read_luminance_from_register(jbd4040.RGB_PANEL_TAG_LIST[1]),
                jbd4040._read_luminance_from_register(jbd4040.RGB_PANEL_TAG_LIST[2]))
            log.debug(f" parse current : {current_file_str}")

            for panel_tag in jbd4040.RGB_PANEL_TAG_LIST:
                log.debug(f"offset of {panel_tag} : {jbd4040.parse_single_panel_offset(jbd4040._read_offset_from_register(panel_tag))}")

            offset_file_str = jbd4040.parse_panels_offset(
                True,
                jbd4040._read_offset_from_register(jbd4040.RGB_PANEL_TAG_LIST[0]),
                jbd4040._read_offset_from_register(jbd4040.RGB_PANEL_TAG_LIST[0]),
                jbd4040._read_offset_from_register(jbd4040.RGB_PANEL_TAG_LIST[0]))
            log.debug(f" parse offset : {offset_file_str}")
        '''
        TEST End
        '''


        app.exec_()
    except Exception as e:
        # 【新增】捕捉其他所有未預期的錯誤
        log.error(f"程式執行中發生未預期的錯誤: {e}")

    finally:
        # 【新增】安全退出的清理機制
        # 無論是按 Ctrl+C、發生錯誤，還是正常結束，都會執行到這裡
        log.debug("開始執行清理作業...")
        if jbd4040 is not None:
            log.debug("正在關閉硬體輸出與電源...")
            # 這裡可以放你的關機/清理邏輯，避免硬體卡在不穩定的狀態
            try:
                jbd4040.turn_off_panel()
                jbd4040.power_off_seq_jbd4040()
                jbd4040.turn_off_mipi_dsi_output()
            except Exception as cleanup_error:
                log.error(f"清理硬體時發生錯誤: {cleanup_error}")

        log.debug("程式已安全退出。")
        sys.exit(0)


if __name__ == "__main__":
    main()