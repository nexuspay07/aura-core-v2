cognitive_log = []

def log_event(stage, message):

    event = {
        "stage": stage,
        "message": message
    }

    cognitive_log.append(event)

    if len(cognitive_log) > 50:
        cognitive_log.pop(0)


def get_stream():
    return cognitive_log