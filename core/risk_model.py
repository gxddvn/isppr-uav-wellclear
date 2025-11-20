import numpy as np
import math

def compute_distance(obj1_pos, obj2_pos):
    return np.linalg.norm(np.array(obj1_pos) - np.array(obj2_pos))

def compute_alt_diff(obj1_pos, obj2_pos):
    return abs(obj1_pos[1] - obj2_pos[1])

def compute_heading_diff(heading1, heading2):
    """
    heading1, heading2 — це списки [pitch, yaw, roll].
    Повертає різницю тільки по yaw.
    """
    yaw1 = heading1[1] if isinstance(heading1, (list, tuple, np.ndarray)) else heading1
    yaw2 = heading2[1] if isinstance(heading2, (list, tuple, np.ndarray)) else heading2
    return abs((yaw1 - yaw2 + 180) % 360 - 180)

def compute_combined_risk(*risks, gamma=2.0):
    """
    Об'єднання декількох ризиків через γ-норму
    """
    risks = np.array(risks)
    return (np.sum(risks**gamma))**(1.0/gamma)

def compute_collaborative_risk(uav, obstacles, ml_system, gamma=2.0, min_altitude=0.0):

    if not obstacles:
        return 0.0

    # межі зон (масштабовані)
    red_R    = uav.safe_zones["red"]    * uav.scale
    yellow_R = uav.safe_zones["yellow"] * uav.scale
    green_R  = uav.safe_zones["green"]  * uav.scale

    zone_coefficients = {
        "green":  (0.0, 0.3),
        "yellow": (0.3, 0.7),
        "red":    (0.7, 1.0),
    }

    risks = []

    for obs in obstacles:

        dist = np.linalg.norm(np.array(uav.position) - np.array(obs.position))
        alt_diff = abs(uav.altitude - obs.altitude)
        heading_diff = abs((uav.rotation[1] - obs.rotation[1] + 180) % 360 - 180)
        speed_diff = abs(uav.speed - obs.speed)

        # -----------------------------
        # Визначаємо реальну зону
        # -----------------------------
        if dist > green_R:
            # поза зонами
            geo_risk = 0.0
        elif dist > yellow_R:
            zone = "green"
            zone_R = green_R
        elif dist > red_R:
            zone = "yellow"
            zone_R = yellow_R
        else:
            zone = "red"
            zone_R = red_R

        if dist <= green_R:
            min_risk, max_risk = zone_coefficients[zone]

            # фактор 0..1 залежно від відстані всередині ЗОНИ
            factor = np.clip((zone_R - dist) / zone_R, 0.0, 1.0)

            # фізична частина
            height_factor = (1 - min(alt_diff / (100.0 * uav.scale), 1.0)) ** 2
            heading_factor = 1.0 + 0.5 * (1.0 - math.cos(math.radians(heading_diff)))
            speed_factor = 1.0 + min(speed_diff / 200.0, 1.0) * 0.3

            base = factor * height_factor * heading_factor * speed_factor

            # масштабування до діапазону цієї зони
            geo_risk = min_risk + base * (max_risk - min_risk)
            geo_risk = np.clip(geo_risk, min_risk, max_risk)

        # ML коректор
        features = [
            uav.speed, obs.speed, uav.rotation[1], obs.rotation[1],
            dist, uav.altitude, obs.altitude,
            alt_diff, heading_diff, speed_diff
        ]
        ml_risk = float(ml_system.predict(features))

        risk = 0.8 * geo_risk + 0.2 * ml_risk
        risks.append(np.clip(risk, 0.0, 1.0))

    avg_risk = (sum(r ** gamma for r in risks) / len(risks)) ** (1.0 / gamma)
    return np.clip(avg_risk, 0.0, 1.0)


def wald(payoff_matrix):
    """
    Метод Вальда (Maximin)
    payoff_matrix: numpy array, строки = действия, столбцы = состояния
    """
    min_values = np.min(payoff_matrix, axis=1)
    return np.argmax(min_values)  # индекс действия с максимальным минимальным выигрышем

def hurwicz(payoff_matrix, alpha=0.7):
    """
    Метод Гурвица
    alpha: коэффициент пессимизма (0-1)
    """
    min_values = np.min(payoff_matrix, axis=1)
    max_values = np.max(payoff_matrix, axis=1)
    H = alpha * min_values + (1 - alpha) * max_values
    return np.argmax(H)

def laplace(payoff_matrix):
    """
    Метод Лапласа (среднее по всем состояниям)
    """
    avg_values = np.mean(payoff_matrix, axis=1)
    return np.argmax(avg_values)

def savage(payoff_matrix):
    """
    Метод Севиджа (минимизация максимального сожаления)
    """
    max_in_columns = np.max(payoff_matrix, axis=0)
    regret_matrix = max_in_columns - payoff_matrix
    max_regret = np.max(regret_matrix, axis=1)
    return np.argmin(max_regret)

def hybrid_decision(payoff_matrix, current_risk):
    """
    Гібридний метод вибору рішення:
    - високий ризик  → Вальда (максимальна безпека)
    - середній ризик → Гурвіца (баланс)
    - низький ризик  → Лапласа (нейтрально)
    """

    if current_risk > 0.7:
        decision = wald(payoff_matrix)
        strategy = "Wald (Safe)"
    elif 0.3 < current_risk <= 0.7:
        # робимо коефіцієнт α динамічним — чим більший ризик, тим песимістичніше
        alpha = np.clip(current_risk, 0.4, 0.9)
        decision = hurwicz(payoff_matrix, alpha=alpha)
        strategy = f"Hurwicz (α={alpha:.2f})"
    else:
        decision = laplace(payoff_matrix)
        strategy = "Laplace (Neutral)"

    return decision, strategy
