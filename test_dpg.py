import sys
sys.path.insert(0, 'C:/coder/app/ca-analyzer')
try:
    exec(open('C:/coder/app/ca-analyzer/main_dpg.py', encoding='utf-8').read())
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
