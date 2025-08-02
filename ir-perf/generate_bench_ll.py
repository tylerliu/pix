import sys
from pathlib import Path

template_type = sys.argv[1]  # e.g., "arithmetic", "memory", "phi", "pointer"
template = Path(sys.argv[2]).read_text()
snippet = Path(sys.argv[3]).read_text()
output = sys.argv[4]

# Map template types to function names and template files
template_configs = {
    "arithmetic": {
        "template_file": "templates/arithmetic.ll"
    },
    "memory": {
        "template_file": "templates/memory.ll"
    },
    "phi": {
        "template_file": "templates/phi.ll"
    },
    "pointer": {
        "template_file": "templates/pointer.ll"
    },
    "fp-arithmetic": {
        "template_file": "templates/fp-arithmetic.ll"
    },
    "conversion": {
        "template_file": "templates/conversion.ll"
    },
    "branching": {
        "template_file": "templates/branching.ll"
    },
    "call": {
        "template_file": "templates/call.ll"
    },
    "alloca": {
        "template_file": "templates/alloca.ll"
    }
}

if template_type not in template_configs:
    print(f"Error: Unknown template type '{template_type}'")
    sys.exit(1)

config = template_configs[template_type]

start = template.index('; --- The instruction you want to measure: ---')
end = template.index('; -------------------------------------------', start)
new_ll = template[:start] + '; --- The instruction you want to measure: ---\n' + snippet + '\n' + template[end:]
Path(output).write_text(new_ll) 