import re
import pathlib

root = pathlib.Path("/Users/mastersam/Documents/SmartWake")

python_files = (
    list((root / "server").rglob("*.py"))
    + list((root / "termux").rglob("*.py"))
)

dart_files = list((root / "SmartWakeApp" / "lib").rglob("*.dart"))

def clean_python(src):
    out = re.sub(r'^[ \t]*#\s*CODEX-FIX:[^\n]*\n', '', src, flags=re.MULTILINE)
    out = re.sub(r'(\S[^\n]*?)\s+#\s*CODEX-FIX:[^\n]*', r'\1', out)
    return out

def clean_dart(src):
    out = re.sub(r'^[ \t]*//\s*CODEX-FIX:[^\n]*\n', '', src, flags=re.MULTILINE)
    out = re.sub(r'(\S[^\n]*?)\s+//\s*CODEX-FIX:[^\n]*', r'\1', out)
    return out

for p in python_files:
    src = p.read_text(encoding="utf-8")
    cleaned = clean_python(src)
    if cleaned != src:
        p.write_text(cleaned, encoding="utf-8")
        print(f"  cleaned: {p.relative_to(root)}")

for p in dart_files:
    src = p.read_text(encoding="utf-8")
    cleaned = clean_dart(src)
    if cleaned != src:
        p.write_text(cleaned, encoding="utf-8")
        print(f"  cleaned: {p.relative_to(root)}")

print("Done.")
