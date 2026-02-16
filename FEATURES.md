# ValoSwitcher - New Features Guide

## 🚀 Quick Start

- **First launch**: Add accounts with "Add Account" button
- **Auto-capture**: Sessions save automatically after first password login
- **Quick switch**: Use `Ctrl+1-9` or tray menu to switch accounts instantly
- **Start minimized**: Enable auto-start to have ValoSwitcher ready in tray on boot

---

## 🎯 System Tray Support

ValoSwitcher now runs in the system tray for easy access!

### Features:
- **Minimize to Tray**: Clicking the X button minimizes to tray instead of closing
- **Quick Access**: Left-click the tray icon to show/hide the window
- **Tray Menu**: Right-click for quick actions:
  - Show/Hide window
  - Quick account switching (1-9 accounts)
  - Toggle auto-start with Windows
  - Quit application

### How to Use:
1. Click the X button or minimize - app goes to system tray
2. Click the tray icon to restore the window
3. Right-click the tray icon for quick account switching

---

## ⌨️ Keyboard Shortcuts

Switch accounts instantly with keyboard shortcuts!

### Available Shortcuts:
- `Ctrl+1` - Switch to Account 1
- `Ctrl+2` - Switch to Account 2
- `Ctrl+3` - Switch to Account 3
- ... up to `Ctrl+9`

**Note**: Shortcuts are assigned based on the order accounts appear in the app (top to bottom).

---

## 🚀 Auto-Start with Windows

Launch ValoSwitcher automatically when Windows starts.

### How to Enable:
1. Right-click the system tray icon
2. Click "Start with Windows" to toggle ON
3. Checkmark appears when enabled

### How to Disable:
1. Right-click the system tray icon
2. Click "Start with Windows" to toggle OFF

### Start Minimized:
- **Auto-start enabled**: Launches hidden in tray (no window appears)
- **Manual launch**: Run with `--minimized` flag to start hidden
  ```bash
  ValoSwitcher.exe --minimized
  ```
- **Default behavior**: Window shows normally when you open the app

**Note**: When auto-start is enabled, ValoSwitcher will automatically launch minimized to the system tray on Windows startup - perfect for keeping it ready without cluttering your desktop!

---

## 📦 Building Executable (.exe)

Create a standalone executable that doesn't require Python installed.

### How to Build:

1. **Open Command Prompt/PowerShell** in the ValoSwitcher folder

2. **Run the build script**:
   ```bash
   python build.py
   ```

3. **Wait for build to complete** (may take 2-5 minutes)

4. **Find your .exe**:
   - Located in: `dist/ValoSwitcher.exe`

### Important Notes:
- Config file is automatically created in `Documents\ValoSwitcher\config.ini`
- The `sessions` folder is automatically created in `Documents\ValoSwitcher\sessions\`
- Set correct paths in the config file before running (check your Documents folder)

### Build Script Features:
- Automatically installs PyInstaller if needed
- Creates single-file executable
- Includes all assets and dependencies
- Option to clean up build files after completion

---

## 📝 Account Management QOL

### Nicknames
Add custom labels to your accounts for easy identification!

**How to use**:
- When adding an account, fill in the "Nickname" field (e.g., "Main", "Smurf", "Alt")
- Nickname appears next to your in-game name in green italic text
- Optional - leave blank if you don't want a nickname

### Last Used Indicator
See which account you used last with a blue "● Last Used" badge!

**How it works**:
- Automatically tracks when you switch accounts
- Blue indicator shows on the most recently used account
- Updates in real-time as you switch

### Right-Click to Copy
Quickly copy account information to clipboard!

**How to use**:
1. Right-click on any account card
2. Choose what to copy:
   - Copy Name (just the username)
   - Copy Tag (just the tag)
   - Copy Full (Name#TAG format)
   - Copy Riot Username (email)
3. Paste anywhere with `Ctrl+V`

**Tip**: Great for quickly sharing your in-game name or copying credentials!

### Auto-Detect Riot Username
No need to manually enter your Riot email!

**How it works**:
- When adding an account, leave "Riot Username" field empty
- ValoSwitcher automatically reads it from your Riot Client settings
- Falls back to a placeholder if detection fails
- You can still manually enter it if you prefer

---

## 🎮 Session Management

Use Riot's "Stay signed in" feature for instant account switching!

### How to Use:
1. **First-time setup** (Automatic):
   - Click "Launch" on any account
   - ValoSwitcher logs you in with password
   - **Session is automatically captured!** (💾 becomes ✓)
   - Done! Next login will be instant.

2. **Manual capture** (Optional):
   - If you logged in outside ValoSwitcher with "Stay signed in"
   - Click the 💾 button to manually capture the session

3. **Switching accounts**:
   - Click "Launch" on any account
   - If session exists: **Instant switch** (no password needed)
   - If no session: Password login → auto-captures for next time

### Benefits:
- **Automatic** - No manual session capture needed
- First login uses password, all future logins are instant
- Faster account switching (no password typing)
- More secure (passwords not used repeatedly)

---

## 🎭 Deceive Integration

Appear offline while playing with friends!

### How to Use:
1. Download [Deceive](https://github.com/molenzwiebel/Deceive/releases) if you haven't
2. Set `DECEIVE_PATH` in `config.ini`:
   ```ini
   DECEIVE_PATH = C:\Path\To\Deceive.exe
   ```
3. Check "Deceive" on any account card
4. Click "Launch" - Riot Client opens with Deceive enabled

### Per-Account Toggle:
- Each account has its own Deceive checkbox
- Enable for accounts you want to appear offline
- Disable for accounts you want to appear online

---

## 📝 Configuration

### config.ini Settings:
```ini
[SETTINGS]
RIOTCLIENT_PATH = D:\Riot Games\Riot Client\RiotClientServices.exe
DECEIVE_PATH = C:\Path\To\Deceive.exe
DECEIVE_ENABLED = false

[ACCOUNT1]
name = YourName:TAG
riot_username = your.email@example.com
password = your_password
```

### File Locations:
- **Config**: `%USERPROFILE%\Documents\ValoSwitcher\config.ini` (created automatically)
- **Sessions**: `%USERPROFILE%\Documents\ValoSwitcher\sessions\` (created automatically)
- **Assets**: `assets/` folder (icons and images, bundled with exe)

---

## 🐛 Troubleshooting

### "Riot Client path not found"
- Check `RIOTCLIENT_PATH` in config.ini (located in `Documents\ValoSwitcher\config.ini`)
- Make sure path points to `RiotClientServices.exe`

### "Session capture failed"
- Make sure you're logged into Riot Client
- Try logging in again with "Stay signed in" checked
- Check that Riot Client is fully loaded before capturing

### Keyboard shortcuts not working
- Make sure ValoSwitcher window has focus
- Check if another app is using the same shortcuts

### Auto-start not working
- Check Windows startup apps: `Task Manager > Startup`
- Re-toggle "Start with Windows" in tray menu

### .exe build failed
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check that `assets` folder exists
- Try running `pip install pyinstaller` manually

---

## 💡 Tips & Tricks

1. **Quick Switching**: Use keyboard shortcuts (`Ctrl+1-9`) for fastest switching
2. **Minimize on Launch**: Set auto-start to run ValoSwitcher in the background
3. **Session First**: Always capture sessions for accounts you use frequently
4. **Organize Accounts**: Your most-used accounts should be at the top for better shortcuts
5. **Deceive Toggle**: You can change Deceive setting per-launch without restarting

---

## 🎉 Summary of Improvements

### Core Features:
✅ **System Tray Integration** - Minimize to tray, quick access
✅ **Keyboard Shortcuts** - Ctrl+1-9 for instant switching
✅ **Auto-Start** - Launch with Windows automatically (minimized to tray)
✅ **.exe Builder** - One-click build script
✅ **Session Management** - Auto-capture sessions after first login
✅ **Deceive Integration** - Per-account offline mode
✅ **Quick Switch Menu** - Right-click tray for account list

### QOL Enhancements:
✅ **Account Nicknames** - Add custom labels ("Main", "Smurf", etc.)
✅ **Last Used Indicator** - Blue badge shows recently used account
✅ **Right-Click to Copy** - Copy username/tag to clipboard easily
✅ **Auto-Detect Username** - Riot email auto-filled from system
✅ **Start Minimized** - Launch hidden to tray with auto-start

Enjoy your improved ValoSwitcher! 🎮

---

## 📜 Credits & Acknowledgments

### Original Project
- **ValoSwitcher** - Original concept and base code (July 2024)
  - GitHub: [Original ValoSwitcher Repository](https://github.com/E1Bos/VALocker)

### Improvements & Features
- **Enhanced by Claude Code** (Anthropic) - February 2025
  - System tray integration
  - Session management system
  - Keyboard shortcuts (Ctrl+1-9)
  - Auto-start with Windows
  - Account nicknames & last used tracking
  - Right-click context menus
  - Auto-detect Riot username
  - Auto-capture sessions
  - Build automation script

### Inspiration & Concepts
- **RiotSwitcher** ([GitHub](https://github.com/Andndre/RiotSwitcher)) - Session file backup concept
  - Inspired the session-based switching approach
  - "Stay signed in" file management technique

- **Deceive** ([GitHub](https://github.com/molenzwiebel/Deceive)) - Offline mode integration
  - Appear offline functionality
  - Per-account toggle support

### Technologies & Libraries
- **PyQt6** - Modern Qt6 bindings for Python
- **PyQt-Fluent-Widgets** - Fluent Design System components
- **PyQt6-Frameless-Window** - Frameless window implementation
- **Cloudscraper** - Cloudflare bypass for Tracker.gg API
- **Matplotlib** - KDA graph visualization
- **NumPy & SciPy** - Data processing for graphs
- **Tracker.gg API** - Rank and match statistics
- **Valorant-API** - Player card and level border images

### Special Thanks
- **Riot Games** - For Valorant and the Riot Client
- **Tracker.gg** - For providing the stats API
- **PyInstaller** - For .exe compilation support
- **Open Source Community** - For the amazing tools and libraries

---

## 📄 License

This project builds upon the original ValoSwitcher. All improvements and modifications are provided as-is for personal use.

**Disclaimer**: This tool is not affiliated with, endorsed by, or connected to Riot Games. Use at your own risk. Account automation may violate Riot Games' Terms of Service.

---

## 🔗 Useful Links

- **Original ValoSwitcher**: [GitHub Repository](https://github.com/E1Bos/VALocker)
- **Deceive (Offline Mode)**: [Download Latest Release](https://github.com/molenzwiebel/Deceive/releases)
- **Report Issues**: Create an issue in the repository
- **Tracker.gg**: [Check Your Stats](https://tracker.gg/valorant)

---

**Made with ❤️ and Python** | Enhanced February 2025
