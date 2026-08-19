#Requires AutoHotkey v2.0
#SingleInstance Force

; =============================================================
;  F8 Macro Loop
; -------------------------------------------------------------
;  Press F8 to START the loop. Press F8 again to STOP it.
;
;  Each cycle performs:
;     1. Ctrl + C
;     2. Right arrow
;     3. Enter
;     4. Ctrl + V
;     5. Wait 2 seconds
;     6. Down arrow
;     7. Escape
;     8. Down arrow
;     9. Left arrow
;  ...then repeats until stopped.
;
;  Press Esc + F8, or just F8, to stop the loop at any time.
;  Exit the whole script from the tray icon, or with Ctrl+Alt+X.
; =============================================================

Running := false

F8:: {
    global Running
    Running := !Running          ; toggle on/off

    if (Running) {
        ToolTip("F8 loop STARTED")
        SetTimer(RemoveToolTip, -1000)
        RunLoop()
    } else {
        ToolTip("F8 loop STOPPED")
        SetTimer(RemoveToolTip, -1000)
    }
}

RunLoop() {
    global Running
    while (Running) {
        Send("^c")               ; Ctrl + C
        Sleep(50)

        Send("{Right}")          ; Right arrow
        Sleep(50)

        Send("{Enter}")          ; Enter
        Sleep(50)

        Send("^v")               ; Ctrl + V
        Sleep(50)

        Sleep(2000)              ; Delay of 2 seconds

        Send("{Down}")           ; Down arrow
        Sleep(50)

        Send("{Escape}")         ; Escape
        Sleep(50)

        Send("{Down}")           ; Down arrow
        Sleep(50)

        Send("{Left}")           ; Left arrow
        Sleep(50)
    }
}

RemoveToolTip(*) {
    ToolTip()
}

; Emergency exit: Ctrl + Alt + X
^!x:: ExitApp()
