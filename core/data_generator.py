import numpy as np
import pandas as pd
import os

def generate_synthetic_dataset(num_samples=5000, output_dir="../ml/datasets/synthetic"):
    os.makedirs(output_dir, exist_ok=True)

    data = []
    for _ in range(num_samples):
        # Випадкові швидкості (м/с)
        v1 = np.random.uniform(5, 50)
        v2 = np.random.uniform(5, 50)

        # Випадкові курси (градуси)
        heading1 = np.random.uniform(0, 360)
        heading2 = np.random.uniform(0, 360)

        # Початкові відстані (м)
        dist = np.random.uniform(100, 5000)

        # Висоти (м)
        alt1 = np.random.uniform(0, 500)
        alt2 = np.random.uniform(0, 500)

        # Обчислимо "загрозу" — умовно, якщо різниця курсів < 30° і відстань < 500 → collision risk
        collision_risk = int(abs(heading1 - heading2) < 30 and dist < 500 and abs(alt1 - alt2) < 50)

        data.append([v1, v2, heading1, heading2, dist, alt1, alt2, collision_risk])

    df = pd.DataFrame(data, columns=["v1", "v2", "heading1", "heading2", "distance", "alt1", "alt2", "collision_risk"])
    output_path = os.path.join(output_dir, "synthetic_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"✅ Generated {num_samples} samples → {output_path}")
    return df

if __name__ == "__main__":
    generate_synthetic_dataset()
