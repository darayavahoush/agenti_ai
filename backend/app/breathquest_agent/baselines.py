"""
Baselines for the comparison ladder:
  1. rule-based
  2. contextual bandit
  3. tabular Q-learning
  4. deep policy (PPO / RecurrentPPO) -- loaded directly in service.py
"""

import random
import numpy as np


class RuleBasedAgent:
    """Fixed heuristic: raise difficulty on a streak of successes, lower on a
    streak of failures. No learning, no memory beyond the recent window."""

    def act(self, obs: np.ndarray) -> int:
        success_rate, difficulty, frustration, severity_numeric, is_targeted_sound = obs
        if frustration > 0.6:
            return 0
        if success_rate > 0.85:
            return 2
        if success_rate < 0.6:
            return 0
        return 1


class EpsilonGreedyBanditAgent:
    """Contextual bandit over a coarse discretization of
    (success_rate bucket, frustration bucket) -> action."""

    def __init__(self, epsilon: float = 0.1, lr: float = 0.1, n_buckets: int = 5):
        self.epsilon = epsilon
        self.lr = lr
        self.n_buckets = n_buckets
        self.q_table = {}

    def _bucket(self, obs: np.ndarray):
        success_rate, difficulty, frustration, severity_numeric, is_targeted_sound = obs
        sb = min(self.n_buckets - 1, int(success_rate * self.n_buckets))
        fb = min(self.n_buckets - 1, int(frustration * self.n_buckets))
        sevb = min(2, int(severity_numeric * 3))
        tb = int(round(is_targeted_sound))
        return (sb, fb, sevb, tb)

    def act(self, obs: np.ndarray) -> int:
        key = self._bucket(obs)
        if key not in self.q_table:
            self.q_table[key] = [0.0, 0.0, 0.0]
        if random.random() < self.epsilon:
            return random.randint(0, 2)
        return int(np.argmax(self.q_table[key]))

    def update(self, obs: np.ndarray, action: int, reward: float):
        key = self._bucket(obs)
        if key not in self.q_table:
            self.q_table[key] = [0.0, 0.0, 0.0]
        q = self.q_table[key][action]
        self.q_table[key][action] = q + self.lr * (reward - q)


class TabularQAgent:
    """Rung 3: proper Q-learning with a Bellman update, bootstrapping off
    the next state's max Q-value."""

    def __init__(self, epsilon: float = 0.15, lr: float = 0.1, gamma: float = 0.95, n_buckets: int = 5):
        self.epsilon = epsilon
        self.lr = lr
        self.gamma = gamma
        self.n_buckets = n_buckets
        self.q_table = {}

    def _bucket(self, obs: np.ndarray):
        success_rate, difficulty, frustration, severity_numeric, is_targeted_sound = obs
        sb = min(self.n_buckets - 1, int(success_rate * self.n_buckets))
        db = min(self.n_buckets - 1, int(difficulty * self.n_buckets))
        fb = min(self.n_buckets - 1, int(frustration * self.n_buckets))
        sevb = min(2, int(severity_numeric * 3))
        tb = int(round(is_targeted_sound))
        return (sb, db, fb, sevb, tb)

    def _ensure(self, key):
        if key not in self.q_table:
            self.q_table[key] = [0.0, 0.0, 0.0]

    def act(self, obs: np.ndarray) -> int:
        key = self._bucket(obs)
        self._ensure(key)
        if random.random() < self.epsilon:
            return random.randint(0, 2)
        return int(np.argmax(self.q_table[key]))

    def update(self, obs: np.ndarray, action: int, reward: float, next_obs: np.ndarray, done: bool):
        key = self._bucket(obs)
        next_key = self._bucket(next_obs)
        self._ensure(key)
        self._ensure(next_key)
        target = reward if done else reward + self.gamma * max(self.q_table[next_key])
        q = self.q_table[key][action]
        self.q_table[key][action] = q + self.lr * (target - q)
