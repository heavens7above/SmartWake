#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
python logger.py &
python alarm.py &
wait
