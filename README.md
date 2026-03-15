# NHL Draft Lottery Simulator

Live odds simulator for the NHL Draft Lottery, auto-updated daily from NHL standings.

## How it works

1. **GitHub Action** runs every morning at 6 AM UTC
2. Fetches current NHL standings from `api-web.nhle.com`
3. Identifies the 16 non-playoff teams, sorts by points% (worst first)
4. Assigns official NHL lottery odds by position (25.5% → 0.5%)
5. Merges in manual `notes.json` (trade conditions, forfeitures)
6. Writes `docs/odds.json` and commits if changed
7. GitHub Pages serves `docs/index.html` which fetches `odds.json` on load

## Repo structure

```
├── generate_odds.py          # Standings → odds JSON
├── notes.json                # Manual trade/forfeiture notes
├── .github/
│   └── workflows/
│       └── update-odds.yml   # Daily cron job
└── docs/
    ├── index.html            # The simulator (GitHub Pages root)
    └── odds.json             # Auto-generated, committed by Action
```

## Setup

### 1. Create the repo and enable GitHub Pages

```bash
git init nhl-lottery
cd nhl-lottery
# copy all files in
git add .
git commit -m "init"
git push -u origin main
```

In GitHub repo settings → Pages → Source: **Deploy from branch** → `main` → `/docs`

### 2. Update the ODDS_URL in index.html

Open `docs/index.html` and change:
```js
const ODDS_URL = "./odds.json";
```
to your actual GitHub Pages URL if needed. The relative path works fine when
served from GitHub Pages.

### 3. Run the Action manually once

Go to **Actions → Update NHL Lottery Odds → Run workflow** to generate the
initial `docs/odds.json`.

After that it runs automatically every morning. You can also trigger it manually
any time from the Actions tab.

## Updating notes manually

Edit `notes.json` — it's an array of note objects:

```json
[
  {
    "teamId": "OTT",
    "text": "Pick forfeited — Dadonov trade penalty",
    "type": "warning"
  },
  {
    "teamId": "FLA",
    "text": "Pick goes to Chicago Blackhawks (Seth Jones trade, top-10 protected)",
    "type": "trade"
  }
]
```

`type` can be `"warning"` (amber) or `"trade"` (blue). Notes appear on the
team's card in the odds table.

## Dropping into an existing repo

If you want this inside `stat-trick-hockey` or another org repo instead of
a standalone repo, just:

1. Copy `generate_odds.py`, `notes.json`, and `.github/workflows/update-odds.yml`
   into the root of the existing repo
2. Copy `docs/index.html` into whatever subdirectory you're serving from
3. Update `ODDS_URL` in `index.html` to point to the correct relative or
   absolute path for `odds.json`
