import micropython
import board, busio, displayio, time
import adafruit_imageload
import digitalio
from time import sleep
from adafruit_st7789 import ST7789
import displayio
import neopixel
import adafruit_ds3231
import os, sys
import gc
import terminalio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
# ---------------- Config ----------------

# ---------------- Config ----------------
CYello = 0xFFFF00
DEBUG = False

# ---------------- Buttons ----------------
btn_H1 = digitalio.DigitalInOut(board.GP27)
btn_H1.direction = digitalio.Direction.INPUT
btn_H1.pull = digitalio.Pull.DOWN

btn_M1 = digitalio.DigitalInOut(board.GP22)
btn_M1.direction = digitalio.Direction.INPUT
btn_M1.pull = digitalio.Pull.DOWN

btn_Mode = digitalio.DigitalInOut(board.GP18)
btn_Mode.direction = digitalio.Direction.INPUT
btn_Mode.pull = digitalio.Pull.DOWN

# ---------------- Button Debounce ----------------
last_press = {"H1": 0, "M1": 0, "MODE": 0}
def read_button_lock(btn, key, lock_ms=250):
    now = time.monotonic()
    if btn.value:
        if now - last_press[key] > lock_ms / 1000:
            last_press[key] = now
            return True
    return False

# ---------------- Buzzer ----------------
Buzz = digitalio.DigitalInOut(board.GP26)
Buzz.direction = digitalio.Direction.OUTPUT
Buzz.value = False

# ---------------- Outputs ----------------
OUT1 = digitalio.DigitalInOut(board.GP13)
OUT2 = digitalio.DigitalInOut(board.GP14)
OUT3 = digitalio.DigitalInOut(board.GP15)
OUT1.direction = digitalio.Direction.OUTPUT
OUT2.direction = digitalio.Direction.OUTPUT
OUT3.direction = digitalio.Direction.OUTPUT
OUT1.value = False
OUT2.value = False
OUT3.value = False

# ---------------- CS for dual displays ----------------
cs1 = digitalio.DigitalInOut(board.GP2)
cs2 = digitalio.DigitalInOut(board.GP7)
cs1.direction = digitalio.Direction.OUTPUT
cs2.direction = digitalio.Direction.OUTPUT
cs1.value = True
cs2.value = True

# ---------------- RTC ----------------
i2c = busio.I2C(board.GP21, board.GP20)  # SCL, SDA
rtc = adafruit_ds3231.DS3231(i2c)
days = ("Mon","Tue","Wed","Thu","Fri","Sat","Sun")

# ---------------- NeoPixel ----------------
pixels = neopixel.NeoPixel(board.GP0, 10, brightness=0.03)
blue = (0, 0, 255)
for i in range(3):
    pixels[i] = blue
pixels.show()

# ---------------- TFT Display ----------------
displayio.release_displays()
spi = busio.SPI(board.GP10, MOSI=board.GP11)
display_bus = displayio.FourWire(
    spi, command=board.GP16, chip_select=board.GP1, reset=board.GP17, baudrate=24000000
)
display = ST7789(display_bus, width=240, height=320, rotation=180)

# ---------------- Load Assets ----------------
Nixie_Yakroo = displayio.OnDiskBitmap("/Yakroo108.bmp")
Back_Frame = displayio.OnDiskBitmap("/setC.bmp")
background = displayio.OnDiskBitmap("/pic/tube2.bmp")

digits = []
for i in range(10):
    digits.append(displayio.OnDiskBitmap(f"/pic/{i}p.bmp"))

DIGIT_WIDTH = 70
DIGIT_HEIGHT = 112
DIGIT_SPACING = 4
x_start = (240 - (2 * DIGIT_WIDTH + DIGIT_SPACING)) // 2
y_start = (320 - DIGIT_HEIGHT) // 2

# ---------------- Pre-allocate display groups (CRITICAL!) ----------------
group1 = displayio.Group()
group2 = displayio.Group()

# Backgrounds
bg1 = displayio.TileGrid(background, pixel_shader=background.pixel_shader, x=42, y=40)
bg2 = displayio.TileGrid(background, pixel_shader=background.pixel_shader, x=42, y=40)
group1.append(bg1)
group2.append(bg2)

# Digit grids (will only update .bitmap)
digit_m_tens = displayio.TileGrid(digits[0], pixel_shader=digits[0].pixel_shader, x=x_start, y=y_start)
digit_m_units = displayio.TileGrid(digits[0], pixel_shader=digits[0].pixel_shader, x=x_start + DIGIT_WIDTH + DIGIT_SPACING, y=y_start)
digit_h_tens = displayio.TileGrid(digits[0], pixel_shader=digits[0].pixel_shader, x=x_start, y=y_start)
digit_h_units = displayio.TileGrid(digits[0], pixel_shader=digits[0].pixel_shader, x=x_start + DIGIT_WIDTH + DIGIT_SPACING, y=y_start)

group1.append(digit_m_tens)
group1.append(digit_m_units)
group2.append(digit_h_tens)
group2.append(digit_h_units)

# ---------------- Pre-create splash group (ONCE!) ----------------
splash_group = displayio.Group()
splash_tile = displayio.TileGrid(Nixie_Yakroo, pixel_shader=Nixie_Yakroo.pixel_shader, x=60, y=80)
splash_group.append(splash_tile)

# ---------------- WS2812 & Output Functions ----------------
def update_second_ws2812():
    t = rtc.datetime
    sec = t.tm_sec
    sec2 = sec % 10
    for i in range(2, 10):
        pixels[i] = (0, 0, 0)
    if sec2 <= 2:
        pixels[2] = blue
    elif sec2 == 3:
        pixels[2] = pixels[3] = blue
    elif sec2 == 4:
        pixels[2] = pixels[3] = pixels[4] = blue
    elif sec2 == 5:
        pixels[2:6] = [blue]*4
    elif sec2 == 6:
        pixels[2:7] = [blue]*5
    elif sec2 == 7:
        pixels[2:8] = [blue]*6
    elif sec2 == 8:
        pixels[2:9] = [blue]*7
    elif sec2 == 9:
        pixels[2:10] = [blue]*8
    pixels.show()
    if DEBUG:
        print(f"[WS2812] {sec:02d}s -> sec2={sec2}")

def update_out_by_second():
    t = rtc.datetime
    sec = t.tm_sec
    sec2 = sec // 10
    if sec2 == 0:
        OUT1.value, OUT2.value, OUT3.value = False, False, False
    elif sec2 == 1:
        OUT1.value, OUT2.value, OUT3.value = False, False, True
    elif sec2 == 2:
        OUT1.value, OUT2.value, OUT3.value = False, True, False
    elif sec2 == 3:
        OUT1.value, OUT2.value, OUT3.value = False, True, True
    elif sec2 == 4:
        OUT1.value, OUT2.value, OUT3.value = True, False, False
    elif sec2 == 5:
        OUT1.value, OUT2.value, OUT3.value = True, False, True
    if DEBUG:
        print(f"[OUT] {sec:02d}s -> {sec2} OUT1={OUT1.value} OUT2={OUT2.value} OUT3={OUT3.value}")

# ========================================================================
# RTC SET FUNCTION - ตั้งค่า RTC โดยตรง
# ========================================================================
def rtc_set(year, month, day, hour, minute, weekday):
    """
    ตั้งค่า RTC โดยตรง
    Parameters:
    - year: ปี (เช่น 2025)
    - month: เดือน (1-12)
    - day: วันที่ (1-31)
    - hour: ชั่วโมง (0-23)
    - minute: นาที (0-59)
    - weekday: วันในสัปดาห์ (0=จันทร์, 6=อาทิตย์)
    """
    # สร้าง struct_time (วินาทีตั้งเป็น 0)
    t = time.struct_time((year, month, day, hour, minute, 0, weekday, -1, -1))
    
    # ตั้งค่า RTC
    rtc.datetime = t
    
    # แสดงข้อความยืนยัน
    print(f"RTC set to: {year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:00")
    
    # เรียกเสียงบัซเซอร์เพื่อยืนยัน
    Buzz.value = True
    time.sleep(0.1)
    Buzz.value = False
    time.sleep(0.05)
    Buzz.value = True
    time.sleep(0.1)
    Buzz.value = False

# ========================================================================
# CLOCK MODE (อัปเดตจอเมื่อวินาที >= 59)
# ========================================================================
def clock4():
    last_displayed_minute = -1
    last_displayed_hour = -1
    last_sec_checked = -1  # ป้องกันประมวลผลซ้ำ

    while True:
        t = rtc.datetime
        current_hour = t.tm_hour
        current_minute = t.tm_min
        current_sec = t.tm_sec

        # อัปเดตเอฟเฟกต์วินาที (LED, OUT) ทุกวินาที
        if current_sec != last_sec_checked:
            last_sec_checked = current_sec
            update_second_ws2812()
            update_out_by_second()

        # คำนวณ "เวลาที่ควรแสดง" — เปลี่ยนที่วินาที 59
        if current_sec >= 59:
            # แสดงนาที/ชั่วโมงถัดไปล่วงหน้า 1 วินาที
            display_minute = (current_minute + 1) % 60
            if display_minute == 0:
                display_hour = (current_hour + 1) % 24
            else:
                display_hour = current_hour
        else:
            # ยังไม่ถึงวินาที 59 → แสดงเวลาปัจจุบัน
            display_minute = current_minute
            display_hour = current_hour

        # --- อัปเดตจอ 1 (นาที) ถ้าเปลี่ยน ---
        if display_minute != last_displayed_minute:
            last_displayed_minute = display_minute
            m_tens = display_minute // 10
            m_units = display_minute % 10
            digit_m_tens.bitmap = digits[m_tens]
            digit_m_tens.pixel_shader = digits[m_tens].pixel_shader
            digit_m_units.bitmap = digits[m_units]
            digit_m_units.pixel_shader = digits[m_units].pixel_shader

            cs1.value = False
            cs2.value = True
            display.root_group = group1
            display.refresh()
            time.sleep(0.05)
            cs1.value = True

        # --- อัปเดตจอ 2 (ชั่วโมง) ถ้าเปลี่ยน ---
        if display_hour != last_displayed_hour:
            last_displayed_hour = display_hour
            h_tens = display_hour // 10
            h_units = display_hour % 10
            digit_h_tens.bitmap = digits[h_tens]
            digit_h_tens.pixel_shader = digits[h_tens].pixel_shader
            digit_h_units.bitmap = digits[h_units]
            digit_h_units.pixel_shader = digits[h_units].pixel_shader

            cs1.value = True
            cs2.value = False
            display.root_group = group2
            display.refresh()
            time.sleep(0.05)
            cs2.value = True

        # ถ้ากดปุ่ม MODE ให้รีเฟรชจอ (อาจเพิ่มฟังก์ชันอื่นในอนาคต)
        if read_button_lock(btn_Mode, "MODE"):
            # แสดง splash screen ชั่วคราว
            cs1.value = True
            cs2.value = True
            display.root_group = splash_group
            display.refresh()
            time.sleep(0.5)
            cs1.value = False
            cs2.value = False

        time.sleep(0.1)
        gc.collect()

# ========================================================================
# MAIN
# ========================================================================

# เริ่มต้นด้วยการส่งเสียงบัซเซอร์
Buzz.value = True
time.sleep(0.08)
Buzz.value = False
time.sleep(0.2)
Buzz.value = True
time.sleep(0.08)
Buzz.value = False

# Initial splash (use pre-created group)
cs1.value = True
cs2.value = True
display.root_group = splash_group
time.sleep(0.1)
cs1.value = False
cs2.value = False
gc.collect()

# ตั้งค่า RTC เริ่มต้น (ปี, เดือน, วันที่, ชั่วโมง, นาที, วันในสัปดาห์)
# ตัวอย่าง: 2025-11-4 11:50:00 วันอังคาร (วันอังคาร = 1)
# 0=จันทร์, 1=อังคาร, 2=พุธ, 3=พฤหัส, 4=ศุกร์, 5=เสาร์, 6=อาทิตย์
rtc_set(2025, 11, 4, 11, 50, 1)

# เข้าสู่โหมดนาฬิกาหลัก
clock4()
