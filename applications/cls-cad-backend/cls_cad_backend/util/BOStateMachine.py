from statemachine import StateMachine, State

class BOStateMachine(StateMachine):
    # Define states
    initial = State("Startup State", initial=True)
    waiting_for_mp_results = State("Ready: Waiting for MP Results")
    calculating_new_constraints = State("Busy: Calculating new synthesis constraints")

    # Define transitions
    to_synthesis = initial.to(calculating_new_constraints)
    to_calculating_new_constraints = waiting_for_mp_results.to(calculating_new_constraints)
    to_waiting_for_mp_results = calculating_new_constraints.to(waiting_for_mp_results)

    def __init__(self):
        super().__init__()
        self.cycle_counter = 0
        self.optimal_vector = []
        self.PLACEHOLDER_hyperparameters = {}
    
    def on_enter_initial(self):
        print("STARTUP_STATE")
        # placeholder logic to initialize BO framework
        self.to_calculating_new_constraints()

    def on_enter_waiting_for_mp_results(self):
        print("READY_WAITING_FOR_MP_RESULTS")
        self.to_calculating_new_constraints()


    def on_enter_calculating_new_constraints(self):
        print("BUSY_CALCULATING_NEW_CONSTRAINTS")
        # 
        self.to_waiting_for_mp_results()
