# F8 Macro Loop (AutoHotkey)

A simple [AutoHotkey v2](https://www.autohotkey.com/) script. Press **F8** to
start a repeating macro; press **F8** again to stop it.

## What each cycle does

1. `Ctrl + C`
2. `Right` arrow
3. `Enter`
4. `Ctrl + V`
5. Wait **2 seconds**
6. `Down` arrow
7. `Escape`
8. `Down` arrow
9. `Left` arrow

...then repeats until you stop it.

## How to use

1. Install **AutoHotkey v2** from <https://www.autohotkey.com/>.
2. Double-click `f8_macro.ahk` to run it (a green "H" icon appears in the tray).
3. Click into the window/app you want to control.
4. Press **F8** to start the loop. A tooltip shows "F8 loop STARTED".
5. Press **F8** again to stop. A tooltip shows "F8 loop STOPPED".

## Exiting

- **Ctrl + Alt + X** quits the script entirely, or
- Right-click the tray icon → **Exit**.

## Tuning

- The `2 seconds` delay is `Sleep(2000)` (milliseconds) in `f8_macro.ahk`.
- The small `Sleep(50)` after each key gives the target app time to react.
  Increase these if a slow app misses keystrokes.
