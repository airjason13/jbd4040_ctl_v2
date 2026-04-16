# 根據手冊規範定義參數
START_ADDR = 0x250000  # Gamma Table 0 起始位址
NUM_POINTS = 256       # 每個 Table 包含 256 個 16-bit 數據
GAMMA_EN_REG = 0x200200 # Gamma 使能暫存器地址
MAX_DRIVE_VALUE = 1023

# 1. 預先計算 Gamma 1.0 的線性數據 (10-bit 精度: 0-1023)
# 公式：(當前階數 / 最大階數) * 最大驅動值
gamma_1_0_data = [round((i / 255.0) * 1023) for i in range(NUM_POINTS)]
gamma_2_2_data = [
                    round(((i /255.0) ** (2.2)) * MAX_DRIVE_VALUE)
                    for i in range(NUM_POINTS)
                ]
