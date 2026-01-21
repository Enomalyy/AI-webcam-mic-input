import subprocess
import threading
import winreg
import config

# --- POWERSHELL SCRIPTS ---
# 1. The Definition (Run ONCE at startup)
PS_DEFINE = r"""
$code = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
public class TouchKeyboardController {
    [ComImport, Guid("4ce576fa-83dc-4F88-951c-9d0782b4e376")] class UIHostNoLaunch {}
    [ComImport, Guid("37c994e7-432b-4834-a2f7-dce1f13b834b")] [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface ITipInvocation { void Toggle(IntPtr hwnd); }
    [DllImport("user32.dll", SetLastError = false)] static extern IntPtr GetDesktopWindow();
    public static void Toggle() {
        try {
            UIHostNoLaunch uiHost = new UIHostNoLaunch();
            ((ITipInvocation)uiHost).Toggle(GetDesktopWindow());
            Marshal.ReleaseComObject(uiHost);
        } catch (Exception) {
            Process.Start(new ProcessStartInfo("TabTip.exe") { UseShellExecute = true });
        }
    }
}
'@
Add-Type -TypeDefinition $code -Language CSharp
"""

# 2. The Trigger (Run whenever you gesture)
PS_TRIGGER = "[TouchKeyboardController]::Toggle()\n"

# Global persistent process
ps_process = None

def ensure_tablet_mode_enabled():
    """Registry hack to ensure the keyboard actually pops up on Desktop."""
    try:
        key_path = r"Software\Microsoft\TabletTip\1.7"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "EnableDesktopModeAutoInvoke", 0, winreg.REG_DWORD, 1)
    except Exception: 
        pass

def init_service():
    """Starts a persistent PowerShell process and pre-compiles the C# code."""
    global ps_process
    
    # 1. Set Registry Keys First
    ensure_tablet_mode_enabled()
    
    # 2. Start PowerShell
    if ps_process is None:
        try:
            ps_process = subprocess.Popen(
                ["powershell", "-Command", "-"], 
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Send the definition immediately to compile in background
            ps_process.stdin.write(PS_DEFINE + "\n")
            ps_process.stdin.flush()
            print("[Keyboard] Service Initialized (Background Compile)")
        except Exception as e:
            print(f"[Keyboard] Service Init Failed: {e}")

def toggle():
    """Sends the toggle command to the running process."""
    global ps_process
    
    # Update Config State
    config.keyboard_open = not getattr(config, 'keyboard_open', False)
    
    # Check if process is alive
    if ps_process and ps_process.poll() is None:
        try:
            ps_process.stdin.write(PS_TRIGGER)
            ps_process.stdin.flush()
        except Exception as e:
            print(f"[Keyboard] Trigger Error: {e}")
            init_service() # Restart if crashed
    else:
        init_service() # Restart if missing

def cleanup():
    """Kills the background process on app exit."""
    global ps_process
    if ps_process:
        print("[Keyboard] Stopping Service...")
        ps_process = None