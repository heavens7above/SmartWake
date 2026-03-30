# SmartWake — Google Colab Training Guide

> Train the sleep-detection `GradientBoostingClassifier` on the Fitbit dataset and export `sleep_model.pkl` ready to drop into the Railway server.

---

## Prerequisites

| What you need | Where to get it |
|---|---|
| Google account (Drive + Colab) | [accounts.google.com](https://accounts.google.com) |
| Kaggle account | [kaggle.com](https://kaggle.com) |
| `kaggle.json` API token | Kaggle → Settings → API → **Create New Token** |

---

## Phase 1 — One-Time Setup

### 1 · Upload the notebook to Colab

1. Open [colab.research.google.com](https://colab.research.google.com).
2. Click **File → Upload notebook**.
3. Choose `SmartWake/train/Train.ipynb` from your local machine.

> [!TIP]
> Alternatively: push the notebook to GitHub → open Colab → **File → Open notebook → GitHub tab** → paste the repo URL and select `train/Train.ipynb`.

---

### 2 · Upload your Kaggle token to Google Drive

The notebook fetches the Fitbit dataset via the Kaggle CLI. The token must live in Drive so Colab can access it.

1. Go to [drive.google.com](https://drive.google.com) and open **My Drive**.
2. Upload `kaggle.json` directly to the **root** of My Drive (not in any folder).

```
MyDrive/
└── kaggle.json   ← must be exactly here
```

> [!IMPORTANT]
> The notebook runs `!cp /content/drive/MyDrive/kaggle.json ~/.kaggle/` — the path is hardcoded. If you put the file in a subfolder the copy will fail.

---

### 3 · (Optional) Enable GPU

The model is a scikit-learn `GradientBoostingClassifier` which runs on CPU, so GPU is not required. Training on the full merged Fitbit dataset takes **~3–6 minutes** on a standard CPU runtime.

To enable GPU anyway: **Runtime → Change runtime type → T4 GPU → Save**.

---

## Phase 2 — Running the Notebook

Run cells **sequentially** — each cell depends on the one above.

### Cell 1 — Install dependencies & imports

```python
!pip install kaggle pandas numpy scikit-learn joblib matplotlib seaborn
```

**What to expect:** pip output ending in `Successfully installed …`. The imports below it should produce no output.

---

### Cell 2 — Mount Drive & download dataset

```python
from google.colab import drive
drive.mount('/content/drive')
!mkdir -p ~/.kaggle
!cp /content/drive/MyDrive/kaggle.json ~/.kaggle/
!chmod 600 ~/.kaggle/kaggle.json
!kaggle datasets download -d arashnic/fitbit
!unzip -o fitbit.zip
```

**What to expect:**

1. A pop-up asks you to allow Drive access → click **Connect to Google Drive** and authenticate.
2. The Kaggle CLI downloads `fitbit.zip` (~100 MB) and unzips it to `/content/Fitabase Data 4.12.16-5.12.16/`.

> [!WARNING]
> If you see `401 - Unauthorized` on the Kaggle download, your `kaggle.json` token has expired. Regenerate it on Kaggle (Settings → API → **Create New Token**) and re-upload to Drive.

---

### Cell 3 — Load raw data

```python
intensities = pd.read_csv('Fitabase Data 4.12.16-5.12.16/minuteIntensitiesNarrow_merged.csv')
sleep       = pd.read_csv('Fitabase Data 4.12.16-5.12.16/minuteSleep_merged.csv')
```

**What to expect:**

```
Intensities shape: (1325580, 3)
Sleep shape:       (188521, 4)
```
Exact row counts may vary slightly. Previews of both DataFrames appear below.

> [!NOTE]
> `Intensity` is the Fitbit wrist-movement intensity (0–3 scale). The sleep log uses `value`: **1 = asleep**, 2 = restless, 3 = awake.

---

### Cell 4 — Merge & label

Joins the two datasets on `(Id, minute)` and creates a binary `is_asleep` column (1 = asleep, 0 = awake/restless/unknown).

**No output expected.** If the merge returns 0 rows, check that both CSVs were read correctly in Cell 3.

---

### Cell 5 — Feature engineering (~30 s)

Resamples raw per-minute data into **5-minute windows** per user and computes:

| Feature | Meaning |
|---|---|
| `accel_magnitude_mean` | Average movement intensity in the window |
| `accel_magnitude_std` | Variability of movement |
| `accel_magnitude_max` | Peak movement |
| `zero_crossing_rate` | How often signal crosses its mean (activity rhythm) |
| `consecutive_still_count` | Stillness streak at window end |
| `hour_sin / hour_cos` | Cyclic time-of-day encoding (circadian proxy) |
| `notification_delta` | Placeholder (always 0 for offline training) |
| `charging` | Placeholder (always 0 for offline training) |

**What to expect:** No output, but the cell takes 20–60 seconds depending on runtime speed.

---

### Cell 6 — Label distribution

```
0    0.83
1    0.17
Name: label, dtype: float64
```

~83% awake, ~17% asleep. The severe class imbalance is handled in Cell 8 via `compute_sample_weight`.

---

### Cell 7 — Train/test split

Uses `GroupShuffleSplit` so **entire users** are held out in the test set — this prevents data leakage from the same person appearing in both train and test.

**No output expected.**

---

### Cell 8 — Train the model (~2–5 min)

```python
model = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42)
model.fit(X_train, y_train, sample_weight=sample_weights)
```

**What to expect:** A long progress bar or just silent execution followed by the model object repr. This is the slowest cell.

> [!TIP]
> To speed up iteration during experimentation, temporarily reduce `n_estimators=50`. For production accuracy, keep 200.

---

### Cell 9 — Evaluate

Prints a classification report and renders two plots:

- **Precision-Recall curve** — aim for AUC-PR > 0.65 on the held-out users.
- **Feature Importances bar chart** — `hour_sin/cos` and `accel_magnitude_mean` should dominate.

**Sample expected output:**

```
              precision    recall  f1-score   support

           0       0.95      0.97      0.96    120000
           1       0.72      0.62      0.67     24000

    accuracy                           0.93    144000
```

> [!NOTE]
> Lower recall on class 1 (asleep) is expected due to inter-user variability in the Fitbit dataset. The live model adapts per-user over time through the SmartWake server feedback loop.

---

### Cell 10 — Export & download

```python
joblib.dump(model, "sleep_model.pkl")
from google.colab import files
files.download("sleep_model.pkl")
```

**What to expect:** Your browser automatically downloads `sleep_model.pkl` (~5–15 MB).

---

## Phase 3 — Deploy the Model to the Server

Once downloaded, replace the model file in the SmartWake server:

```bash
# From the repo root
cp ~/Downloads/sleep_model.pkl server/sleep_model.pkl
```

Then redeploy to Railway (or restart locally):

```bash
# Railway (if you have the CLI)
cd server && railway up

# Or locally
uvicorn main:app --reload
```

The server's `/predict` endpoint loads `sleep_model.pkl` at startup — the new model is live immediately after restart.

> [!IMPORTANT]
> Commit the updated `sleep_model.pkl` to the repo if you want Railway's auto-deploy to pick it up on push:
> ```bash
> git add server/sleep_model.pkl
> git commit -m "chore: update trained sleep model"
> git push
> ```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `401 Unauthorized` on Kaggle download | Regenerate `kaggle.json` on Kaggle → re-upload to Drive |
| `FileNotFoundError: Fitabase Data …` | Re-run Cell 2; the unzip may have timed out |
| Drive mount pop-up never appears | Try a different browser or disable pop-up blockers |
| Cell 8 runs for >10 min | **Runtime → Disconnect and delete runtime** then re-run from top |
| `sleep_model.pkl` download doesn't start | Run `files.download("sleep_model.pkl")` in a new cell manually |
| Model accuracy < 0.85 | Verify `dataset` has > 50k rows before Cell 7; small datasets hurt GBM |

---

## Quick Checklist

- [ ] `kaggle.json` uploaded to **root** of My Drive
- [ ] Notebook opened in Colab from `train/Train.ipynb`
- [ ] All 10 cells run **top to bottom** without errors
- [ ] Classification report F1 (class 1) > 0.60
- [ ] `sleep_model.pkl` downloaded to local machine
- [ ] `sleep_model.pkl` copied to `server/sleep_model.pkl`
- [ ] Server restarted / redeployed
