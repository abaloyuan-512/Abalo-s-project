"""Deterministic five-element generation/control relationships."""

from .enums import BodyUseRelation, Element

_GENERATES = {
    Element.WOOD: Element.FIRE,
    Element.FIRE: Element.EARTH,
    Element.EARTH: Element.METAL,
    Element.METAL: Element.WATER,
    Element.WATER: Element.WOOD,
}

_CONTROLS = {
    Element.WOOD: Element.EARTH,
    Element.EARTH: Element.WATER,
    Element.WATER: Element.FIRE,
    Element.FIRE: Element.METAL,
    Element.METAL: Element.WOOD,
}


def generates(source: Element, target: Element) -> bool:
    return _GENERATES[source] is target


def controls(source: Element, target: Element) -> bool:
    return _CONTROLS[source] is target


def relation_between_body_and_use(body: Element, use: Element) -> BodyUseRelation:
    if body is use:
        return BodyUseRelation.SAME_ELEMENT
    if generates(use, body):
        return BodyUseRelation.USE_GENERATES_BODY
    if controls(body, use):
        return BodyUseRelation.BODY_CONTROLS_USE
    if generates(body, use):
        return BodyUseRelation.BODY_GENERATES_USE
    if controls(use, body):
        return BodyUseRelation.USE_CONTROLS_BODY
    raise AssertionError(f"Unreachable element relationship: body={body}, use={use}")
