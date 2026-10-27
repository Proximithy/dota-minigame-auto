"""Pure helpers; screen coordinates increase downward."""

def reflect(x, left, right):
    width = right - left
    if width <= 0:
        raise ValueError('Arena estreita demais')
    phase = (x - left) % (2 * width)
    return left + (phase if phase <= width else 2 * width - phase)


def intercept(x, y, vx, vy, paddle_y, left, right):
    if vy <= 20 or paddle_y <= y:
        return max(left, min(right, x))
    seconds = min(3.0, (paddle_y - y) / vy)
    return reflect(x + vx * seconds, left, right)


def direction(target, paddle_x, deadzone):
    delta = target - paddle_x
    return 0 if abs(delta) <= deadzone else (1 if delta > 0 else -1)
