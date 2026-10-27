# Dota Minigame Auto

[Português](README.md) · [Download for Windows](https://github.com/Proximithy/dota-minigame-auto/releases/latest/download/Dota-Minigame-Auto-Calibrado.exe)

A Windows assistant for the breakout minigame in **Dark Carnival inside Dota 2**. It tracks the boot on screen, predicts its path and moves the paddle using **A/D**. The standalone executable includes Python and a reference calibration.

## Getting started

1. Open the application. Click the **US flag / English** button at the top right to switch languages. Your choice is saved for the next launch; the Brazil flag switches back to Portuguese.
2. Run Dota in windowed or borderless mode and open the minigame.
3. If the bundled calibration does not match your screen, click **Calibrate**, return to Dota during the countdown, then select the arena, ball and paddle in the frozen image.
4. Return to Dota and press **F6** to preview detection or **F7** to start playing.

Switching the interface language does not change your calibration or restart the controller. A new calibration overrides the bundled reference.

**Automatic relaunch currently recognizes the Portuguese in-game prompt “TRAVAR POSIÇÃO DO CARRINHO”.** It sends Space twice, once per wait. English interface support does not add recognition of an English in-game prompt. Keep the game in Portuguese for this feature, or disable automatic relaunch and launch manually.

## Shortcuts inside Dota

| Key | Action |
| --- | --- |
| F6 | Preview without sending game inputs |
| F7 | Start automatic controls |
| F8 | Pause / resume |
| F9 | Stop |
| F10 | Save local diagnostics |

Inputs are sent only while Dota 2 is in the foreground. Losing focus or detection releases A/D. Alt+Tab can pause the minigame itself, so start using the in-game shortcuts.

## Local data

Calibration, language settings and diagnostics are stored in `%LOCALAPPDATA%\DotaMinigameAssistente`. Captures are not uploaded. To report a problem, press F10 during the failure and share the diagnostic folder you want reviewed.

The detector uses local OpenCV image processing. It does not read game memory or inject code into Dota. The bundled calibration is a starting point, not a match for every screen. Detection and trajectory prediction can still fail under untested effects or layouts.

## Running the source

Requires Windows and Python with Tkinter. See [the main README](README.md#executar-a-partir-do-código) for installation, build and test commands.

Original project code is [MIT licensed](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for libraries and visual references. This is an independent project, with no Valve endorsement.
