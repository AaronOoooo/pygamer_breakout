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
import neopixel
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
INITIAL_LIVES = 3

# --- Setup Display ---
display = board.DISPLAY
main_group = displayio.Group()
display.root_group = main_group

# --- NeoPixel Lives Indicator ---
NUM_PIXELS = 5  # onboard NeoPixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, NUM_PIXELS, brightness=0.2, auto_write=True)
LIFE_INDICES = [1, 2, 3]  # middle three LEDs

def update_lives_lights(lives, bright=False):
    pixels.brightness = 1.0 if bright else 0.2
    for idx_num, idx in enumerate(LIFE_INDICES, start=1):
        pixels[idx] = (255, 0, 0) if idx_num <= lives else (0, 0, 0)

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

# --- Button Setup ---
keys = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    latch=board.BUTTON_LATCH,
    data=board.BUTTON_OUT,
    key_count=4,
    value_when_pressed=False
)
# mapping: 0=A, 1=B, 2=SELECT (left), 3=START (right)

# --- Game Objects ---
game_layer = displayio.Group()
main_group.append(game_layer)

paddle = Rectangle(pixel_shader=displayio.Palette(1),
                   width=PADDLE_WIDTH, height=PADDLE_HEIGHT,
                   x=(SCREEN_WIDTH - PADDLE_WIDTH)//2,
                   y=SCREEN_HEIGHT - 10)
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
                              x=col * BRICK_WIDTH + 1,
                              y=row * BRICK_HEIGHT + 1)
            brick.pixel_shader[0] = colors[row % len(colors)]
            bricks.append(brick)
            game_layer.append(brick)

def reset_ball():
    ball.x = SCREEN_WIDTH // 2
    ball.y = SCREEN_HEIGHT // 2
    return random.choice([-1, 1]), -1

def show_message(text, duration=None):
    status_label.text = text
    status_label.hidden = False
    display.refresh()
    if duration:
        time.sleep(duration)
        status_label.hidden = True

def hide_message():
    status_label.hidden = True

def breakout_game():
    lives = INITIAL_LIVES
    update_lives_lights(lives, bright=False)
    make_bricks()
    hide_message()
    dx, dy = reset_ball()
    score = 0
    pressed = set()

    while True:
        # Handle button events
        event = keys.events.get()
        while event:
            if event.pressed:
                pressed.add(event.key_number)
            elif event.released:
                if event.key_number == 1:  # B = pause
                    update_lives_lights(lives, bright=True)
                    show_message("Paused. B to resume.")
                    while True:
                        e = keys.events.get()
                        if e and e.released and e.key_number == 1:
                            hide_message()
                            update_lives_lights(lives, bright=False)
                            break
                        time.sleep(0.1)
                pressed.discard(event.key_number)
            event = keys.events.get()

        # Paddle movement: START(3)=right, SELECT(2)=left
        if 3 in pressed:
            paddle.x = min(SCREEN_WIDTH - PADDLE_WIDTH, paddle.x + PADDLE_SPEED)
        if 2 in pressed:
            paddle.x = max(0, paddle.x - PADDLE_SPEED)

        # Move ball
        ball.x += dx
        ball.y += dy

        # Wall collisions
        if ball.x <= 0 or ball.x >= SCREEN_WIDTH - BALL_RADIUS:
            dx = -dx; play_beep()
        if ball.y <= 0:
            dy = -dy; play_beep()

        # Paddle collision
        if (paddle.y - BALL_RADIUS <= ball.y <= paddle.y and
            paddle.x <= ball.x <= paddle.x + PADDLE_WIDTH):
            dy = -dy; play_beep()

        # Brick collisions
        for brick in bricks[:]:
            if (brick.x < ball.x < brick.x + BRICK_WIDTH and
                brick.y < ball.y < brick.y + BRICK_HEIGHT):
                bricks.remove(brick)
                game_layer.remove(brick)
                dy = -dy; score += 10; play_beep()
                break

        # Ball missed
        if ball.y > SCREEN_HEIGHT:
            lives -= 1
            update_lives_lights(lives, bright=False)
            if lives > 0:
                show_message(f"Life lost! {lives} left", 1)
                dx, dy = reset_ball()
                continue
            else:
                update_lives_lights(0, bright=False)
                show_message(f"Game Over! Score: {score}. A to restart")
                while True:
                    e = keys.events.get()
                    if e and e.released and e.key_number == 0:
                        for b in bricks:
                            game_layer.remove(b)
                        bricks.clear()
                        return
                    time.sleep(0.1)

        # Level cleared
        if not bricks:
            update_lives_lights(lives, bright=True)
            show_message(f"Score: {score}! Level up", 1)
            make_bricks()
            hide_message()
            update_lives_lights(lives, bright=False)
            dx, dy = reset_ball()
            continue

        display.refresh()
        time.sleep(0.02)

# --- Main Loop ---
while True:
    show_message("Press A to Start")
    update_lives_lights(INITIAL_LIVES, bright=False)
    while True:
        evt = keys.events.get()
        if evt and evt.released and evt.key_number == 0:
            break
        time.sleep(0.1)
    hide_message()
    breakout_game()
