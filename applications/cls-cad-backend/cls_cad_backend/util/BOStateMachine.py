from statemachine import StateMachine, State

class BOStateMachine(StateMachine):
    # Define states
    generate_predicate = State("Generate Predicate", initial=True)
    performing_synthesis = State("Performing Synthesis")
    performing_motion_planning = State("Performing Motion Planning")

    # Define transitions
    to_synthesis = generate_predicate.to(performing_synthesis)
    to_motion_planning = performing_synthesis.to(performing_motion_planning)
    to_generate_predicate = performing_motion_planning.to(generate_predicate)

    def on_enter_generate_predicate(self):
        print("GENERATE_PREDICATE")
        # BO framework generates a predicate
        # Placeholder logic
        # send predicate back to fusion so fusion can make rest call
        self.to_synthesis()

    def on_enter_performing_synthesis(self):
        print("PERFORMING_SYNTHESIS")
        # backend receives a synthesis request from fusion and generates a list of assemblies
        

        # done in server.py self.to_motion_planning()


    def on_enter_performing_motion_planning(self):
        print("PERFORMING_MOTION_PLANNING")
        # backend receives a single assembly and performs motion planning
        # update BO
        # Placeholder logic
        self.to_generate_predicate()
