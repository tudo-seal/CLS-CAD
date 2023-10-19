def combine_motions(motion1: str, motion2: str):
    if motion1 == motion2:
        return motion1
    if motion1 == "Rigid":
        return motion2
    if motion2 == "Rigid":
        return motion1
    return "Ball"
