import sys
from PyQt5.QtCore import QFileSystemWatcher, QObject, pyqtSlot
from global_def import *

class OEParamsMonitor(QObject):
    def __init__(self, watch_files):
        super().__init__()

        # 1. 初始化監控器
        self.watcher = QFileSystemWatcher()
        self.watcher.addPaths(watch_files)

        # 2. 連接檔案變更訊號
        self.watcher.fileChanged.connect(self.on_file_changed)

        log.debug(f"正在監控檔案: {watch_files}")

    @pyqtSlot(str)
    def on_file_changed(self, path):
        """當被監控的檔案發生變更（寫入、修改）時會觸發此函式"""
        log.debug(f"偵測到變動：{path}")

        try:
            # 讀取檔案內容，根據內容決定控制邏輯
            with open(path, 'r') as f:
                content = f.read().strip()

            self.execute_control_logic(content)

        except Exception as e:
            log.debug(f"讀取檔案或執行控制時發生錯誤: {e}")

        # 注意：在某些作業系統或編輯器中，檔案存檔會觸發「刪除並重建」
        # 這會導致 watcher 失去追蹤，因此保險起見可以重新 addPath
        if path not in self.watcher.files():
            self.watcher.addPath(path)

    def execute_control_logic(self, cmd_value):
        """
        這裡放置你對 jbd4040 的控制邏輯
        """
        log.debug(f"依據檔案內容 '{cmd_value}' 執行 JBD4040 控制指令...")
        # TODO: 實作控制代碼
        if cmd_value == "STOP":
            log.debug(">>> 執行停止充電指令")
        elif cmd_value == "START":
            log.debug(">>> 執行啟動充電指令")