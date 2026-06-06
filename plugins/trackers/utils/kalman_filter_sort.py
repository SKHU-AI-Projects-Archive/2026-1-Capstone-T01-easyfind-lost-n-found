import numpy as np

class KalmanFilter:
    def __init__(self, dim_x, dim_z):
        self.dim_x = dim_x
        self.dim_z = dim_z
        self.F = np.eye(dim_x)
        self.H = np.eye(dim_z, dim_x)
        self.P = np.eye(dim_x)
        self.R = np.eye(dim_z)
        self.Q = np.eye(dim_x)
        self.x = np.zeros((dim_x, 1))
        self.I = np.eye(dim_x)

    # 기존 상태를 바탕으로 다음 위치 예측
    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x
    
    # 측정값 z를 바탕으로 상태 업데이트
    def update(self, z):
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        S += 1e-6 * np.eye(self.dim_z)  # numerical stability
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        I_KH = self.I - K @ self.H
        self.P = I_KH @ self.P @ I_KH.T + K @ self.R @ K.T
