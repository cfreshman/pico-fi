## chess

THIS IS BROKEN.

It works in theory, and you may be able to load a synced game on two devices, but even at the first move the Pico hits a memory allocation error when trying to sync the board state again. TODO - rewrite board sync to be less memory intensive.

### Setup
1. Install [pico-fi](/README.md#install)
1. Build with **chess** enabled
   ```
   python3 build -a chess
   ```
