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

def clean_garbage():
    garbage_dirs = ["__pycache__", ".pytest_cache"]
    garbage_exts = [".pyc", ".pyo", ".DS_Store", "-journal"]
    
    deleted_items = 0
    # Clean files first
    for p in root.rglob("*"):
        if p.is_file() and any(p.name.endswith(ext) for ext in garbage_exts):
            p.unlink()
            print(f"  deleted file: {p.relative_to(root)}")
            deleted_items += 1

    # Clean dirs manually (bottom-up to avoid deleting parents before children)
    import shutil
    for p in sorted(root.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p.is_dir() and p.name in garbage_dirs:
            shutil.rmtree(p)
            print(f"  deleted dir: {p.relative_to(root)}")
            deleted_items += 1
            
    return deleted_items

for p in python_files:
    src = p.read_text(encoding="utf-8")
    cleaned = clean_python(src)
    if cleaned != src:
        p.write_text(cleaned, encoding="utf-8")
        print(f"  cleaned comments: {p.relative_to(root)}")

for p in dart_files:
    src = p.read_text(encoding="utf-8")
    cleaned = clean_dart(src)
    if cleaned != src:
        p.write_text(cleaned, encoding="utf-8")
        print(f"  cleaned comments: {p.relative_to(root)}")

print("\nRunning Garbage File Collection...")
total_deleted = clean_garbage()

print(f"\nDone. Cleaned {total_deleted} garbage files/folders.")
