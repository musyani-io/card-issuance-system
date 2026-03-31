import time


class SessionManager:
    def __init__(self):
        self.reg_number = None
        self.session_id = None
        self.auth_step = None
        self.auth_status = None
        self.start_time = None
        self.last_activity_time = None

    def teardown(self):
        self.reg_number = None
        self.session_id = None
        self.auth_step = None
        self.auth_status = None
        self.start_time = None
        self.last_activity_time = None

    def update_activity(self):
        if self.start_time is None:
            self.start_time = time.time()
            self.last_activity_time = time.time()

    def is_timed_out(self, timeout_seconds=60):
        if self.last_activity_time is None:
            return False
        elapsed_time = time.time() - self.last_activity_time
        return elapsed_time > timeout_seconds
