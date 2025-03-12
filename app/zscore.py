from sklearn.preprocessing import StandardScaler
import numpy as np

def calculate_zscore(values):
    """ 計算 z-score 的函數 """
    scaler = StandardScaler()
    values = np.array(values).reshape(-1, 1)  # 將數據轉換為 2D 以供 StandardScaler 使用
    z_scores = scaler.fit_transform(values)
    return z_scores.flatten().tolist()
