
import os

file_path = "e:/Lichess app project/Lichess-opening-coach-main/app.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Target range: 322 to 1117 (1-based) -> 321 to 1117 (0-based slice, exclusive end? No, 1117 is included)
# Python slice [start:end] excludes end. So 321:1117 means 321 up to 1116.
# I want 321 up to 1116 (line 1117).
# So slice should be 321:1117.

start_idx = 321
end_idx = 1117

# Verify
print(f"Line {start_idx+1}: {lines[start_idx]}")
print(f"Line {end_idx}: {lines[end_idx-1]}")

# Check if indentation is 4 spaces
if not lines[start_idx].startswith("    "):
    print("Warning: Start line does not start with 4 spaces.")
    # exit(1)

new_lines = []
for i, line in enumerate(lines):
    if start_idx <= i < end_idx:
        if line.startswith("    "):
            new_lines.append(line[4:])
        elif line.strip() == "":
            new_lines.append(line) # Keep empty lines
        else:
            print(f"Warning: Line {i+1} not indented: {line}")
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Indentation fixed.")
