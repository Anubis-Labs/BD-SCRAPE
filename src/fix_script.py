with open('llm_handler_fixed.py', 'r') as f:
    content = f.read()

# Fix the indentation issues
fixed_content = content.replace('    return prompt', 'return prompt')

with open('llm_handler_fixed.py', 'w') as f:
    f.write(fixed_content)
    
print('Fixed the indentation in llm_handler_fixed.py') 