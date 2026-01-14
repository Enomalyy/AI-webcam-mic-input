# AI-webcam-mic-input
Physical mouse and keyboard replacement by using computer vision to track hand gestures and local AI for voice dictation, optimized (as best I can) for lower end systems. 

Offline, low resource usage solution for Windows 10 computers lacking, um, everything. 

(This project essentially demonstrates the use of offline AI running on older hardware -  Google's MediaPipe Hands and Faster-Whisper (Int8 Quantization), along with WebRTCVAD to buffer the auido for better voice to text.)

Runs silently in the System Tray with a "Headless" option (no video feed) to save resources.


Useful for mounted monitors, or for projects with minimal need for direct contact. Personally I built for use with an old i5 4200u based system with Tiny10 (https://archive.org/details/tiny-10-NTDEV) as the OS.

Faster-Whisper Integration: Includes a VAD (Voice Activity Detection) system that records audio only when a specific hand gesture is held, then transcribes it using a quantized Whisper model.  this is awesome.

# Installation
Option 1: Compiled Executable (Recommended)

Download AIMouse_Final.exe.

Place it in your desired folder (or Windows Startup folder).

Run it. It will create a settings.json file automatically.

Option 2: Run from Source

Clone the repository.

Install dependencies:

    pip install opencv-python mediapipe pyautogui pyaudio keyboard sounddevice faster-whisper pystray pillow webrtcvad-wheels

Run the script:

    python main.pyw

optionally, compile using:

    pyinstaller --noconfirm --onedir --windowed --name "AIInput" --additional-hooks-dir=. --collect-all "mediapipe" --hidden-import "faster_whisper" --hidden-import "pystray" --hidden-import "PIL" --hidden-import "cv2" --add-data "config.py;." main.py
    # Note this is uses a custom hook to overcome webrtcvad windows issues.

For control of programs requiring provledges to mouse over (e.g. Task Manager) run as administrator.

# Gestures:
(imagine a finger gun, point it upwards, this is the starting position)

Index finger: control mouse.
Thumb to middle finger joint - click (imagine a finger gun, point it upwards)
Pinkie raise: right click
Middle finger raise - open windows keyobard (tabtip.exe) using some COM black magic
Thumb to pinkie - voice transciption activation.

# Configuration (settings.json)

The application generates a settings.json file on the first launch. You can edit this file manually or use the built-in GUI (Right-click Tray Icon -> Settings).

    SENSITIVITY: Border size (in pixels) ignored by the camera to allow reaching screen edges.

    SMOOTHING: Higher values = smoother cursor, Lower values = faster response.

    AUDIO_START: Set to true to enable the Whisper engine automatically on boot.

    HEADLESS_DEFAULT: Set to true to start without the camera window (saves CPU).

To interact with UAC prompts and Task Manager, assuming you grant admin privledges. (You should)
Additionally, as of 1.1, the program will not display mouse output if no mouse is plugged in - Windows turns off mouse rendering if no mouse is detected. This can be changed in the registry.
Note: This project was made by an EE major using AI assistance and minimal python skills. Dont yell at me.

