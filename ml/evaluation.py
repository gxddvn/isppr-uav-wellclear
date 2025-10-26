import os
import torch
import numpy as np
import joblib
from sklearn.metrics import roc_auc_score, accuracy_score
from ml.models import CollisionModel

MODEL_PATH = "./ml/models/collision_model_weights.pt"
SCALER_PATH = MODEL_PATH.replace("_weights.pt", "_scaler.pkl")
DATASET_PATH = "./ml/datasets/synthetic/synthetic_dataset.csv"  # замените на ваш датасет

def load_dataset(path):
    data = np.loadtxt(path, delimiter=",")
    X, y = data[:, :-1], data[:, -1]
    return X, y

def evaluate_model():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        raise FileNotFoundError("Модель или scaler не найдены. Сначала выполните train_and_save().")
    
    # Загружаем scaler
    scaler = joblib.load(SCALER_PATH)
    
    # Загружаем модель
    input_dim = None
    X, y = load_dataset(DATASET_PATH)
    input_dim = X.shape[1]
    model = CollisionModel(input_dim)
    state_dict = torch.load(MODEL_PATH, map_location=torch.device("cpu"))
    model.load_state_dict(state_dict)
    model.eval()
    
    # Применяем scaler
    X_scaled = scaler.transform(X)
    X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
    
    with torch.no_grad():
        y_pred = model(X_tensor).numpy().flatten()
    
    # Метрики
    y_pred_label = (y_pred >= 0.5).astype(int)
    acc = accuracy_score(y, y_pred_label)
    auc = roc_auc_score(y, y_pred)
    
    print(f"Accuracy: {acc:.4f}")
    print(f"ROC AUC: {auc:.4f}")

if __name__ == "__main__":
    evaluate_model()
