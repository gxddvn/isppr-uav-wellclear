import os
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
import joblib
from ml.models import CollisionModel

DATA_PATH = "./datasets/synthetic/synthetic_dataset.csv"
MODEL_DIR = "./ml/models"
MODEL_PATH = os.path.join(MODEL_DIR, "collision_model_weights.pt")

def load_data():
    df = pd.read_csv(DATA_PATH)
    X = df.drop("collision_risk", axis=1).values
    y = df["collision_risk"].values
    return X, y

def train_and_save():
    os.makedirs(MODEL_DIR, exist_ok=True)
    X, y = load_data()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, MODEL_PATH.replace("_weights.pt", "_scaler.pkl"))
    print("✅ Scaler saved")

    X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
    y_tensor = torch.tensor(y.reshape(-1,1), dtype=torch.float32)

    model = CollisionModel(X.shape[1])
    criterion = torch.nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(15):
        optimizer.zero_grad()
        outputs = model(X_tensor)
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()
        if (epoch+1) % 5 == 0:
            print(f"Epoch {epoch+1}/15, Loss: {loss.item():.4f}")

    torch.save(model.state_dict(), MODEL_PATH)
    print(f"✅ Model weights saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_and_save()
