import re

with open("research/paper/main.tex") as f:
    text = f.read()

# Find all citations
citations = set()
for match in re.finditer(r"\\cite\{([^}]+)\}", text):
    for k in match.group(1).split(","):
        citations.add(k.strip())

with open("research/paper/references.bib") as f:
    bib = f.read()

bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))

missing = citations - bib_keys
print("Citations in main.tex but missing in references.bib:")
for k in sorted(missing):
    print(" -", k)

print("\nKeys in references.bib not cited:")
for k in sorted(bib_keys - citations):
    print(" -", k)
