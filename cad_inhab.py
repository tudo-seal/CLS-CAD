from glob import glob1
import json
from typing import Iterable
from uuid import uuid4
from cls_python import *


class Jsonify:

    def __call__(self, x):
        return Jsonify(self.config, [*self.data, x], self.description)

    def __str__(self):
        return deep_str(self.data)

    def __init__(self, config, data, description):
        self.config = config
        self.data = data
        self.description = description

    def to_dict(self):
        return dict(part=self.description,
                    provides=self.config.provides,
                    **{
                        label: bauteil.to_dict()
                        for (label,
                             bauteil) in zip(self.config.jointorder, self.data)
                    })


class Part(object):

    def __call__(self, x):
        return Jsonify(x, [], self.payload)

    def __repr__(self):
        return ""

    def __str__(self):
        return ""

    def __eq__(self, other):
        return isinstance(other, Part)

    def __hash__(self):
        return hash(self.payload)

    def __init__(self, payload):
        # Create combinator type here based on some JSON payload in future
        self.payload = payload


#additional info about the parts configuration options
class Config:

    def __init__(self, jointorder, provides):
        # Create combinator type here based on some JSON payload in future
        self.jointorder = jointorder
        self.provides = provides


if __name__ == "__main__":

    steel = Constructor("steel")
    steel410 = Constructor("steel410")
    steel440 = Constructor("steel440")

    xl430horn = Constructor("xl430horn")
    xl430hornmount = Constructor("xl430hornmount")
    baseplate = Constructor("baseplate")
    baseplatebolt = Constructor("baseplatebolt")

    motor = Constructor("motor")
    dynamixel = Constructor("dynamixel")

    differentialdrive = Constructor("differentialdrive")

    mainpart = Part("mainpart")
    endpart1 = Part("endpart1")
    endpart2 = Part("endpart2")
    endpart3 = Part("endpart3")

    g1 = Config(["j1", "j2"], "j3")
    g2 = Config(["j1", "j3"], "j2")
    g3 = Config(["j2", "j3"], "j1")
    h1 = Config([], "j1")
    h2 = Config([], "j2")
    h3 = Config(["j2"], "j1")

    taxonomy = Subtypes({
        steel410.name: {steel.name},
        steel440.name: {steel.name}
    })

    mychemicalrepo = {
        mainpart:
            Type.intersect([
                Arrow(
                    Constructor("j1_j2_j3"),
                    Arrow(
                        Type.intersect([steel, xl430hornmount]),
                        Arrow(
                            Type.intersect([steel410, xl430hornmount]),
                            Type.intersect(
                                [steel, differentialdrive,
                                 baseplatebolt])))),    #j3 as last
                Arrow(
                    Constructor("j1_j3_j2"),
                    Arrow(
                        Type.intersect([steel, xl430hornmount]),
                        Arrow(
                            Type.intersect([steel, baseplate]),
                            Type.intersect(
                                [steel, differentialdrive,
                                 xl430horn])))),    #j2 as last
                Arrow(Constructor("j2_j3_j1"),
                      Arrow(
                          Type.intersect([steel410, xl430hornmount]),
                          Arrow(
                              Type.intersect([steel, baseplate]),
                              Type.intersect(
                                  [steel, differentialdrive,
                                   xl430horn]))))    #j1 as last
            ]),
        endpart1:
            Type.intersect([
                Arrow(
                    Constructor("j2_j1"),
                    Arrow(Type.intersect([steel410, xl430hornmount]),
                          Type.intersect([steel410, xl430hornmount
                                         ]))),    #provides its j1
                Arrow(Constructor("j2"),
                      Type.intersect([steel410,
                                      baseplate])),    #provides its j2
            ]),    #only has provides joints
        endpart2:
            Type.intersect([
                Arrow(Constructor("j1"),
                      Type.intersect([steel410, xl430hornmount]))
            ]),    #only has provides joints
        g1:
            Constructor("j1_j2_j3"),
        g2:
            Constructor("j1_j3_j2"),
        g3:
            Constructor("j2_j3_j1"),
        h1:
            Constructor("j1"),
        h2:
            Constructor("j2"),
        h3:
            Constructor("j2_j1")
    }

    gamma = FiniteCombinatoryLogic(mychemicalrepo, taxonomy, processes=1)
    result = gamma.inhabit(Type.intersect([steel, differentialdrive,
                                           xl430horn]))
    print(result.size())
    for x in range(9, 10):
        json_formatted_str = json.dumps(result.evaluated[x].to_dict(), indent=4)
        print(json_formatted_str)
