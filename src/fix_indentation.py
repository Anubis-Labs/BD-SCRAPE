# Fix indentation issues in llm_handler.py

def fix_file():
    with open('llm_handler.py', 'r') as f:
        lines = f.readlines()
    
    fixed_lines = []
    for i, line in enumerate(lines):
        # Fix first issue around line 80
        if i == 79 and line.strip().startswith('elif "response" in outer_json:'):
            fixed_lines.append('            elif "response" in outer_json:\n')
            fixed_lines.append('                logger.error(f"Ollama \'response\' field was not a string. Type: {type(outer_json[\'response\'])}. Content: {str(outer_json[\'response\'])[:500]}")\n')
            fixed_lines.append('                return {"error": "Ollama \'response\' field was not a string as expected.", "details": str(outer_json[\'response\'])[:500]}\n')
        # Fix second issue around line 571
        elif i == 570 and line.strip() == 'return prompt':
            fixed_lines.append('    return prompt\n')
        else:
            fixed_lines.append(line)
    
    with open('llm_handler.py', 'w') as f:
        f.writelines(fixed_lines)
    
    print("Fixed indentation issues in llm_handler.py")

if __name__ == "__main__":
    fix_file() 