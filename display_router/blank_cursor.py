#!/usr/bin/env python3
"""Create a fully transparent Xcursor theme ('blank') in ~/.icons so the
kiosk shows no mouse pointer (the touchscreen registers as a mouse)."""
import os
import struct

CURSOR_NAMES = [
    'default', 'arrow', 'pointer', 'hand', 'hand1', 'hand2', 'text', 'xterm',
    'ibeam', 'crosshair', 'cross', 'wait', 'watch', 'progress', 'half-busy',
    'left_ptr_watch', 'help', 'question_arrow', 'move', 'all-scroll',
    'grab', 'grabbing', 'fleur', 'not-allowed', 'no-drop', 'copy', 'alias',
    'context-menu', 'cell', 'vertical-text', 'zoom-in', 'zoom-out',
    'col-resize', 'row-resize', 'e-resize', 'w-resize', 'n-resize', 's-resize',
    'ne-resize', 'nw-resize', 'se-resize', 'sw-resize', 'ew-resize',
    'ns-resize', 'nesw-resize', 'nwse-resize', 'sb_h_double_arrow',
    'sb_v_double_arrow', 'top_left_corner', 'top_right_corner',
    'bottom_left_corner', 'bottom_right_corner', 'top_side', 'bottom_side',
    'left_side', 'right_side',
]

# 1x1 fully transparent image chunk
chunk = struct.pack('<9I', 36, 0xfffd0002, 1, 1, 1, 1, 0, 0, 0) + struct.pack('<I', 0)
data = struct.pack('<4s3I', b'Xcur', 16, 0x10000, 1) + struct.pack('<3I', 0xfffd0002, 1, 28) + chunk

# Chromium looks up the theme "default" regardless of XCURSOR_THEME, so write both.
for theme in ('blank', 'default'):
    cursors_dir = os.path.expanduser(f'~/.icons/{theme}/cursors')
    os.makedirs(cursors_dir, exist_ok=True)
    with open(os.path.join(cursors_dir, 'left_ptr'), 'wb') as f:
        f.write(data)
    for name in CURSOR_NAMES:
        link = os.path.join(cursors_dir, name)
        if os.path.lexists(link):
            os.remove(link)
        os.symlink('left_ptr', link)
    print(f'Blank cursor theme written to {os.path.dirname(cursors_dir)}')
