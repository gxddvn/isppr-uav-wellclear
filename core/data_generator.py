import numpy as np
import pandas as pd
import os

def generate_synthetic_dataset(
    num_samples=10000,
    danger_ratio=0.3,
    output_dir="../ml/datasets/synthetic"
):
    os.makedirs(output_dir, exist_ok=True)

    data = []
    num_danger = int(num_samples * danger_ratio)
    num_safe = num_samples - num_danger

    for _ in range(num_safe):
        v1 = np.random.uniform(5, 50)
        v2 = np.random.uniform(5, 50)
        heading1 = np.random.uniform(0, 360)
        heading2 = np.random.uniform(0, 360)
        distance = np.random.uniform(500, 5000)
        alt1 = np.random.uniform(0, 500)
        alt2 = np.random.uniform(0, 500)

        alt_diff = alt1 - alt2
        heading_diff = (heading1 - heading2 + 180) % 360 - 180
        speed_diff = v1 - v2

        collision_risk = np.clip(
            0.2 * (1 - distance/5000) + 
            0.3 * (1 - abs(heading_diff)/180) + 
            0.3 * (1 - abs(alt_diff)/500), 
            0, 0.3
        )

        data.append([v1, v2, heading1, heading2, distance, alt1, alt2, alt_diff, heading_diff, speed_diff, collision_risk])

    for _ in range(num_danger):
        v1 = np.random.uniform(5, 50)
        v2 = np.random.uniform(5, 50)
        heading1 = np.random.uniform(0, 360)
        heading2 = (heading1 + np.random.uniform(-30, 30)) % 360
        distance = np.random.uniform(50, 300)
        alt1 = np.random.uniform(0, 500)
        alt2 = alt1 + np.random.uniform(-20, 20)

        # Новые признаки
        alt_diff = alt1 - alt2
        heading_diff = (heading1 - heading2 + 180) % 360 - 180
        speed_diff = v1 - v2

        collision_risk = np.clip(
            0.5 + 0.5*(1 - distance/300) + 
            0.2*(1 - abs(heading_diff)/30) + 
            0.2*(1 - abs(alt_diff)/20), 
            0, 1
        )

        data.append([v1, v2, heading1, heading2, distance, alt1, alt2, alt_diff, heading_diff, speed_diff, collision_risk])

    df = pd.DataFrame(data, columns=[
        "v1", "v2", "heading1", "heading2", "distance", 
        "alt1", "alt2", "alt_diff", "heading_diff", "speed_diff", 
        "collision_risk"
    ])

    output_path = os.path.join(output_dir, "synthetic_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"✅ Generated {num_samples} samples → {output_path}")

    return df

if __name__ == "__main__":
    generate_synthetic_dataset()
