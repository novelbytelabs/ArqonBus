
import sys

def repair():
    try:
        with open('notebooks/arqonhpo_experiments_01.ipynb', 'r') as f:
            content = f.read()
        
        # 1. Fix syntax error: params[\"alpha\\\"] -> params[\"alpha\"]
        # We need to be careful with exact string matching.
        # The grep showed: params[\"alpha\\\"]
        old_syntax = r'params[\"alpha\\\"]'
        new_syntax = r'params[\"alpha\"]'
        
        if old_syntax in content:
            content = content.replace(old_syntax, new_syntax)
            print("Fixed syntax error.")
        else:
            print("Syntax error pattern not found.")

        # 2. Add imports
        # Target: "import math\n",
        # New: "import math\n",\n    "from pathlib import Path\n",
        
        # Note: The file might use specific indentation.
        # Let's try to match the exact line from grep/view_file.
        # "import math\n",
        
        old_import = '"import math\\n",'
        new_import = '"import math\\n",\n    "from pathlib import Path\\n",'
        
        if old_import in content:
            content = content.replace(old_import, new_import)
            print("Added Path import.")
        else:
            print("Import pattern not found.")
            
        with open('notebooks/arqonhpo_experiments_01.ipynb', 'w') as f:
            f.write(content)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    repair()
