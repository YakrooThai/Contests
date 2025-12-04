import board
import busio
import displayio
import digitalio
import time
import random
from adafruit_st7789 import ST7789
import neopixel
import adafruit_imageload
from fourwire import FourWire

# --- ตั้งค่าฮาร์ดแวร์ ---
btn_up = digitalio.DigitalInOut(board.GP15)
btn_up.direction = digitalio.Direction.INPUT
btn_up.pull = digitalio.Pull.DOWN

btn_down = digitalio.DigitalInOut(board.GP27)
btn_down.direction = digitalio.Direction.INPUT
btn_down.pull = digitalio.Pull.DOWN

btn_fire = digitalio.DigitalInOut(board.GP22)
btn_fire.direction = digitalio.Direction.INPUT
btn_fire.pull = digitalio.Pull.DOWN

btn_auto = digitalio.DigitalInOut(board.GP28)
btn_auto.direction = digitalio.Direction.INPUT
btn_auto.pull = digitalio.Pull.DOWN

pixels = neopixel.NeoPixel(board.GP0, 3)
pixels.brightness = 0.01
pixels.fill((0, 0, 0))
pixels.show()

#-----------------
# ST7789V2 1.9" display pin setup (170x320)
tft_dc = board.GP16
tft_cs = board.GP17  
tft_res = board.GP21
spi_sda = board.GP19
spi_scl = board.GP18

# Release previous displays
displayio.release_displays()

# SPI bus setup
spi = busio.SPI(spi_scl, MOSI=spi_sda)

# Display bus and ST7789 setup สำหรับจอ 170x320
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_res)
display = ST7789(
    display_bus, 
    rotation=0,
    width=170,
    height=320,
    rowstart=0,      
    colstart=35        
)

# --- กำหนดค่าเกม ---
SCREEN_WIDTH = 170
SCREEN_HEIGHT = 320
PLAYER_SIZE = 24
ENEMY_SIZE = 24
BULLET_SIZE = 8
FPS = 30
GAME_SPEED = 1.0 / FPS

# --- โหลดภาพแบบโปร่งใส (แก้ไขเฉพาะส่วนนี้) ---
try:
    # โหลดภาพปกติ
    bg_bmp, bg_pal = adafruit_imageload.load("space_bg.bmp")
    #bg_bmp, bg_pal = adafruit_imageload.load("pichai2.bmp")
    player_bmp, player_pal = adafruit_imageload.load("player_ship3.bmp")
    enemy_bmp, enemy_pal = adafruit_imageload.load("enemy_ship.bmp")
    bullet_bmp, bullet_pal = adafruit_imageload.load("bullet.bmp")
    
    # ทำให้พื้นหลังสีดำโปร่งใส (สำคัญ!)
    player_pal.make_transparent(0)
    enemy_pal.make_transparent(0)
    bullet_pal.make_transparent(0)
    
    print("✅ โหลดภาพสำเร็จและตั้งค่าโปร่งใสแล้ว")
    
except OSError as e:
    print(f"⚠️ ไม่พบไฟล์ภาพ: {e} — ใช้สี่เหลี่ยมแทน")
    # สร้างภาพทดแทนแบบง่าย (สี่เหลี่ยมธรรมดา)
    bg_bmp = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 1)
    bg_pal = displayio.Palette(1)
    bg_pal[0] = 0x000000
    
    player_bmp = displayio.Bitmap(PLAYER_SIZE, PLAYER_SIZE, 1)
    player_pal = displayio.Palette(1)
    player_pal[0] = 0x00FF00
    
    enemy_bmp = displayio.Bitmap(ENEMY_SIZE, ENEMY_SIZE, 1)
    enemy_pal = displayio.Palette(1)
    enemy_pal[0] = 0xFF0000
    
    bullet_bmp = displayio.Bitmap(BULLET_SIZE, BULLET_SIZE, 1)
    bullet_pal = displayio.Palette(1)
    bullet_pal[0] = 0xFFFFFF

# โหลดภาพระเบิด (ถ้ามี)
try:
    explosion_0_bmp, explosion_0_pal = adafruit_imageload.load("explosion_0.bmp")
    explosion_1_bmp, explosion_1_pal = adafruit_imageload.load("explosion_1.bmp")
    explosion_2_bmp, explosion_2_pal = adafruit_imageload.load("explosion_2.bmp")
    
    # ทำให้ระเบิดโปร่งใสด้วย
    explosion_0_pal.make_transparent(0)
    explosion_1_pal.make_transparent(0)
    explosion_2_pal.make_transparent(0)
    
    explosion_frames = [
        (explosion_0_bmp, explosion_0_pal),
        (explosion_1_bmp, explosion_1_pal),
        (explosion_2_bmp, explosion_2_pal)
    ]
    print("✅ โหลดภาพระเบิดสำเร็จ")
    
except OSError:
    print("⚠️ ใช้ระเบิดสีแทน")
    explosion_frames = []
    for i in range(3):
        exp_bmp = displayio.Bitmap(ENEMY_SIZE, ENEMY_SIZE, 1)
        exp_pal = displayio.Palette(1)
        exp_pal[0] = [0xFFFF00, 0xFF8800, 0xFF0000][i]
        explosion_frames.append((exp_bmp, exp_pal))

# --- ส่วนที่เหลือของโค้ดเหมือนเดิมทั้งหมด ---
# --- สร้างกลุ่มแสดงผล ---
main_group = displayio.Group()
display.root_group = main_group

# --- สร้างพื้นหลัง ---
bg_tile = displayio.TileGrid(bg_bmp, pixel_shader=bg_pal)
main_group.append(bg_tile)

# --- คลาสระเบิด ---
class Explosion:
    def __init__(self, x, y):
        self.sprite = displayio.TileGrid(explosion_frames[0][0], pixel_shader=explosion_frames[0][1])
        self.sprite.x = x
        self.sprite.y = y
        self.current_frame = 0
        self.last_frame_time = time.monotonic()
        self.frame_delay = 0.1
        self.active = True
        
    def update(self):
        if not self.active:
            return False
            
        current_time = time.monotonic()
        if current_time - self.last_frame_time > self.frame_delay:
            self.current_frame += 1
            self.last_frame_time = current_time
            
            if self.current_frame < len(explosion_frames):
                bmp, pal = explosion_frames[self.current_frame]
                self.sprite.bitmap = bmp
                self.sprite.pixel_shader = pal
            else:
                self.active = False
                return False
        return True

# ลิสต์เก็บระเบิด
explosions = []

# --- สร้างยานผู้เล่น ---
class Player:
    def __init__(self):
        self.sprite = displayio.TileGrid(player_bmp, pixel_shader=player_pal, 
                                       x=SCREEN_WIDTH//2 - PLAYER_SIZE//2, 
                                       y=SCREEN_HEIGHT - PLAYER_SIZE - 10)
        self.speed = 2
        self.bullets = []
        self.last_shot = 0
        self.auto_mode = True
        self.last_auto_move = 0

    def update(self):
        if self.auto_mode:
            self.auto_update()
        else:
            self.manual_update()

        for b in self.bullets[:]:
            b.update()
            if b.sprite.y < -BULLET_SIZE:
                main_group.remove(b.sprite)
                self.bullets.remove(b)

    def manual_update(self):
        if btn_up.value and self.sprite.y > 0:
            self.sprite.y -= self.speed
        if btn_down.value and self.sprite.y < SCREEN_HEIGHT - PLAYER_SIZE:
            self.sprite.y += self.speed

        if btn_fire.value and time.monotonic() - self.last_shot > 0.3:
            self.shoot()
            self.last_shot = time.monotonic()

    def auto_update(self):
        current_time = time.monotonic()
        
        if current_time - self.last_shot > 0.5:
            self.shoot()
            self.last_shot = current_time
        
        if current_time - self.last_auto_move > 0.8:
            new_y = self.sprite.y + random.choice([-self.speed*2, 0, self.speed*2])
            if 0 <= new_y <= SCREEN_HEIGHT - PLAYER_SIZE:
                self.sprite.y = new_y
            self.last_auto_move = current_time

    def shoot(self):
        bullet_x = self.sprite.x + PLAYER_SIZE//2 - BULLET_SIZE//2
        bullet_y = self.sprite.y
        bullet = Bullet(bullet_x, bullet_y)
        self.bullets.append(bullet)
        main_group.append(bullet.sprite)

    def toggle_auto_mode(self):
        self.auto_mode = not self.auto_mode

class Bullet:
    def __init__(self, x, y):
        self.sprite = displayio.TileGrid(bullet_bmp, pixel_shader=bullet_pal, x=x, y=y)
        self.speed = 5

    def update(self):
        self.sprite.y -= self.speed

# --- สร้างศัตรู ---
class Enemy:
    def __init__(self):
        self.sprite = displayio.TileGrid(enemy_bmp, pixel_shader=enemy_pal, 
                                       x=random.randint(0, SCREEN_WIDTH - ENEMY_SIZE), 
                                       y=-ENEMY_SIZE)
        self.speed = random.randint(1, 3)
        self.active = True
        self.respawn_timer = 0

    def update(self):
        if self.active:
            self.sprite.y += self.speed
            if self.sprite.y > SCREEN_HEIGHT:
                self.respawn()
        else:
            self.respawn_timer += GAME_SPEED
            if self.respawn_timer >= 0.5:
                self.respawn()
                self.respawn_timer = 0

    def respawn(self):
        time.sleep(0.05)
        self.sprite.x = random.randint(0, SCREEN_WIDTH - ENEMY_SIZE)
        self.sprite.y = -ENEMY_SIZE
        self.speed = random.randint(1, 3)
        self.active = True
        self.sprite.hidden = False

    def explode(self, x, y):
        explosion = Explosion(x, y)
        explosions.append(explosion)
        main_group.append(explosion.sprite)
        return explosion

# --- สร้างตัวละคร ---
player = Player()
main_group.append(player.sprite)

enemies = [Enemy() for _ in range(2)]
for e in enemies:
    main_group.append(e.sprite)

# --- HUD ---
score = 0
lives = 3

from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font

try:
    font = bitmap_font.load_font("Helvetica-Bold-16.bdf")
except:
    import terminalio
    font = terminalio.FONT

score_label = label.Label(font, text=f"SCORE: {score}", color=0xFFFFFF, x=5, y=5)
main_group.append(score_label)

lives_label = label.Label(font, text=f"LIVES: {lives}", color=0xFFFFFF, x=120, y=5)
main_group.append(lives_label)

mode_text = label.Label(font, text="AUTO", color=0x00FF00, x=130, y=15)
main_group.append(mode_text)

# --- ตรวจจับการชน ---
def check_collision():
    global score, lives
    
    for enemy in enemies[:]:
        if not enemy.active:
            continue
            
        for bullet in player.bullets[:]:
            if (bullet.sprite.x < enemy.sprite.x + ENEMY_SIZE and
                bullet.sprite.x + BULLET_SIZE > enemy.sprite.x and
                bullet.sprite.y < enemy.sprite.y + ENEMY_SIZE and
                bullet.sprite.y + BULLET_SIZE > enemy.sprite.y):
                
                explosion = enemy.explode(enemy.sprite.x, enemy.sprite.y)
                score += 10
                score_label.text = f"SCORE: {score}"
                
                main_group.remove(bullet.sprite)
                player.bullets.remove(bullet)
                enemy.active = False
                enemy.sprite.hidden = True
                break

        if (enemy.active and
            player.sprite.x < enemy.sprite.x + ENEMY_SIZE and
            player.sprite.x + PLAYER_SIZE > enemy.sprite.x and
            player.sprite.y < enemy.sprite.y + ENEMY_SIZE and
            player.sprite.y + PLAYER_SIZE > enemy.sprite.y):
            
            lives -= 1
            lives_label.text = f"LIVES: {lives}"
            explosion = enemy.explode(enemy.sprite.x, enemy.sprite.y)
            enemy.active = False
            enemy.sprite.hidden = True
            
            for _ in range(3):
                pixels.fill((255, 0, 0))
                pixels.show()
                time.sleep(0.1)
                pixels.fill((0, 0, 0))
                pixels.show()
                time.sleep(0.1)
            
            if lives <= 0:
                game_over()

def game_over():
    game_over_label = label.Label(font, text="GAME OVER", color=0xFF0000, 
                               x=30, y=SCREEN_HEIGHT//2)
    game_over_label.anchor_point = (0.5, 0.5)
    game_over_label.scale = 2
    main_group.append(game_over_label)
    
    for _ in range(6):
        pixels.fill((255, 0, 0))
        pixels.show()
        time.sleep(0.2)
        pixels.fill((0, 0, 0))
        pixels.show()
        time.sleep(0.2)
    
    time.sleep(2)
    main_group.remove(game_over_label)
    reset_game()

def reset_game():
    global score, lives
    score = 0
    lives = 3
    score_label.text = f"SCORE: {score}"
    lives_label.text = f"LIVES: {lives}"
    
    for bullet in player.bullets[:]:
        main_group.remove(bullet.sprite)
    player.bullets.clear()
    
    for explosion in explosions[:]:
        main_group.remove(explosion.sprite)
    explosions.clear()
    
    for e in enemies:
        e.respawn()
        e.sprite.hidden = False
    
    player.sprite.x = SCREEN_WIDTH//2 - PLAYER_SIZE//2
    player.sprite.y = SCREEN_HEIGHT - PLAYER_SIZE - 10
    pixels.fill((0, 0, 0))
    pixels.show()

def cleanup():
    for explosion in explosions[:]:
        if not explosion.active:
            main_group.remove(explosion.sprite)
            explosions.remove(explosion)
    
    for bullet in player.bullets[:]:
        if bullet.sprite.y < -BULLET_SIZE:
            main_group.remove(bullet.sprite)
            player.bullets.remove(bullet)

# --- Main Loop ---
print("🎮 เริ่มเกม! โหมดอัตโนมัติทำงานอยู่")
print("✅ ภาพโปร่งใสทำงานแล้ว")
print("กดปุ่ม GP28 เพื่อสลับโหมดอัตโนมัติ/มือ")

last_auto_toggle = 0
auto_toggle_delay = 0.5
last_time = time.monotonic()
frame_count = 0


while True:
    current_time = time.monotonic()
    dt = current_time - last_time
    
    if dt >= GAME_SPEED:
        last_time = current_time
        frame_count += 1
        
        if btn_auto.value and current_time - last_auto_toggle > auto_toggle_delay:
            player.toggle_auto_mode()
            mode_text.text = "AUTO" if player.auto_mode else "MANUAL"
            mode_text.color = 0x00FF00 if player.auto_mode else 0xFFFF00
            last_auto_toggle = current_time
            print("🤖 โหมดอัตโนมัติ" if player.auto_mode else "🎮 โหมดมือ")

        player.update()
        for e in enemies:
            e.update()
        check_collision()
        
        for explosion in explosions[:]:
            if not explosion.update():
                main_group.remove(explosion.sprite)
                explosions.remove(explosion)
        
        if frame_count % 60 == 0:
            cleanup()
            frame_count = 0
    
    else:
        time.sleep(0.01)