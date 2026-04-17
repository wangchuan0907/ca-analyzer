"""Debug DPG startup - write to file"""
import sys
import os
import traceback

log = []

def w(msg):
    log.append(msg)
    print(msg, flush=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import dearpygui.dearpygui as dpg
    w(f"[OK] DPG imported")
except Exception as e:
    w(f"[FAIL] DPG import: {type(e).__name__}: {e}")
    traceback.print_exc()
    with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
        f.write('\n'.join(log))
    sys.exit(1)

try:
    dpg.create_context()
    w("[OK] create_context")
except Exception as e:
    w(f"[FAIL] create_context: {e}")
    with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
        f.write('\n'.join(log))
    sys.exit(1)

try:
    dpg.create_viewport(title="test", width=800, height=600)
    w("[OK] create_viewport")
except Exception as e:
    w(f"[FAIL] create_viewport: {e}")
    with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
        f.write('\n'.join(log))
    sys.exit(1)

try:
    with dpg.theme(tag="test_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (30, 91, 158))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 152, 0))
    w("[OK] theme created")
except Exception as e:
    w(f"[FAIL] theme: {e}")
    with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
        f.write('\n'.join(log))
    sys.exit(1)

try:
    with dpg.window(tag="win", width=400, height=300):
        dpg.add_drawlist(width=300, height=200, tag="dl")
        dpg.draw_rectangle([0, 0], [300, 200], color=[60, 60, 60],
                          fill=[255, 255, 255], parent="dl", tag="rect")
        dpg.draw_text([120, 75], "255", size=24, color=[26, 26, 46],
                      parent="dl", tag="txt")
    w("[OK] window + drawlist elements")
except Exception as e:
    w(f"[FAIL] window/drawlist: {e}")
    traceback.print_exc()
    with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
        f.write('\n'.join(log))
    sys.exit(1)

try:
    dpg.bind_theme("test_theme")
    w("[OK] bind_theme")
except Exception as e:
    w(f"[FAIL] bind_theme: {e}")
    with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
        f.write('\n'.join(log))
    sys.exit(1)

try:
    dpg.setup_dearpygui()
    w(f"[OK] setup_dearpygui ok={dpg.is_viewport_ok()}")
except Exception as e:
    w(f"[FAIL] setup_dearpygui: {e}")
    with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
        f.write('\n'.join(log))
    sys.exit(1)

w("[DONE - no GUI available is expected on server]")
dpg.destroy_context()
with open('c:/coder/app/ca-analyzer/debug_dpg.log', 'w') as f:
    f.write('\n'.join(log))
