# SmartWake Field Data Collection Protocol (Tier A)

**Document Status:** Operational Research Protocol  
**Principal Investigator:** 3rd-year BSc Data Science and AI Candidate  
**Institutional Ethics Framework:** Faculty of Engineering and Informatics Human Research Guidelines  

---

## 1. Study Objective & Overview

This protocol governs the prospective collection of naturalistic sleep telemetry using the SmartWake smartphone client (`termux/logger.py` and `SmartWakeApp`). The goal is to assemble a naturalistic, non-synthetic evaluation benchmark of nocturnal motion, battery charging dynamics, notification activity, and morning self-reported sleep inertia across a minimum of 14 consecutive nights per subject.

> [!IMPORTANT]
> **Data Availability Status:** As verified during the repository audit (`research/REPO_AUDIT.md`), the repository does **not** currently contain historical recorded telemetry sessions in version control. Per Project Hard Rule 2, no synthetic data may be passed off as real, and no telemetry files may be fabricated. This protocol provides the complete operating procedure for participants to gather Tier A data. All empirical results in the interim paper are evaluated on Tier C (PhysioNet gold-standard clinical PSG dataset) and Tier B (labeled synthetic sensitivity benchmarks).

---

## 2. Participant Recruitment & Target Sample Size

* **Target Cohort:** 
  - Primary participant (repository maintainer): minimum 14 consecutive nights.
  - Secondary volunteer cohort: 3–5 consenting adult volunteers (target: 40–70 total nights of telemetry).
* **Inclusion Criteria:**
  - Age $\ge 18$ years.
  - Regular sleep-wake routine (regular bedtimes between 21:00 and 02:00).
  - Android smartphone running Android 7.0 (API 24) or newer.
* **Exclusion Criteria:**
  - Shift workers undergoing rotating nocturnal shifts.
  - Active diagnoses of primary sleep disorders (e.g., severe obstructive sleep apnea, narcolepsy, REM sleep behavior disorder).
  - Active use of sedative-hypnotic medications during the collection window.

---

## 3. Sensor Configuration & Hardware Placement

* **Device Positioning:**
  - The smartphone must be placed flat on the mattress surface, positioned **parallel to the torso** approximately 15–25 cm from the participant's shoulder or upper chest.
  - The screen should face upwards or downwards consistently throughout the study.
  - The device must **not** be placed on a rigid bedside nightstand (which dampens bedding vibrations) or beneath pillows (which introduces thermal hazards).
* **Power Connection:**
  - The smartphone must be plugged into its primary charging adapter overnight to evaluate the `charging` feature state and prevent battery exhaustion during background polling.
* **Background Process Permissions:**
  - Android battery optimization must be set to "Unrestricted" / "Don't optimize" for Termux or the SmartWake Flutter client.
  - Termux wake lock must be active (`termux-wake-lock`) to prevent OS CPU deep-sleep suspension.

---

## 4. Morning Self-Report Battery

Within 5 minutes of final awakening (either by SmartWake or upon natural awakening), the participant must complete the two validated instruments:

### 1. Karolinska Sleepiness Scale (KSS)
*Please circle the number that best reflects your state of alertness right now upon waking:*
* `1` — Extremely alert
* `2` — Very alert
* `3` — Alert
* `4` — Rather alert
* `5` — Neither alert nor sleepy
* `6` — Some signs of sleepiness
* `7` — Sleepy, but no effort to keep awake
* `8` — Sleepy, some effort to keep awake
* `9` — Very sleepy, great effort to keep awake, fighting sleep

### 2. Sleep Inertia Grogginess Scale (SIGS - 1 to 5)
*How groggy, disoriented, or sluggish do you feel right now?*
* `1` — Completely clear-headed, immediate physical and mental vigor
* `2` — Mild morning sluggishness, fades within 2–3 minutes
* `3` — Moderate grogginess, noticeable mental fog
* `4` — Substantial grogginess, difficulty orienting or coordinating
* `5` — Severe sleep inertia, profound confusion, strong urge to return to sleep

### 3. Objective Log Entries
* Scheduled Wake Deadline: `[HH:MM]`
* Actual Alarm Fire Time: `[HH:MM]`
* Self-Reported Bedtime (Lights Out): `[HH:MM]`
* Estimated Sleep Latency (Minutes to fall asleep): `[Minutes]`

---

## 5. Participant Information & Informed Consent Text

```
INFORMED CONSENT FOR SMARTWAKE RESEARCH STUDY

Title: Empirical Evaluation of Smartphone Accelerometer Telemetry for Sleep Onset Detection 
       and Smart Alarm Scheduling
Institution: Department of Computer Science & Data Science, Faculty of Engineering and Informatics

PURPOSE:
You are invited to participate in a student research study investigating whether smartphone motion 
sensors can accurately estimate sleep onset and time alarms to reduce morning grogginess.

PROCEDURES:
If you agree to participate, you will run the SmartWake logging application on your Android phone 
while you sleep for 14 nights. The application will log:
  1. Triaxial acceleration values (x, y, z in m/s^2) polled once every 5 minutes.
  2. Battery charging status and percentage.
  3. Total count of unread notifications in your status bar.
No audio, video, GPS location, personal messages, or contact lists will ever be collected or stored.

DATA PRIVACY & CONFIDENTIALITY:
All recordings will be pseudopseudonymized with a random UUID. Your identity will never be linked to 
your telemetry files in any publication, code repository, or public dataset. All raw telemetry will 
be stored on encrypted drives.

RISKS & RIGHTS:
The study entails minimal risk. You may withdraw at any time and request deletion of your telemetry.

CONSENT DECLARATION:
I confirm that I have read and understood this document. I freely agree to participate.

Participant Signature: _______________________      Date: ______________
```

---

## 6. Execution Commands & Telemetry Harvesting

Participants execute the following sequence on their Android Termux environment:

```bash
# 1. Update and install required termux packages
pkg update && pkg install -y python git termux-api jq

# 2. Clone the repository and navigate to termux client
git clone https://github.com/heavens7above/SmartWake.git ~/smartwake
cd ~/smartwake/termux

# 3. Export environment configuration
export SMARTWAKE_URL="https://your-server-domain.railway.app"
export SMARTWAKE_API_KEY="your-secure-api-key"

# 4. Acquire CPU wake-lock to prevent OS deep sleep
termux-wake-lock

# 5. Launch background data collection daemon
bash start.sh
```

To harvest logs locally without a server, participant logs can be redirected to local storage:
```bash
python logger.py --local-storage ~/smartwake/logs/session_$(date +%Y%m%d).json
```
