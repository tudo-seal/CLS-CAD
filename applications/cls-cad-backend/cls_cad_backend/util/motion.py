def combine_motions(motion1: str, motion2: str):
    """
    Composes two motions. If one JointOrigin is Rigid, it follow the motion the other
    JointOrigin permits. If two motions are the same, their composition is their
    identity. If both motions are different and not-rigid, this is undefined behaviour,
    so the least restrictive Joint type is chosen, a ball joint, constraining no axes.

    :param motion1: The first motion.
    :param motion2: The second motion.
    :return: The result of composing the motions.
    """
    if motion1 == motion2:
        return motion1
    if motion1 == "Rigid":
        return motion2
    if motion2 == "Rigid":
        return motion1
    return "Ball"
