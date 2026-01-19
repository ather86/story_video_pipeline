from datetime import datetime

def generate_run_id():
    return datetime.now().strftime("run_%Y%m%d_%H%M%S")
