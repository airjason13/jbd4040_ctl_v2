import sys
from PyQt5.QtCore import QFileSystemWatcher, QObject, pyqtSlot, pyqtSignal
from global_def import *

class OEParamsMonitor(QObject):
    qtsignal_current_changed = pyqtSignal(str)
    qtsignal_luminance_changed = pyqtSignal(str)
    qtsignal_offset_changed = pyqtSignal(str)
    qtsignal_flip_changed = pyqtSignal(str)
    qtsignal_mirror_changed = pyqtSignal(str)

    qtsignal_file_changed = pyqtSignal(str)
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
            if "current" in path:
                self.qtsignal_current_changed.emit(path)
            elif "luminance" in path:
                self.qtsignal_luminance_changed.emit(path)
            elif "offset" in path:
                self.qtsignal_offset_changed.emit(path)
            elif "flip" in path:
                self.qtsignal_flip_changed.emit(path)
            elif "mirror" in path:
                self.qtsignal_mirror_changed.emit(path)

        except Exception as e:
            log.debug(f"讀取檔案或執行控制時發生錯誤: {e}")

        # 注意：在某些作業系統或編輯器中，檔案存檔會觸發「刪除並重建」
        # 這會導致 watcher 失去追蹤，因此保險起見可以重新 addPath
        # if path not in self.watcher.files():
        #    self.watcher.addPath(path)

    def install_slots(self, qtslot_current_changed,
                      qtslot_luminance_changed,
                      qtslot_offset_changed,
                      qtslot_flip_changed,
                      qtslot_mirror_changed):
        self.qtsignal_current_changed.connect(qtslot_current_changed)
        self.qtsignal_luminance_changed.connect(qtslot_luminance_changed)
        self.qtsignal_offset_changed.connect(qtslot_offset_changed)
        self.qtsignal_flip_changed.connect(qtslot_flip_changed)
        self.qtsignal_mirror_changed.connect(qtslot_mirror_changed)
