from skopt import Optimizer

class SkoptOptimizer:
    def __init__(self, search_space, base_estimator='GP', n_initial_points=5, random_state=None):
        """
        search_space: list of skopt.space.Dimension (e.g., Real, Integer, Categorical)
        """
        self.optimizer = Optimizer(
            dimensions=search_space,
            base_estimator=base_estimator,
            n_initial_points=n_initial_points,
            random_state=random_state
        )
        self._ask_queue = []  # Store pending asks
        self._suggested = []  # For tracking what was asked
        self._results = []    # For tracking results
        self.state = "ready"  # State machine status

    def suggest(self):
        """Suggest next parameters to evaluate."""
        if self.state != "ready":
            raise RuntimeError(f"Cannot suggest in state {self.state}")

        params = self.optimizer.ask()
        self._ask_queue.append(params)
        self._suggested.append(params)
        self.state = "waiting"
        return params

    def observe(self, params, result):
        """Tell the optimizer the result of previously suggested params."""
        if self.state != "waiting":
            raise RuntimeError(f"Cannot observe in state {self.state}")

        if params not in self._ask_queue:
            raise ValueError("The given parameters were not suggested by this optimizer.")

        self.optimizer.tell(params, result)
        self._ask_queue.remove(params)
        self._results.append((params, result))
        self.state = "ready"

    def best_params(self):
        """Returns the best found parameters so far."""
        return self.optimizer.Xi[self.optimizer.yi.index(min(self.optimizer.yi))] if self.optimizer.yi else None

    def reset(self):
        """Optional: Reset internal state if needed (not a full optimizer reset)."""
        self._ask_queue.clear()
        self._suggested.clear()
        self._results.clear()
        self.state = "ready"

    def status(self):
        return {
            "state": self.state,
            "iterations": len(self._results),
            "best_score": min(self.optimizer.yi) if self.optimizer.yi else None,
        }