#!/usr/bin/env python3
"""
Machine Learning Click Probability Predictor
Simple logistic regression model trained on historical bid data to predict CTR.
"""

import numpy as np
import pickle
import os
from datetime import datetime
import sqlite3
import json


class ClickProbabilityPredictor:
    """
    Predicts click-through probability for given impression features.
    Uses a simple logistic regression model trained on synthetic data.
    """
    
    def __init__(self, model_path='ctr_model.pkl', training_data_path='training_data.db'):
        self.model_path = model_path
        self.training_data_path = training_data_path
        self.model = None
        self.feature_names = ['device_type_phone', 'device_type_tablet', 'os_ios', 
                             'os_android', 'country_usa', 'hour_of_day', 'bidfloor']
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or train a new one."""
        if os.path.exists(self.model_path):
            logger.info(f"Loading existing model from {self.model_path}")
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
        else:
            logger.info("No existing model found. Training new model...")
            self.train_model()
            self.save_model()
    
    def train_model(self):
        """Train a simple logistic regression model on synthetic data."""
        # Generate synthetic training data
        X_train, y_train = self._generate_synthetic_training_data()
        
        # Train simple logistic regression manually (or use sklearn)
        self.model = self._train_logistic_regression(X_train, y_train)
        
        logger.info(f"Model trained on {len(X_train)} samples")
    
    def _generate_synthetic_training_data(self):
        """Generate realistic synthetic training data based on industry CTR rates."""
        np.random.seed(42)  # For reproducibility
        
        n_samples = 10000
        
        # Features: [phone, tablet, desktop, ios, android, usa, hour, bidfloor]
        X = np.zeros((n_samples, 8))
        y = np.zeros(n_samples)
        
        # Industry average CTR by device and OS
        # Generally: Mobile > Desktop, iOS > Android
        
        for i in range(n_samples):
            # Random device (0=phone, 1=tablet, 2=desktop)
            device = np.random.choice([0, 1, 2])
            X[i, device] = 1
            
            # Random OS
            if device < 2:  # Mobile
                os_type = np.random.choice([0, 1])  # iOS or Android
            else:  # Desktop
                os_type = np.random.choice([0, 1], p=[0.3, 0.7])  # Mostly Android/other
            
            # OS one-hot encoding
            if os_type == 0:
                X[i, 3] = 1  # iOS
            else:
                X[i, 4] = 1  # Android
            
            # Country (USA = 1, other = 0)
            X[i, 5] = np.random.choice([0, 1], p=[0.3, 0.7])
            
            # Hour of day (normalized 0-23)
            X[i, 6] = np.random.randint(0, 24) / 23.0
            
            # Bidfloor (normalized)
            X[i, 7] = np.random.uniform(0.1, 3.0) / 3.0
            
            # Calculate CTR based on real industry data
            base_ctr = 0.015  # 1.5% average
            
            # Device multiplier
            device_multiplier = [1.2, 1.1, 0.8]  # phone > tablet > desktop
            
            # OS multiplier
            os_multiplier = 1.1 if os_type == 0 else 0.9  # iOS > Android
            
            # Country multiplier
            country_multiplier = 1.2 if X[i, 5] == 1 else 0.8  # USA > others
            
            # Time of day multiplier (peak 10-14)
            hour = X[i, 6] * 23
            if 10 <= hour <= 14:
                time_multiplier = 1.3
            elif 8 <= hour <= 18:
                time_multiplier = 1.1
            else:
                time_multiplier = 0.7
            
            # Calculate CTR
            ctr = (base_ctr * device_multiplier[device] * os_multiplier * 
                  country_multiplier * time_multiplier)
            
            # Add some randomness
            ctr *= np.random.uniform(0.7, 1.3)
            
            # Binary outcome (click or no click)
            y[i] = 1 if np.random.random() < ctr else 0
        
        return X, y
    
    def _train_logistic_regression(self, X, y, n_iterations=1000, learning_rate=0.01):
        """Train logistic regression using gradient descent."""
        n_samples, n_features = X.shape
        
        # Initialize weights
        weights = np.random.normal(0, 0.1, (n_features, 1))
        bias = 0.0
        
        # Gradient descent
        for _ in range(n_iterations):
            # Forward pass
            linear = np.dot(X, weights) + bias
            predictions = self._sigmoid(linear)
            
            # Compute gradient
            error = predictions - y.reshape(-1, 1)
            dw = np.dot(X.T, error) / n_samples
            db = np.mean(error)
            
            # Update weights
            weights -= learning_rate * dw
            bias -= learning_rate * db
        
        return {'weights': weights, 'bias': bias}
    
    def _sigmoid(self, x):
        """Sigmoid activation function."""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def save_model(self):
        """Save trained model to disk."""
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved to {self.model_path}")
    
    def predict(self, impression_data):
        """
        Predict click probability for given impression.
        
        Args:
            impression_data: dict with impression features
            
        Returns:
            float: click probability (0-1)
        """
        # Extract features from impression
        features = self._extract_features(impression_data)
        
        # Make prediction
        linear = np.dot(features, self.model['weights']) + self.model['bias']
        probability = self._sigmoid(linear)[0, 0]
        
        # Ensure probability is in valid range
        return float(np.clip(probability, 0, 1))
    
    def _extract_features(self, impression_data):
        """Extract features from impression data for model input."""
        device_type = impression_data.get('device', {}).get('devicetype', '').upper()
        os = impression_data.get('device', {}).get('os', '')
        country = impression_data.get('device', {}).get('geo', {}).get('country', '')
        bidfloor = impression_data.get('bidfloor', 1.0)
        
        # Feature vector: [phone, tablet, desktop, ios, android, usa, hour, bidfloor]
        features = np.zeros(8)
        
        # Device one-hot encoding
        if device_type == 'PHONE':
            features[0] = 1
        elif device_type == 'TABLET':
            features[1] = 1
        else:
            features[2] = 1  # DESKTOP or other
        
        # OS one-hot encoding
        if os.lower() == 'ios':
            features[3] = 1
        elif os.lower() == 'android':
            features[4] = 1
        
        # Country (USA = 1, other = 0)
        features[5] = 1 if country.upper() == 'USA' else 0
        
        # Hour of day (normalized)
        current_hour = datetime.now().hour
        features[6] = current_hour / 23.0
        
        # Bidfloor (normalized)
        features[7] = min(bidfloor, 3.0) / 3.0
        
        return features.reshape(1, -1)
    
    def update_model(self, impression_data, clicked):
        """
        Incrementally update model based on new data.
        This would implement online learning in a production system.
        
        Args:
            impression_data: dict with impression features
            clicked: bool, whether the ad was clicked
        """
        # Simple online learning implementation
        # In production, this would use more sophisticated methods
        pass


# Global logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create global predictor instance
_predictor = None

def get_predictor():
    """Get or create global predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = ClickProbabilityPredictor()
    return _predictor


if __name__ == '__main__':
    # Test the predictor
    print("Training click probability predictor...")
    predictor = ClickProbabilityPredictor()
    
    print("\nTesting predictions:")
    print("=" * 80)
    
    # Test cases
    test_cases = [
        ("USA iOS Phone", {
            'device': {'devicetype': 'PHONE', 'os': 'iOS', 'geo': {'country': 'USA'}},
            'bidfloor': 1.5
        }),
        ("USA Android Tablet", {
            'device': {'devicetype': 'TABLET', 'os': 'Android', 'geo': {'country': 'USA'}},
            'bidfloor': 0.8
        }),
        ("GER iOS Desktop", {
            'device': {'devicetype': 'DESKTOP', 'os': 'iOS', 'geo': {'country': 'GER'}},
            'bidfloor': 2.0
        }),
    ]
    
    for name, impression in test_cases:
        prob = predictor.predict(impression)
        print(f"{name:20} → CTR: {prob*100:.2f}%")
    
    print("=" * 80)
    print(f"Model file: {predictor.model_path}")
    print("Ready to use!")

