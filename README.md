# Wildlife Monitoring Robot

## Project Overview
The **Wildlife Monitoring Robot** is a tele-operated mobile robot designed for wildlife monitoring applications. The robot uses various sensors, including cameras and microphones, to detect the wildlife around it. The system is capable of user controlled movement through real-time communication with a base station for control.

### Key Features:
- Tele-operated movement with motor control using **PWM**.
- Wireless communication via **Wi-Fi** (TCP communication between the base station and Pi Zero 2W).
- **Motor control** through an STM32 microcontroller via **UART communication** with the Pi Zero 2W.
- Dynamic speed control with keyboard inputs from the base-station.
- Ability to detect wildlife using an AI overlay on the live video feed from the onboard camera
- Ability to detet wildlife using an audio recognition software, that takes inputs from the onboard microphone

---

## Components

### Hardware Components:
- **Pi Zero 2 W**: Acts as the main communication hub for wireless communication with the base station and relay to STM32.
- **STM32 Nucleo-L432KC**: Controls motors via Motor Driver.
- **L298N Motor Driver**: Drives the DC motors based on PWM signals from the STM32.
- **Microphone**: For audio capture.
- **USB Camera**: For live streaming and visual monitoring.

### Software Components:
- **Pi (Server)**: A Python TCP server running on the **Pi Zero 2 W** that handles incoming control commands from the base=station and forwards them to the STM32 via UART. Also sends video feed to the base station from the USB Camera.
- **Base Station (Client)**: A Python script that launches a GUI which handles the sending of control commands to the Pi through TCP and also handles the streaming of video feed to the GUI window.
- **STM32 Firmware**: Firmware running on the STM32 that processes incoming commands from the Pi and uses them to control the motors accordingly via PWM signals.

---

## Project Setup

### 1. Hardware Setup

1. **Pi Zero 2 W**:
   - TBC

2. **STM32 Nucleo-L432KC**:
   - TBC

3. **Motor Driver Setup**:
   - TBC

4. **Sensor Setup**:
   - TBC

---

### 2. Software Setup

#### Dependencies:
##### Pi Zero 2W
- piserver.py
##### Base-Station
- TBC
