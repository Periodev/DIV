"""
Unit tests for merge logic (normal and inherit merge)

Test cases based on specification:
Focus | Sub | merge | drop | Inherit
B1    | 0   | F+B1  | 0    | x
B1    | B1  | F+B1  | 0    | x
B1    | B2  | F+B1  | B2   | x
0     | B2  | 0     | 0    | F+B2

Note: "Inherit only when focus not carry"
These tests assume focus is on empty ground (not on NO_CARRY tile)
"""

import sys
from timeline_system import (
    BranchState, Entity, EntityType, TerrainType, Timeline, Physics
)


def create_test_level(focus_holding_uid=None, sub_holding_uid=None,
                      focus_pos=(2, 2), sub_pos=(2, 3)):
    """Create a minimal test level with two branches.

    Args:
        focus_holding_uid: uid of box held by focused player (None if not holding)
        sub_holding_uid: uid of box held by sub player (None if not holding)
        focus_pos: position of focused player
        sub_pos: position of sub player

    Returns:
        (main_branch, sub_branch) tuple
    """
    # Create main (focused) branch
    main = BranchState()
    main.grid_size = 6
    main.terrain = {
        (x, y): TerrainType.FLOOR
        for x in range(6) for y in range(6)
    }

    # Add player (must be at entities[0])
    player = Entity(uid=0, type=EntityType.PLAYER, pos=focus_pos)
    main.entities.append(player)

    # Add box B1 (uid=1) if needed
    if focus_holding_uid == 1:
        box1 = Entity(uid=1, type=EntityType.BOX, pos=focus_pos,
                     holder=0, z=1, collision=0)
        main.entities.append(box1)

    # Add box B2 (uid=2) if needed
    if focus_holding_uid == 2:
        box2 = Entity(uid=2, type=EntityType.BOX, pos=focus_pos,
                     holder=0, z=1, collision=0)
        main.entities.append(box2)

    # Create sub branch
    sub = BranchState()
    sub.grid_size = 6
    sub.terrain = main.terrain.copy()

    # Add player (must be at entities[0])
    player_sub = Entity(uid=0, type=EntityType.PLAYER, pos=sub_pos)
    sub.entities.append(player_sub)

    # Add box B1 (uid=1) to sub if needed
    if sub_holding_uid == 1:
        box1_sub = Entity(uid=1, type=EntityType.BOX, pos=sub_pos,
                         holder=0, z=1, collision=0)
        sub.entities.append(box1_sub)

    # Add box B2 (uid=2) to sub if needed
    if sub_holding_uid == 2:
        box2_sub = Entity(uid=2, type=EntityType.BOX, pos=sub_pos,
                         holder=0, z=1, collision=0)
        sub.entities.append(box2_sub)

    return main, sub


def test_case_1_focus_b1_sub_empty():
    """Test: Focus=B1, Sub=empty → merge: F+B1, drop: none"""
    print("\n[Test 1] Focus=B1, Sub=empty")

    main, sub = create_test_level(focus_holding_uid=1, sub_holding_uid=None)

    # Execute merge
    merged = Timeline.converge(main, sub)
    Timeline.settle_carried(merged)

    # Verify: Focus should be holding B1
    held = merged.get_held_items()
    assert len(held) == 1, f"Expected 1 held item, got {len(held)}"
    assert 1 in held, f"Expected uid=1 held, got {held}"

    # Verify: No boxes on ground
    grounded_boxes = [e for e in merged.entities if e.uid != 0 and e.holder is None]
    assert len(grounded_boxes) == 0, f"Expected 0 grounded boxes, got {len(grounded_boxes)}"

    print("[OK] PASS: Focus holds B1, nothing dropped")


def test_case_2_focus_b1_sub_b1():
    """Test: Focus=B1, Sub=B1 (same box) → merge: F+B1, drop: none"""
    print("\n[Test 2] Focus=B1, Sub=B1 (same box)")

    main, sub = create_test_level(focus_holding_uid=1, sub_holding_uid=1)

    # Execute merge
    merged = Timeline.converge(main, sub)
    Timeline.settle_carried(merged)

    # Verify: Focus should be holding B1
    held = merged.get_held_items()
    assert len(held) == 1, f"Expected 1 held item, got {len(held)}"
    assert 1 in held, f"Expected uid=1 held, got {held}"

    # Verify: Only 1 instance of B1 exists (shadows converged)
    b1_instances = [e for e in merged.entities if e.uid == 1]
    assert len(b1_instances) == 1, f"Expected 1 instance of B1, got {len(b1_instances)}"

    # Verify: No boxes on ground
    grounded_boxes = [e for e in merged.entities if e.uid != 0 and e.holder is None]
    assert len(grounded_boxes) == 0, f"Expected 0 grounded boxes, got {len(grounded_boxes)}"

    print("[OK] PASS: Focus holds B1 (converged), nothing dropped")


def test_case_3_focus_b1_sub_b2():
    """Test: Focus=B1, Sub=B2 → merge: F+B1, drop: B2"""
    print("\n[Test 3] Focus=B1, Sub=B2 (different boxes)")

    main, sub = create_test_level(focus_holding_uid=1, sub_holding_uid=2,
                                  focus_pos=(2, 2), sub_pos=(2, 3))

    # Execute merge
    merged = Timeline.converge(main, sub)
    Timeline.settle_carried(merged)

    # Verify: Focus should be holding B1
    held = merged.get_held_items()
    assert len(held) == 1, f"Expected 1 held item, got {len(held)}"
    assert 1 in held, f"Expected uid=1 held, got {held}"

    # Verify: B2 is dropped on ground at sub's position
    grounded_boxes = [e for e in merged.entities if e.uid != 0 and e.holder is None]
    assert len(grounded_boxes) == 1, f"Expected 1 grounded box, got {len(grounded_boxes)}"
    assert grounded_boxes[0].uid == 2, f"Expected B2 dropped, got uid={grounded_boxes[0].uid}"
    assert grounded_boxes[0].pos == (2, 3), f"Expected B2 at (2,3), got {grounded_boxes[0].pos}"

    print("[OK] PASS: Focus holds B1, B2 dropped at sub's position")


def test_case_4_focus_empty_sub_b2_normal_merge():
    """Test: Focus=empty, Sub=B2 → normal merge: drop B2"""
    print("\n[Test 4a] Focus=empty, Sub=B2 → Normal merge")

    main, sub = create_test_level(focus_holding_uid=None, sub_holding_uid=2,
                                  focus_pos=(2, 2), sub_pos=(2, 3))

    # Execute normal merge
    merged = Timeline.converge(main, sub)
    Timeline.settle_carried(merged)

    # Verify: Focus should not be holding anything
    held = merged.get_held_items()
    assert len(held) == 0, f"Expected 0 held items, got {len(held)}"

    # Verify: B2 is dropped on ground at sub's position
    grounded_boxes = [e for e in merged.entities if e.uid != 0 and e.holder is None]
    assert len(grounded_boxes) == 1, f"Expected 1 grounded box, got {len(grounded_boxes)}"
    assert grounded_boxes[0].uid == 2, f"Expected B2 dropped, got uid={grounded_boxes[0].uid}"

    print("[OK] PASS: Focus empty, B2 dropped")


def test_case_4_focus_empty_sub_b2_inherit_merge():
    """Test: Focus=empty, Sub=B2 → inherit merge: F+B2"""
    print("\n[Test 4b] Focus=empty, Sub=B2 → Inherit merge")

    main, sub = create_test_level(focus_holding_uid=None, sub_holding_uid=2,
                                  focus_pos=(2, 2), sub_pos=(2, 3))

    # Check capacity
    capacity = Physics.effective_capacity(main)
    assert capacity >= 1, f"Expected capacity >= 1, got {capacity}"

    # Simulate inherit merge logic
    focused_held = set(main.get_held_items())
    other_held = set(sub.get_held_items())
    items_to_inherit = focused_held | other_held

    # Execute merge
    merged = Timeline.converge(main, sub)

    # Mark all items to inherit as held
    for uid in items_to_inherit:
        instances = [e for e in merged.entities if e.uid == uid]
        for e in instances:
            e.holder = 0

    # Settle carried
    Timeline.settle_carried(merged)

    # Verify: Focus should be holding B2
    held = merged.get_held_items()
    assert len(held) == 1, f"Expected 1 held item, got {len(held)}"
    assert 2 in held, f"Expected uid=2 held, got {held}"

    # Verify: B2 is at focus position
    b2_instances = [e for e in merged.entities if e.uid == 2]
    assert len(b2_instances) == 1, f"Expected 1 instance of B2, got {len(b2_instances)}"
    assert b2_instances[0].pos == (2, 2), f"Expected B2 at focus pos (2,2), got {b2_instances[0].pos}"
    assert b2_instances[0].holder == 0, f"Expected B2 held, got holder={b2_instances[0].holder}"

    print("[OK] PASS: Focus inherits B2")


def test_inherit_blocked_when_focus_holding():
    """Test: Inherit merge should fail when focus is already holding something"""
    print("\n[Test 5] Inherit blocked when focus holding")

    main, sub = create_test_level(focus_holding_uid=1, sub_holding_uid=2)

    # Check if inherit would be allowed
    focused_held = set(main.get_held_items())
    other_held = set(sub.get_held_items())
    total_items = len(focused_held | other_held)
    capacity = Physics.effective_capacity(main)

    # Inherit should fail because total_items (2) > capacity (1)
    should_fail = total_items > capacity
    assert should_fail, "Expected inherit merge to fail when focus already holding"

    print("[OK] PASS: Inherit correctly blocked when focus holding")


def run_all_tests():
    """Run all merge logic tests"""
    print("=" * 60)
    print("MERGE LOGIC UNIT TESTS")
    print("=" * 60)

    try:
        test_case_1_focus_b1_sub_empty()
        test_case_2_focus_b1_sub_b1()
        test_case_3_focus_b1_sub_b2()
        test_case_4_focus_empty_sub_b2_normal_merge()
        test_case_4_focus_empty_sub_b2_inherit_merge()
        test_inherit_blocked_when_focus_holding()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED [OK]")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\nX TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\nX ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
