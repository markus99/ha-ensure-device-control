import sys

input_file = "ui-lovelace.yaml"
output_file = "ui-lovelace-updated.yaml"

with open(input_file, "r") as f:
    lines = f.readlines()

new_lines = []
current_entity = None
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    
    # Capture entity_id
    if stripped.startswith("- entity:"):
        current_entity = stripped.split(":")[1].strip()
        new_lines.append(line)
        i += 1
        continue
    
    # Detect tap_action: toggle
    if stripped == "tap_action:":
        # Peek ahead to see if it's 'action: toggle'
        if i + 1 < len(lines) and lines[i + 1].strip() == "action: toggle":
            # Replace with call-service block
            indent = " " * (len(line) - len(line.lstrip()))
            new_lines.append(f"{indent}tap_action:\n")
            new_lines.append(f"{indent}  action: call-service\n")
            new_lines.append(f"{indent}  service: ensure.toggle\n")
            new_lines.append(f"{indent}  data:\n")
            new_lines.append(f"{indent}    entity_id: {current_entity}\n")
            i += 2  # skip the original 'tap_action' + 'action: toggle'
            continue
    
    # Default: copy line as-is
    new_lines.append(line)
    i += 1

with open(output_file, "w") as f:
    f.writelines(new_lines)

print(f"Updated Lovelace YAML written to {output_file}")
