import os
import joblib
import pickle
import base64
import json
from skopt import Optimizer

class SkoptOptimizer:
    def __init__(self, search_space, base_estimator='GP', n_initial_points=5, random_state=None):
        self.search_space = search_space
        self.optimizer = Optimizer(
            dimensions=search_space,
            base_estimator=base_estimator,
            n_initial_points=n_initial_points,
            random_state=random_state
        )
        self._ask_queue = []
        self._suggested = []
        self._results = []
        self.state = "ready"

    def suggest(self):
        if self.state != "ready":
            raise RuntimeError(f"Cannot suggest in state {self.state}")

        params = self.optimizer.ask()
        params_tuple = tuple(params)
        self._ask_queue.append(params_tuple)
        self._suggested.append(params_tuple)
        self.state = "waiting"
        return params

    def observe(self, params, result):
        if self.state != "waiting":
            raise RuntimeError(f"Cannot observe in state {self.state}")

        params_tuple = tuple(params)
        if params_tuple not in self._ask_queue:
            raise ValueError("The given parameters were not suggested by this optimizer.")

        self.optimizer.tell(list(params_tuple), result)
        self._ask_queue.remove(params_tuple)
        self._results.append((params_tuple, result))
        self.state = "ready"

    def best_params(self):
        if not self.optimizer.yi:
            return None
        best_index = self.optimizer.yi.index(min(self.optimizer.yi))
        return self.optimizer.Xi[best_index]

    def status(self):
        return {
            "state": self.state,
            "iterations": len(self._results),
            "best_score": min(self.optimizer.yi) if self.optimizer.yi else None,
        }
    
    def reset(self):
        self._ask_queue.clear()
        self._suggested.clear()
        self._results.clear()
        self.state = "ready"

    def save_state(self, path):
        """Save the entire optimizer state to disk."""
        data = {
            'optimizer': self.optimizer,
            'ask_queue': self._ask_queue,
            'suggested': self._suggested,
            'results': self._results,
            'state': self.state,
            'search_space': self.search_space
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(data, path)

    def get_classdata(self):
        """Serialize state to a Base64-encoded string suitable for DB storage."""
        raw = {
            'optimizer': self.optimizer,
            'ask_queue': self._ask_queue,
            'suggested': self._suggested,
            'results': self._results,
            'state': self.state,
            'search_space': self.search_space
        }
        pickled = pickle.dumps(raw)
        encoded = base64.b64encode(pickled).decode('utf-8')
        return encoded
    
    @classmethod
    def load_state(cls, encoded_str):
        """Deserialize from Base64 string."""
        pickled = base64.b64decode(encoded_str.encode('utf-8'))
        data = pickle.loads(pickled)
        
        obj = cls(search_space=data['search_space'])
        obj.optimizer = data['optimizer']
        obj._ask_queue = data['ask_queue']
        obj._suggested = data['suggested']
        obj._results = data['results']
        obj.state = data['state']
        return obj

    @classmethod
    def load_state_from_disk(cls, path):
        """Load optimizer from disk."""
        data = joblib.load(path)
        obj = cls(
            search_space=data['search_space']
        )
        obj.optimizer = data['optimizer']
        obj._ask_queue = data['ask_queue']
        obj._suggested = data['suggested']
        obj._results = data['results']
        obj.state = data['state']
        return obj
