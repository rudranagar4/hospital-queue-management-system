import heapq
from collections import deque
from datetime import datetime, timezone
from config import Config

class DepartmentQueue:
    """
    Manages the two queues for a single department:
    - normal_deque: collections.deque (FIFO)
    - emergency_heap: min-heap using heapq with entries (severity, arrival_timestamp, token_id)
    """
    def __init__(self, dept_id, max_consecutive_emergency=None, avg_consultation_time=None):
        self.dept_id = dept_id
        self.normal_deque = deque()
        self.emergency_heap = []
        self.consecutive_emergencies = 0
        self.current_token_id = None
        self.max_consecutive_emergency = (
            max_consecutive_emergency if max_consecutive_emergency is not None
            else Config.MAX_CONSECUTIVE_EMERGENCY
        )
        self.avg_consultation_time = (
            avg_consultation_time if avg_consultation_time is not None
            else Config.AVG_CONSULTATION_TIME_MINS
        )

    def enqueue_normal(self, token_id):
        """Add normal token to the back of the FIFO deque."""
        if token_id not in self.normal_deque:
            self.normal_deque.append(token_id)
            return True
        return False

    def enqueue_emergency(self, token_id, severity, arrival_timestamp=None):
        """
        Add emergency token to min-heap.
        Each entry: (severity, arrival_timestamp, token_id)
        Lower severity number (1=Critical, 2=Serious, 3=Urgent) = higher priority.
        If severities match, earlier arrival_timestamp wins.
        """
        # Ensure arrival_timestamp is a comparable float
        if arrival_timestamp is None:
            arrival_timestamp = datetime.now(timezone.utc).timestamp()
        elif isinstance(arrival_timestamp, datetime):
            arrival_timestamp = arrival_timestamp.timestamp()
            
        # Avoid duplicate tokens in heap
        for item in self.emergency_heap:
            if item[2] == token_id:
                return False

        heapq.heappush(self.emergency_heap, (int(severity), float(arrival_timestamp), int(token_id)))
        return True

    def call_next(self):
        """
        Call next algorithm with starvation prevention fairness rule:
        - If consecutive_emergencies >= MAX_CONSECUTIVE_EMERGENCY and normal_deque has waiting patients:
            serve 1 normal patient, reset consecutive_emergencies = 0
        - Else if emergency_heap is not empty:
            serve emergency patient, consecutive_emergencies += 1
        - Else if normal_deque is not empty:
            serve normal patient, reset consecutive_emergencies = 0
        - Else:
            return None (no patients waiting)
        """
        # Fairness rule check:
        if self.consecutive_emergencies >= self.max_consecutive_emergency and len(self.normal_deque) > 0:
            token_id = self.normal_deque.popleft()
            self.consecutive_emergencies = 0
            self.current_token_id = token_id
            return token_id

        # Serve emergency if available
        if self.emergency_heap:
            _, _, token_id = heapq.heappop(self.emergency_heap)
            self.consecutive_emergencies += 1
            self.current_token_id = token_id
            return token_id

        # Otherwise serve normal FIFO
        if self.normal_deque:
            token_id = self.normal_deque.popleft()
            self.consecutive_emergencies = 0
            self.current_token_id = token_id
            return token_id

        return None

    def remove_token(self, token_id):
        """Remove a token (e.g. cancelled) from either queue."""
        token_id = int(token_id)
        # Check normal deque
        if token_id in self.normal_deque:
            self.normal_deque.remove(token_id)
            return True

        # Check emergency heap
        for i, item in enumerate(self.emergency_heap):
            if item[2] == token_id:
                self.emergency_heap.pop(i)
                heapq.heapify(self.emergency_heap)
                return True

        return False

    def get_emergency_sorted(self):
        """Return a sorted copy of emergency tokens (highest priority first)."""
        heap_copy = list(self.emergency_heap)
        sorted_items = []
        while heap_copy:
            sorted_items.append(heapq.heappop(heap_copy))
        return sorted_items

    def get_position_and_wait_time(self, token_id):
        """
        Calculates (position_in_queue, estimated_wait_minutes).
        position_in_queue is 1-indexed (1 means next to be called).
        Returns (None, None) if not currently waiting.
        """
        token_id = int(token_id)

        # 1. Check if it's an emergency token
        emergency_item = None
        for item in self.emergency_heap:
            if item[2] == token_id:
                emergency_item = item
                break

        if emergency_item is not None:
            # Count emergency patients with strictly higher priority (or same priority earlier timestamp)
            e_ahead = 0
            for item in self.emergency_heap:
                if (item[0], item[1], item[2]) < (emergency_item[0], emergency_item[1], emergency_item[2]):
                    e_ahead += 1

            # Check if fairness rule injects normal patients ahead of this emergency token
            normal_injected = 0
            if len(self.normal_deque) > 0 and self.max_consecutive_emergency > 0:
                potential_fairness = (self.consecutive_emergencies + e_ahead) // self.max_consecutive_emergency
                normal_injected = min(potential_fairness, len(self.normal_deque))

            patients_ahead = e_ahead + normal_injected
            position = patients_ahead + 1
            estimated_wait = patients_ahead * self.avg_consultation_time
            return position, estimated_wait

        # 2. Check if it's a normal token
        if token_id in self.normal_deque:
            normal_index = list(self.normal_deque).index(token_id)
            # All remaining emergency patients ahead plus preceding normal patients
            # (emergencies have priority, subject to interleaving)
            total_emergencies = len(self.emergency_heap)
            patients_ahead = normal_index + total_emergencies
            position = patients_ahead + 1
            estimated_wait = patients_ahead * self.avg_consultation_time
            return position, estimated_wait

        return None, None

    def get_summary(self):
        return {
            'dept_id': self.dept_id,
            'emergency_count': len(self.emergency_heap),
            'normal_count': len(self.normal_deque),
            'total_waiting': len(self.emergency_heap) + len(self.normal_deque),
            'current_token_id': self.current_token_id,
            'consecutive_emergencies': self.consecutive_emergencies
        }


class QueueManager:
    """
    Singleton / Application-wide Queue Manager holding DepartmentQueues.
    """
    def __init__(self, max_consecutive_emergency=None, avg_consultation_time=None):
        self.queues = {}  # dept_id -> DepartmentQueue
        self.max_consecutive_emergency = (
            max_consecutive_emergency if max_consecutive_emergency is not None
            else Config.MAX_CONSECUTIVE_EMERGENCY
        )
        self.avg_consultation_time = (
            avg_consultation_time if avg_consultation_time is not None
            else Config.AVG_CONSULTATION_TIME_MINS
        )

    def get_or_create_queue(self, dept_id) -> DepartmentQueue:
        dept_id = int(dept_id)
        if dept_id not in self.queues:
            self.queues[dept_id] = DepartmentQueue(
                dept_id,
                max_consecutive_emergency=self.max_consecutive_emergency,
                avg_consultation_time=self.avg_consultation_time
            )
        return self.queues[dept_id]

    def enqueue(self, token):
        """Helper to enqueue a Token model instance."""
        q = self.get_or_create_queue(token.department_id)
        if token.case_type == 'emergency':
            arr_ts = token.created_at.timestamp() if token.created_at else None
            return q.enqueue_emergency(token.id, token.severity or 2, arr_ts)
        else:
            return q.enqueue_normal(token.id)

    def call_next(self, dept_id):
        q = self.get_or_create_queue(dept_id)
        return q.call_next()

    def remove_token(self, dept_id, token_id):
        q = self.get_or_create_queue(dept_id)
        return q.remove_token(token_id)

    def get_position_and_wait_time(self, dept_id, token_id):
        q = self.get_or_create_queue(dept_id)
        return q.get_position_and_wait_time(token_id)

    def rebuild_from_db(self, app=None):
        """
        Database is source of truth.
        Rebuilds the deque and heap from tokens with status 'waiting'.
        Also restores current_token_id for any 'called' or 'in_consultation' token.
        """
        from models import Token

        def _rebuild():
            self.queues.clear()
            
            # 1. Fetch active tokens currently being served ('called' or 'in_consultation')
            active_tokens = Token.query.filter(
                Token.status.in_(['called', 'in_consultation'])
            ).order_by(Token.called_at.desc()).all()

            for t in active_tokens:
                q = self.get_or_create_queue(t.department_id)
                if q.current_token_id is None:
                    q.current_token_id = t.id

            # 2. Fetch all waiting tokens in ascending order of creation
            waiting_tokens = Token.query.filter_by(status='waiting').order_by(Token.created_at.asc()).all()
            for t in waiting_tokens:
                self.enqueue(t)

        if app:
            with app.app_context():
                _rebuild()
        else:
            _rebuild()


# Global queue manager instance
queue_manager = QueueManager()
