import pytest

from abalo_iching.meihua.enums import BodyUseRelation, Element
from abalo_iching.meihua.relations import relation_between_body_and_use


@pytest.mark.parametrize(
    "body,use,expected",
    [
        (Element.WOOD, Element.WATER, BodyUseRelation.USE_GENERATES_BODY),
        (Element.WOOD, Element.EARTH, BodyUseRelation.BODY_CONTROLS_USE),
        (Element.WOOD, Element.WOOD, BodyUseRelation.SAME_ELEMENT),
        (Element.WOOD, Element.FIRE, BodyUseRelation.BODY_GENERATES_USE),
        (Element.WOOD, Element.METAL, BodyUseRelation.USE_CONTROLS_BODY),
    ],
)
def test_all_five_body_use_relations(body: Element, use: Element, expected: BodyUseRelation) -> None:
    assert relation_between_body_and_use(body, use) is expected
