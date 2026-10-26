import pytest
import time
from queue_manager import DepartmentQueue, QueueManager

def test_emergency_served_before_normal():
    """Emergency patient arriving after 3 normal patients is served BEFORE them."""
    dq = DepartmentQueue(dept_id=1, max_consecutive_emergency=5, avg_consultation_time=10)

    # 3 normal patients arrive first
    dq.enqueue_normal(token_id=101)
    dq.enqueue_normal(token_id=102)
    dq.enqueue_normal(token_id=103)

    # 1 emergency arrives later
    dq.enqueue_emergency(token_id=201, severity=2, arrival_timestamp=time.time())

    # Call next should serve the emergency patient first
    called = dq.call_next()
    assert called == 201

    # Remaining calls should be normal in FIFO order
    assert dq.call_next() == 101
    assert dq.call_next() == 102
    assert dq.call_next() == 103
    assert dq.call_next() is None


def test_emergency_severity_and_arrival_priority():
    """
    Two emergencies: severity 1 is served before severity 2.
    Equal severity -> earlier arrival first.
    """
    dq = DepartmentQueue(dept_id=1)

    t0 = 1000.0
    # Add severity 2 first
    dq.enqueue_emergency(token_id=1, severity=2, arrival_timestamp=t0)
    # Add severity 1 later
    dq.enqueue_emergency(token_id=2, severity=1, arrival_timestamp=t0 + 10)
    # Add another severity 1 even later
    dq.enqueue_emergency(token_id=3, severity=1, arrival_timestamp=t0 + 20)
    # Add severity 2 earlier than token 1
    dq.enqueue_emergency(token_id=4, severity=2, arrival_timestamp=t0 - 5)

    # Order expected:
    # Severity 1 items: token 2 (t0+10), then token 3 (t0+20)
    # Severity 2 items: token 4 (t0-5), then token 1 (t0)
    assert dq.call_next() == 2
    assert dq.call_next() == 3
    assert dq.call_next() == 4
    assert dq.call_next() == 1
    assert dq.call_next() is None


def test_normal_patients_served_strictly_fifo():
    """Normal patients are served strictly in arrival order."""
    dq = DepartmentQueue(dept_id=1)

    dq.enqueue_normal(1)
    dq.enqueue_normal(2)
    dq.enqueue_normal(3)
    dq.enqueue_normal(4)

    assert dq.call_next() == 1
    assert dq.call_next() == 2
    assert dq.call_next() == 3
    assert dq.call_next() == 4
    assert dq.call_next() is None


def test_fairness_rule_starvation_prevention():
    """After 5 consecutive emergencies, 1 normal patient is served (if waiting)."""
    dq = DepartmentQueue(dept_id=1, max_consecutive_emergency=5)

    # Add 1 normal patient
    dq.enqueue_normal(token_id=999)

    # Add 7 emergency patients
    for i in range(1, 8):
        dq.enqueue_emergency(token_id=i, severity=1, arrival_timestamp=1000 + i)

    # 1st to 5th emergency patients served consecutively
    for i in range(1, 6):
        assert dq.call_next() == i

    # 6th call: consecutive emergencies reached 5! Fairness rule must serve the normal patient (999)
    assert dq.call_next() == 999

    # Next calls serve remaining emergencies
    assert dq.call_next() == 6
    assert dq.call_next() == 7
    assert dq.call_next() is None


def test_remove_token_and_position_update():
    """Cancelled tokens are removed from the queue and positions update."""
    dq = DepartmentQueue(dept_id=1, avg_consultation_time=10)

    dq.enqueue_normal(10)
    dq.enqueue_normal(20)
    dq.enqueue_normal(30)

    # Initial positions
    pos, wait = dq.get_position_and_wait_time(20)
    assert pos == 2
    assert wait == 10  # 1 patient ahead * 10 mins

    pos3, wait3 = dq.get_position_and_wait_time(30)
    assert pos3 == 3
    assert wait3 == 20

    # Cancel token 20
    removed = dq.remove_token(20)
    assert removed is True

    # Token 20 is no longer waiting
    pos20_after, _ = dq.get_position_and_wait_time(20)
    assert pos20_after is None

    # Token 30 position should now be 2
    pos3_after, wait3_after = dq.get_position_and_wait_time(30)
    assert pos3_after == 2
    assert wait3_after == 10

    # Ensure emergency removal also works
    dq.enqueue_emergency(50, severity=1, arrival_timestamp=100)
    assert dq.remove_token(50) is True
    assert dq.get_position_and_wait_time(50) == (None, None)
