# valorant-picker

## How to run team reading and pick recommendation

This mode works locally on your computer. The program reads data from the local Riot Client and Valorant read-only endpoints.

The program does **not** select an agent, lock an agent, click inside the game client, or save tokens to disk.

### 1. Open the terminal in the project folder

In PowerShell, go to the project directory:

```powershell
cd *\valo picker"
```

### 2. Check if the program works

Run:

```powershell
python -m valo_picker 
```

You should see a screen like this:

```text
PRE-GAME (AGENT SELECT)
Map: Ascent
Your Team:
Recommendation:
Best Pick: Omen
```

If this works, Python and the project are running correctly.

### 3. Launch Riot Client and Valorant

Start normally:

* Riot Client
* Valorant
* enter a lobby
* start a queue or custom game
* wait until you enter Agent Select

The program makes the most sense only when you are in the **Agent Select** phase.

