from statemachine import StateMachine, State

class PlannerStateMachine(StateMachine):
    # Define states
    generate_predicate = State("Generate Predicate", initial=True)
    performing_synthesis = State("Expecting Synthesis Request")
    performing_motion_planning = State("Expecting Motion Planning Request")

    # Define transitions
    to_synthesis = generate_predicate.to(performing_synthesis)
    to_motion_planning = performing_synthesis.to(performing_motion_planning)
    to_generate_predicate = performing_motion_planning.to(generate_predicate)

    def on_enter_generate_predicate(self):
        print("\n[STATE] GENERATE_PREDICATE")
        # BO framework generates a predicate
        # Placeholder logic
        self.to_synthesis()

    def on_enter_performing_synthesis(self):
        print("\n[STATE] performing_synthesis")
        # backend receives a synthesis request from fusion and generates a list of assemblies
        # Placeholder logic
        self.to_motion_planning()


    def on_enter_performing_motion_planning(self):
        print("\n[STATE] performing_motion_planning")
        # backend receives a single assembly and performs motion planning
        # update BO
        # Placeholder logic
        self.to_generate_predicate()
