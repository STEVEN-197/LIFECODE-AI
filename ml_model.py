"""
LifeCode AI - Health Prediction ML Model
RandomForest with 9 features including ESP32 sensor inputs
Features: sleep, food, activity, stress, age, bmi,
          heart_rate (ESP32), gsr (ESP32), temperature (ESP32)
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class HealthPredictor:

    FEATURES = ['sleep', 'food_score', 'activity', 'stress',
                'age', 'bmi', 'heart_rate', 'gsr', 'temperature']

    def __init__(self):
        self.scaler           = StandardScaler()
        self.model_stress     = None
        self.model_metabolic  = None
        self.model_risk       = None
        self.is_trained       = False

    def _generate_data(self, n=1500):
        np.random.seed(42)
        sleep       = np.random.uniform(3, 12, n)
        food        = np.random.randint(1, 5, n).astype(float)
        activity    = np.random.gamma(2, 2, n).clip(0, 20)
        stress      = np.random.uniform(1, 10, n)
        age         = np.random.randint(18, 80, n).astype(float)
        bmi         = np.random.normal(22, 4, n).clip(15, 40)
        heart_rate  = np.random.normal(72, 12, n).clip(50, 130)
        gsr         = np.random.normal(5, 2, n).clip(0.5, 15)
        temperature = np.random.normal(36.5, 0.3, n).clip(35, 39)

        X = np.column_stack([sleep, food, activity, stress,
                             age, bmi, heart_rate, gsr, temperature])

        y_stress = (
            (10 - sleep) * 6 +
            stress * 7 +
            (heart_rate - 70) * 0.4 +
            gsr * 1.5 +
            (temperature - 36.5) * 6 +
            np.random.normal(0, 4, n)
        ).clip(0, 100)

        y_metabolic = (
            food * 12 +
            activity * 3.5 +
            (9 - sleep) * 2 +
            (100 - heart_rate) * 0.3 -
            (bmi - 22) * 1.5 +
            np.random.normal(0, 4, n)
        ).clip(0, 100)

        y_risk = (
            stress * 4 +
            (bmi - 22) * 1.5 +
            (age - 30) * 0.4 +
            (heart_rate - 70) * 0.3 +
            gsr * 1.2 -
            activity * 2 -
            sleep * 1.5 +
            np.random.normal(0, 4, n)
        ).clip(0, 100)

        return X, y_stress, y_metabolic, y_risk

    def train_model(self):
        print('Training ML models...')
        X, ys, ym, yr = self._generate_data(1500)

        Xtr, Xte, ystr, yste, ymtr, ymte, yrtr, yrte = \
            train_test_split(X, ys, ym, yr, test_size=0.2, random_state=42)

        Xtr_s = self.scaler.fit_transform(Xtr)
        Xte_s = self.scaler.transform(Xte)

        params = dict(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1)

        self.model_stress    = RandomForestRegressor(**params)
        self.model_metabolic = RandomForestRegressor(**params)
        self.model_risk      = RandomForestRegressor(**params)

        self.model_stress.fit(Xtr_s, ystr)
        self.model_metabolic.fit(Xtr_s, ymtr)
        self.model_risk.fit(Xtr_s, yrtr)

        self.is_trained = True

        r2s = self.model_stress.score(Xte_s, yste)
        r2m = self.model_metabolic.score(Xte_s, ymte)
        r2r = self.model_risk.score(Xte_s, yrte)
        print(f'Models trained | Stress R2:{r2s:.3f} | Metabolic R2:{r2m:.3f} | Risk R2:{r2r:.3f}')

    def predict(self, inputs):
        if not self.is_trained:
            raise RuntimeError('Call train_model() first.')
        X  = np.array(inputs).reshape(1, -1)
        Xs = self.scaler.transform(X)
        return {
            'stress_index':    round(float(np.clip(self.model_stress.predict(Xs)[0],    0, 100)), 1),
            'metabolic_score': round(float(np.clip(self.model_metabolic.predict(Xs)[0], 0, 100)), 1),
            'lifestyle_risk':  round(float(np.clip(self.model_risk.predict(Xs)[0],      0, 100)), 1),
        }
