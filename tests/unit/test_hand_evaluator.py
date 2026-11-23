from app.core.deck_card.cards import Card, Suit
from app.core.rule_engine.hand_evaluator import MeldKind, best_arrangement, best_partial, classify, is_run
from tests.helpers import cards


def test_card_points_figures_are_ten():
    assert [c.points for c in cards("1o 7o 10o 11o 12o")] == [1, 7, 10, 10, 10]


def test_card_code_roundtrip():
    card = Card(12, Suit.ESPADAS, 1)
    assert Card.from_code(card.code) == card


def test_group_of_three_distinct_suits():
    meld = classify(cards("5o 5c 5e"))
    assert meld is not None and meld.kind is MeldKind.GROUP


def test_group_with_repeated_suit_is_invalid():
    assert classify(cards("5o 5o' 5e")) is None


def test_run_crosses_seven_to_sota():
    assert is_run(cards("6b 7b 10b 11b"))


def test_run_needs_same_suit():
    assert classify(cards("3o 4o 5c")) is None


def test_run_with_gap_is_invalid():
    assert classify(cards("3o 4o 6o")) is None


def test_two_cards_are_not_a_meld():
    assert classify(cards("3o 3c")) is None


def test_best_arrangement_minimises_leftover_points():
    hand = cards("1o 2o 3o 4o 12o 12c 12e")
    result = best_arrangement(hand, (3, 3))
    # Mejor: 2-3-4 de oros + reyes; sobra el As (1 pt) y no un rey.
    assert result is not None
    assert result.leftover_points == 1


def test_best_partial_without_melds_counts_everything():
    hand = cards("1o 3c 5e 7b 12o")
    assert best_partial(hand).leftover_points == 1 + 3 + 5 + 7 + 10
