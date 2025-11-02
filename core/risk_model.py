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
    """
    Спрощена оцінка колаборативного ризику (10 ключові параметри) з урахуванням gamma і min_altitude.
    """
    total_risk = 0.0
    if not obstacles:
        return 0.0

    for obs in obstacles:
        # Відстань та різниця по висоті
        dist = compute_distance(uav.position, obs.position)
        alt_diff = abs(uav.altitude - obs.altitude)
        heading_diff = compute_heading_diff(uav.rotation[1], obs.rotation[1])
        speed_diff = abs(uav.speed - obs.speed)

        # === Формуємо features для ML ===
        v1 = uav.speed
        v2 = obs.speed
        heading1 = uav.rotation[1]
        heading2 = obs.rotation[1]
        distance = dist
        alt1 = uav.altitude
        alt2 = obs.altitude

        features = [v1, v2, heading1, heading2, distance, alt1, alt2, alt_diff, heading_diff, speed_diff]
        risk_ml = float(ml_system.predict(features))

        # Геометричний ризик із урахуванням мінімальної висоти
        height_factor = 1.0 if uav.altitude >= min_altitude else 1.0 + (min_altitude - uav.altitude)/min_altitude
        risk_geo = math.exp(-dist / 100) * height_factor

        # Комбінуємо ризики з гамою (γ-норма)
        risk = (0.7 * risk_ml)**gamma + (0.3 * risk_geo)**gamma
        total_risk += risk

    # Середній ризик із урахуванням γ-норми
    avg_risk = (total_risk / len(obstacles))**(1.0/gamma)
    return min(max(avg_risk, 0.0), 1.0)


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
