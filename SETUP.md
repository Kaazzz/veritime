# Veritime Setup Guide

This guide is for staff setting up Veritime for the first time. No technical knowledge is required.

---

## What You Need

- A computer running Windows 10 or 11
- The Arduino device plugged in via USB
- A web browser (Chrome, Edge, or Firefox)
- An internet connection (for first-time setup only)

---

## One-Time Setup

### 1. Install Python

> **Skip this step if Python is already installed.**

1. Go to **https://www.python.org/downloads/**
2. Click the large **Download Python** button
3. Run the installer that downloads
4. **Important:** On the first screen, tick the box that says **"Add Python to PATH"** before clicking Install
5. Click **Install Now** and wait for it to finish

### 2. Plug in the Arduino

Connect the Arduino device to a USB port on the computer. Windows may install drivers automatically — wait for that to finish (usually under a minute).

---

## How to Run Veritime

1. Open the **Veritime** folder
2. Double-click **start.bat**
3. A black window will appear — this is normal. Leave it open.
4. Your web browser will open automatically to the Veritime dashboard

That's it. Veritime is now running.

---

## How to Stop Veritime

Close the black window that appeared when you started Veritime. The system will stop immediately.

---

## Everyday Use

Each day:
1. Make sure the Arduino is plugged in
2. Double-click **start.bat**
3. The browser will open automatically

No other steps are needed. The first-time setup (creating the environment and installing packages) only happens once.

---

## Troubleshooting

### "Python was not found"
Python is not installed, or was installed without the "Add to PATH" option.
- Reinstall Python from **https://www.python.org/downloads/**
- On the installer's first screen, tick **"Add Python to PATH"**

### "Arduino not detected"
The Arduino is not plugged in, or Windows hasn't finished installing its drivers.
- Unplug the Arduino and plug it back in
- Wait 30 seconds, then double-click **start.bat** again

### "Multiple USB devices found"
If more than one device is plugged in via USB, Veritime will ask which one is the Arduino.
- Type the number next to the Arduino in the list and press **Enter**
- If you're unsure, unplug any other USB devices and try again

### "Could not install required packages"
This usually means there's no internet connection.
- Connect to the internet and double-click **start.bat** again
- This step is only needed once; after that, Veritime works offline

### The browser doesn't open automatically
- Wait a few more seconds, then open your browser manually
- Type **http://localhost:5000/landing** in the address bar and press Enter
- Make sure the black window is still open

### The page says "This site can't be reached"
The server may still be starting up, or it stopped unexpectedly.
- Check that the black window is still open
- If the window closed, double-click **start.bat** again

---

## Need Help?

Contact the system administrator or the person who set up Veritime at your school.
