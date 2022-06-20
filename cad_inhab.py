from glob import glob1
from typing import Iterable
from uuid import uuid4
from cls_python import *

a = Constructor("a")


class Listify:

    def __call__(self, x):
        return Listify([*self.data, x])

    def __str__(self):
        return deep_str(self.data)

    def __init__(self, data):
        self.data = data


class Part(object):

    def __call__(self, x):
        return Listify([self.payload, x])

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
        print(payload)


def flatten(lis):
    for idx, item in enumerate(lis):
        if isinstance(item, str):
            jnts = [s + ":" for s in item.split("_")]
            for i in range(len(jnts) - 1):
                jnts[i] = jnts[i] + deep_str(lis[i + idx + 1])
        if isinstance(item, Iterable) and not isinstance(item, str):
            #recurse here
            pass
    return deep_str(jnts)


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

    mainpart = Part("mainpart:")
    endpart1 = Part("endpart1:")
    endpart2 = Part("endpart2:")
    endpart3 = Part("endpart3:")

    g1 = Constructor("j1_j2_j3")
    g2 = Constructor("j1_j3_j2")
    g3 = Constructor("j2_j3_j1")
    h1 = Constructor("j1")
    h2 = Constructor("j2")
    h3 = Constructor("j1_j2")

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
                             baseplatebolt])))),  #j3 as last
            Arrow(
                Constructor("j1_j3_j2"),
                Arrow(
                    Type.intersect([steel, xl430hornmount]),
                    Arrow(
                        Type.intersect([steel, baseplate]),
                        Type.intersect([steel, differentialdrive,
                                        xl430horn])))),  #j2 as last
            Arrow(Constructor("j2_j3_j1"),
                  Arrow(
                      Type.intersect([steel410, xl430hornmount]),
                      Arrow(
                          Type.intersect([steel, baseplate]),
                          Type.intersect([steel, differentialdrive,
                                          xl430horn]))))  #j1 as last
        ]),
        endpart1:
        Type.intersect([
            Arrow(
                Constructor("j1_j2"),
                Arrow(Type.intersect([steel410, xl430hornmount]),
                      Type.intersect([steel410,
                                      xl430hornmount]))),  #provides its j1
            Arrow(Constructor("j2"),
                  Type.intersect([steel410, baseplate])),  #provides its j2
        ]),  #only has provides joints
        endpart2:
        Type.intersect([
            Arrow(Constructor("j1"), Type.intersect([steel410,
                                                     xl430hornmount]))
        ]),  #only has provides joints
        "uid1_uid2_uid3":
        g1,
        "uid1_uid3_uid2":
        g2,
        "uid2_uid3_uid1":
        g3,
        "h1":
        h1,
        "h2":
        h2,
        "uid2_uid1":
        h3
    }
    #print(deep_str(mychemicalrepo))
    gamma = FiniteCombinatoryLogic(mychemicalrepo, taxonomy, processes=1)
    result = gamma.inhabit(
        Type.intersect([steel, differentialdrive, xl430horn]))

    print(deep_str(result.grouped_rules))
    print(result.size())
    for x in range(0, 10):
        #print(deep_str(result.raw[x]))
        #print(deep_str(result.evaluated[x]))
        print(flatten(result.evaluated[x].data) + "\n\n\n")
        #This is just transformable to JSON

        # Bäume (deep_str weil print auf den listen elementen .repr statt .str aufruft)
