SWF THUMBNAIL MAKER — Linux X11

Run this on your MX Linux desktop (Xfce/X11), not the OMV SSH terminal.
Install the supporting packages once:

sudo apt install python3-tk python3-pil.imagetk xdotool imagemagick

Extract this ZIP, open a terminal in the extracted folder, and run:

python3 swf_thumbnail_maker.py

Choose your SWF folder. For Samba, mount/open the share in your file manager
first and select its local mounted path (not smb://). Choose the actual
flashplayer.bin or Ruffle executable with Browse. This program does not include
or download a player. Use a standalone player that accepts a filename argument;
Flatpak launchers and .desktop shortcuts are not supported in this first version.
Close any existing player instances before starting.

Set capture seconds, for example 3, 8, 15 or 5, 15, 30, 60. Times are measured
from discovery of the player window, rather than from verified game readiness.
Click Start batch. The app opens each SWF, resizes its window, takes captures,
then closes that player and moves to the next game. Keep the window visible
and avoid using the desktop while capturing. No automatic clicks are sent.
You can click a game's Play button yourself, and use Capture now for an extra
picture before the final timer expires. Stop ends the batch and closes the player.

The final timed picture is saved beside the SWF:
  My Game.swf
  My Game.png

Existing matching .png files are skipped and never overwritten by the batch.
Delete or rename a poor matching PNG if you want that game processed again.
All alternative captures stay under:
  _swf_captures/My Game.swf/<timestamp>_8s.png

Select a capture in the list to preview it. After the batch finishes, click
Use selected picture as matching PNG to choose a better image (replacement
requires confirmation). Load saved captures restores the review list later.
Each game's original folder must be writable, including on Samba. This does
not modify the SWF files. Captures are full window resolution, not tiny icons.

First try a small folder with two or three games. A screenshot can be a title
screen, loading screen, or blank window; the app does not understand gameplay
or determine the game's name/genre. Some games need clicks, missing resources,
or a different player. Window discovery uses the launched process's PID;
players that hand off to an existing process may fail. Hardware-rendered games
can produce black captures. Wayland is unsupported: use an X11 login session.
An unsupported Flash game cannot be fixed by this capture utility.

Only run games you trust. This utility does not sandbox the player. Prefer a
maintained player where compatible; old Adobe Flash players are unsupported.

Validation: Python compilation and non-GUI logic checks passed. Actual player
launches, window discovery and screenshots must be verified on your desktop;
they could not be exercised in the build environment.
