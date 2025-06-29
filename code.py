# Create updated code.py with swapped paddle controls

import board
import displayio
import terminalio
import time
import random
import digitalio
import audioio
from audiocore import RawSample
import math
import keypad
from adafruit_display_text import label
from vectorio import Rectangle, Circle

# --- Constants ---
SCREEN_WIDTH = 160
SCREEN_HEIGHT = 128
PADDLE_WIDTH = 30
PADDLE_HEIGHT = 5
BALL_RADIUS = 3
BRICK_ROWS = 3
BRICK_COLUMNS = 8
BRICK_WIDTH = SCREEN_WIDTH // BRICK_COLUMNS
BRICK_HEIGHT = 10
BALL_SPEED_INCREMENT = 0.3
PADDLE_SPEED = 3

# --- Setup Display ---
display = board.DISPLAY
main_group = displayio.Group()
display.root_group = main_group

# --- Status Label ---
status_label = label.Label(terminalio.FONT, text="Press A to Start", x=30, y=64)
main_group.append(status_label)

# --- Setup Sound ---
speaker = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker.switch_to_output(True)
try:
    audio = audioio.AudioOut(board.SPEAKER)
except AttributeError:
    audio = audioio.AudioOut(board.A0)

def play_beep():
    tone = bytes([128 + int(127 * math.sin(2 * math.pi * x / 20)) for x in range(100)])
    beep = RawSample(tone, sample_rate=8000)
    audio.play(beep)

# --- Button Setup via Shift Register ---
keys = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    latch=board.BUTTON_LATCH,
    data=board.BUTTON_OUT,
    key_count=4,
    value_when_pressed=False
)
# Button index mapping: 0=A, 1=B, 2=SELECT (left), 3=START (right)

# --- Game Objects ---
game_layer = displayio.Group()
main_group.append(game_layer)

paddle = Rectangle(pixel_shader=displayio.Palette(1),
                   width=PADDLE_WIDTH, height=PADDLE_HEIGHT,
                   x=(SCREEN_WIDTH - PADDLE_WIDTH)//2, y=SCREEN_HEIGHT - 10)
paddle.pixel_shader[0] = 0xFFFFFF
game_layer.append(paddle)

ball = Circle(pixel_shader=displayio.Palette(1),
              radius=BALL_RADIUS,
              x=SCREEN_WIDTH//2, y=SCREEN_HEIGHT//2)
ball.pixel_shader[0] = 0x00FFFF
game_layer.append(ball)

bricks = []

def make_bricks():
    colors = [0xFF0000, 0x00FF00, 0x0000FF]
    for row in range(BRICK_ROWS):
        for col in range(BRICK_COLUMNS):
            brick = Rectangle(pixel_shader=displayio.Palette(1),
                              width=BRICK_WIDTH - 2, height=BRICK_HEIGHT - 2,
                              x=col * BRICK_WIDTH + 1, y=row * BRICK_HEIGHT + 1)
            brick.pixel_shader[0] = colors[row % len(colors)]
            bricks.append(brick)
            game_layer.append(brick)

# --- Game Functions ---
def reset_ball():
    ball.x = SCREEN_WIDTH // 2
    ball.y = SCREEN_HEIGHT // 2
    return random.choice([-1, 1]), -1

def show_message(text):
    status_label.text = text
    status_label.hidden = False
    display.refresh()

def hide_message():
    status_label.hidden = True

def breakout_game():
    dx, dy = reset_ball()
    score = 0
    level = 1
    make_bricks()
    hide_message()

    pressed_keys = set()

    while True:
        # Process events
        event = keys.events.get()
        while event:
            if event.pressed:
                pressed_keys.add(event.key_number)
            elif event.released:
                if event.key_number == 1:
                    show_message("Paused. B to resume.")
                    while True:
                        e = keys.events.get()
                        if e and e.released and e.key_number == 1:
                            hide_message()
                            break
                        time.sleep(0.1)
                pressed_keys.discard(event.key_number)
            event = keys.events.get()

        # Move paddle: START(3)=right, SELECT(2)=left
        if 3 in pressed_keys:
            paddle.x = min(SCREEN_WIDTH - PADDLE_WIDTH, paddle.x + PADDLE_SPEED)
        if 2 in pressed_keys:
            paddle.x = max(0, paddle.x - PADDLE_SPEED)

        # Update ball
        ball.x += dx
        ball.y += dy

        # Collision: walls
        if ball.x <= 0 or ball.x >= SCREEN_WIDTH - BALL_RADIUS:
            dx = -dx
            play_beep()
        if ball.y <= 0:
            dy = -dy
            play_beep()

        # Collision: paddle
        if (paddle.y - BALL_RADIUS <= ball.y <= paddle.y) and (paddle.x <= ball.x <= paddle.x + PADDLE_WIDTH):
            dy = -dy
            play_beep()

        # Brick collisions
        for brick in bricks[:]:
            if (brick.x < ball.x < brick.x + BRICK_WIDTH) and (brick.y < ball.y < brick.y + BRICK_HEIGHT):
                bricks.remove(brick)
                game_layer.remove(brick)
                dy = -dy
                score += 10
                play_beep()
                break

        # Missed ball
        if ball.y > SCREEN_HEIGHT:
            show_message("Game Over. A to Restart.")
            while True:
                e = keys.events.get()
                if e and e.released and e.key_number == 0:
                    for b in bricks:
                        game_layer.remove(b)
                    bricks.clear()
                    return True
                time.sleep(0.1)

        # Level cleared
        if not bricks:
            level += 1
            dx *= 1 + BALL_SPEED_INCREMENT
            dy *= 1 + BALL_SPEED_INCREMENT
            show_message(f"Score: {score}. A to next")
            while True:
                e = keys.events.get()
                if e and e.released and e.key_number == 0:
                    for b in bricks:
                        game_layer.remove(b)
                    bricks.clear()
                    make_bricks()
                    hide_message()
                    break
                time.sleep(0.1)

        display.refresh()
        time.sleep(0.02)

# --- Main Loop ---
while True:
    show_message("Press A to Start")
    while True:
        evt = keys.events.get()
        if evt and evt.released and evt.key_number == 0:
            break
        time.sleep(0.1)
    hide_message()
    breakout_game()