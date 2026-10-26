# TimeWarp player manual

## Launch

1. Install Python 3.10 or newer.
2. From this folder, install the game dependency:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Start the game:

   ```bash
   python main.py
   ```

On systems where `python` points to Python 2, use `python3` instead.

## How to play

- Press **Enter** at the title screen to start.
- Move with **WASD** or the **arrow keys**.
- Hold **Space** to fire at asteroids and alien ships.
- Press **P** to pause or resume. Press **Esc** to quit.
- Avoid colliding with asteroids, alien ships, and their red shots. You start
  with **9 lives**.
- Destroy asteroids for **10 points** and alien ships for **40 points**.
- Collect a gold star for **100 points**, **one extra life**, and one star
  toward your time warp.
- After collecting **5 stars**, a glowing portal opens. Fly into it to rewind
  the game world by **5 seconds**.

## Time warp

When the portal activates, the recent five-second scene plays back as a
blue-tinted echo, including your past ship, shots, and hazards. Your current
ship is rewound to the beginning of that interval and remains under your
control, so you can fly alongside your echo and take a different shot or
collect something you missed.

Your score, lives, and star progress persist through the rewind; the five stars
used to open the portal are spent. The world and its hazards return to their
earlier positions. A new warp can be opened after the echo finishes and you
collect five more stars.

## Goal

There is one endless level. The scrolling gets faster and alien ships appear
more often as the run goes on. See how long you can survive and how high you
can score before losing all your lives.
