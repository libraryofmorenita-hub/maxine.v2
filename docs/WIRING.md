# Wiring (prototype v1, breadboard)

Pin numbers the firmware expects. ESP32-WROOM-32E dev boards, 3.3 V logic.
Bench-unverified: update this file as the first build is wired.

## Wearable
| Part | ESP32 pin | Note |
|---|---|---|
| I2C SDA (MAX30102, MLX90614, MPU-6050) | GPIO 21 | shared bus, 400 kHz, 4.7 kΩ pull-ups |
| I2C SCL | GPIO 22 | |
| Battery sense | GPIO 35 | LiPo through a 1:1 divider (2 × 100 kΩ) |

I2C addresses: MAX30102 0x57, MLX90614 0x5A, MPU-6050 0x68. No conflicts.

## Bedside
| Part | ESP32 pin | Note |
|---|---|---|
| E-paper MOSI / SCK / CS | 23 / 18 / 5 | SPI, mcauser driver defaults |
| E-paper DC / RST / BUSY | 17 / 16 / 4 | |
| BP module TX → | GPIO 26 (UART2 RX) | 9600 baud; moved off 16/17, which the display uses |
| BP module RX ← | GPIO 27 (UART2 TX) | |
| Buzzer | GPIO 25 | through an NPN transistor |
