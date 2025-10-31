import os
import torch
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from ml.models import CollisionModel
from core.data_generator import generate_synthetic_dataset

MODEL_PATH = "./ml/models/collision_model_weights.pt"
INPUT_DIM = 10

class MLSystem:
    def __init__(self, dataset_dir="./ml/datasets/synthetic", model_dir="./ml/models", log_func=print):
        self.dataset_dir = dataset_dir
        self.model_dir = model_dir
        self.model_path = MODEL_PATH
        self.scaler_path = self.model_path.replace("_weights.pt", "_scaler.pkl")
        self.log = log_func
        self.model = None
        self.scaler = None

        self.log("🧠 Initializing ML System (PyTorch)...")
        self.setup()

    def setup(self):
        dataset_file = os.path.join(self.dataset_dir, "synthetic_dataset.csv")
        if not os.path.exists(dataset_file):
            self.log("📊 Dataset not found, generating synthetic dataset...")
            generate_synthetic_dataset(num_samples=5000, output_dir=self.dataset_dir)
            self.log("✅ Dataset generated")
        else:
            self.log("✅ Dataset found")

        if not os.path.exists(self.model_path):
            self.log("🤖 Model not found, starting training...")
            self.train_and_save()
            self.log("✅ Training complete")
        else:
            self.log("✅ Pre-trained model found")

        self.model, self.scaler = self.load_model_and_scaler()
        self.log("✅ ML System ready")

    def load_model_and_scaler(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError("Модель не знайдена. Виконай train_and_save().")
        
        # Создаем модель и загружаем веса
        model = CollisionModel(INPUT_DIM)
        state_dict = torch.load(self.model_path, map_location=torch.device("cpu"))
        model.load_state_dict(state_dict)
        model.eval()

        scaler = joblib.load(self.scaler_path) if os.path.exists(self.scaler_path) else StandardScaler()
        return model, scaler

    def train_and_save(self):
        dataset_path = os.path.join(self.dataset_dir, "synthetic_dataset.csv")
        # Загружаем CSV через pandas
        df = pd.read_csv(dataset_path)
        X = df.drop("collision_risk", axis=1).values
        y = df["collision_risk"].values

        if X.shape[1] != INPUT_DIM:
            raise ValueError(f"Dataset has {X.shape[1]} features, expected {INPUT_DIM}")

        # Масштабирование
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        joblib.dump(self.scaler, self.scaler_path)

        # Конвертируем в тензоры
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        y_tensor = torch.tensor(y.reshape(-1, 1), dtype=torch.float32)

        model = CollisionModel(INPUT_DIM)
        criterion = torch.nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

        for epoch in range(50):
            optimizer.zero_grad()
            outputs = model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            if (epoch+1) % 10 == 0:
                self.log(f"Epoch {epoch+1}/50, Loss: {loss.item():.4f}")

        torch.save(model.state_dict(), self.model_path)
        self.model = model

    def predict(self, features):
        if self.model is None or self.scaler is None:
            raise RuntimeError("ML System is not initialized correctly")
        features_scaled = self.scaler.transform([features])
        X_tensor = torch.tensor(features_scaled, dtype=torch.float32)
        with torch.no_grad():
            return self.model(X_tensor).item()
