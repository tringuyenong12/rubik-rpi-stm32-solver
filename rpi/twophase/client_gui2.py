# ################ A simple graphical interface which communicates with the server #####################################

# While client_gui only allows to set the facelets with the mouse, this file (client_gui2) also takes input from the
# webcam and includes sliders for some opencv parameters.

import sys
from pathlib import Path
from tkinter import *
from queue import Queue
from threading import Thread
from collections import Counter

# Ensure parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import twophase.cubie as cubie
import twophase.vision_params as vision_params
from twophase import vision2
from rubik_robot.vision.face_scanner import COLORS, scanner
from rubik_robot.vision.solve_guide import cube_faces, guide, prepare_cube, request_solution


# ################################## some global variables and constants ###############################################
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = '8080'
width = 60  # width of a facelet in pixels
facelet_id = [[[0 for col in range(3)] for row in range(3)] for fc in range(6)]
colorpick_id = [0 for i in range(6)]
curcol = None
t = ("U", "R", "F", "D", "L", "B")
cols = ("yellow", "green", "red", "white", "blue", "orange")
########################################################################################################################

# ################################################ Diverse functions ###################################################


def show_text(txt):
    """Display messages."""
    print(txt)
    display.insert(INSERT, txt)
    root.update_idletasks()


def create_facelet_rects(a):
    """Initialize the facelet grid on the canvas."""
    offset = ((1, 0), (2, 1), (1, 1), (1, 2), (0, 1), (3, 1))
    for f in range(6):
        for row in range(3):
            y = 10 + offset[f][1] * 3 * a + row * a
            for col in range(3):
                x = 10 + offset[f][0] * 3 * a + col * a
                facelet_id[f][row][col] = canvas.create_rectangle(x, y, x + a, y + a, fill="grey")
                if row == 1 and col == 1:
                    canvas.create_text(x + width // 2, y + width // 2, font=("", 14), text=t[f], state=DISABLED)
    for f in range(6):
        canvas.itemconfig(facelet_id[f][1][1], fill=cols[f])


def create_colorpick_rects(a):
    """Initialize the "paintbox" on the canvas."""
    global curcol
    global cols
    for i in range(6):
        x = (i % 3) * (a + 5) + 7 * a
        y = (i // 3) * (a + 5) + 7 * a
        colorpick_id[i] = canvas.create_rectangle(x, y, x + a, y + a, fill=cols[i])
        canvas.itemconfig(colorpick_id[0], width=4)
        curcol = cols[0]


def get_definition_string():
    """Generate the cube definition string from the facelet colors."""
    color_to_facelet = {}
    for i in range(6):
        color_to_facelet.update({canvas.itemcget(facelet_id[i][1][1], "fill"): t[i]})
    s = ''
    for f in range(6):
        for row in range(3):
            for col in range(3):
                s += color_to_facelet[canvas.itemcget(facelet_id[f][row][col], "fill")]
    return s
########################################################################################################################

# ############################### Solve the displayed cube with a local or remote server ###############################


solve_results = Queue()
solve_generation = 0
solving = False
last_auto_revision = None


def cancel_guidance():
    """Input: none. Output: invalidate pending requests and stop the camera guide."""
    global solve_generation, solving, last_auto_revision
    solve_generation += 1
    solving = False
    last_auto_revision = scanner.snapshot()['revision']
    guide.reset()


def solve_in_background(generation, revision, faces, samples, host, port):
    """Input: captured snapshot/endpoint. Output: a result queued for the Tk thread."""
    try:
        cube, _, centers, note = prepare_cube(faces, samples)
        solution = request_solution(host, port, cube)
        result = (cube, centers, note, solution)
        solve_results.put((generation, revision, result, None))
    except Exception as error:
        solve_results.put((generation, revision, None, str(error)))


def solve():
    """Input: editor cube/server address. Output: asynchronously start verified guidance."""
    global solving, last_auto_revision
    if solving:
        return
    try:
        definition = get_definition_string()
        faces = cube_faces(definition)
        host = txt_host.get(1.0, END).strip()
        port = int(txt_port.get(1.0, END))
    except (KeyError, ValueError):
        show_text('Complete all six faces and check the server port.\n')
        return
    state = scanner.snapshot()
    samples = state['hsv_faces'] if faces == state['faces'] else None
    cancel_guidance()
    pause_scan()
    solving = True
    last_auto_revision = state['revision']
    display.delete(1.0, END)
    show_text('Checking 54 colors and face directions, then requesting the TCP solver...\n')
    Thread(target=solve_in_background,
           args=(solve_generation, state['revision'], faces, samples, host, port), daemon=True).start()


def receive_solution():
    """Input: worker queue. Output: start current results and discard stale replies."""
    global solving
    while not solve_results.empty():
        generation, revision, result, error = solve_results.get_nowait()
        if generation != solve_generation:
            continue
        if revision != scanner.snapshot()['revision']:
            solving = False
            continue
        solving = False
        if error:
            guide.fail(error)
            show_text(f'Check scan: {error}\nUse Rescan shown face or correct the editor, then Solve.\n')
            continue
        cube, centers, note, solution = result
        try:
            guide.begin(cube, solution, centers)
            show_text(f'{note}\n{cube}\nSolution: {solution or "<already solved>"}\n')
        except ValueError as failure:
            guide.fail(failure)
            show_text(f'Cannot start guide: {failure}\n')

########################################################################################################################

# ################################# Functions to change the facelet colors #############################################


def clean():
    """Restore the cube to a clean cube."""
    global last_saved
    cancel_guidance()
    display.delete(1.0, END)
    scanner.reset()
    last_saved = {}
    pause_scan()
    for f in range(6):
        for row in range(3):
            for col in range(3):
                canvas.itemconfig(facelet_id[f][row][col], fill=canvas.itemcget(facelet_id[f][1][1], "fill"), outline='black', width=1)


def empty():
    """Remove the facelet colors except the center facelets colors."""
    global last_saved
    cancel_guidance()
    display.delete(1.0, END)
    orientation_status.set('Reference: yellow U, red F, green R. Rotate the whole cube while scanning.')
    scanner.reset()
    last_saved = {}
    auto_scan.set(True)
    vision_params.cube_col.clear()
    vision_params.cube_hsv.clear()
    for f in range(6):
        for row in range(3):
            for col in range(3):
                canvas.itemconfig(facelet_id[f][row][col], outline='black', width=1)
                if row != 1 or col != 1:
                    canvas.itemconfig(facelet_id[f][row][col], fill="grey")


def random():
    """Generate a random cube and sets the corresponding facelet colors."""
    global last_saved
    cancel_guidance()
    display.delete(1.0, END)
    scanner.reset()
    last_saved = {}
    pause_scan()
    cc = cubie.CubieCube()
    cc.randomize()
    fc = cc.to_facelet_cube()
    idx = 0
    for f in range(6):
        for row in range(3):
            for col in range(3):
                canvas.itemconfig(facelet_id[f][row][col], fill=cols[fc.f[idx]], outline='black', width=1)
                idx += 1
########################################################################################################################

# ################################### Edit the facelet colors ##########################################################


def click(_event):
    """Define how to react on left mouse clicks"""
    global curcol, last_auto_revision
    idlist = canvas.find_withtag("current")
    if len(idlist) > 0:
        if idlist[0] in colorpick_id:
            curcol = canvas.itemcget("current", "fill")
            for i in range(6):
                canvas.itemconfig(colorpick_id[i], width=1)
            canvas.itemconfig("current", width=5)
        else:
            if solving or guide.snapshot()['phase'] not in ('idle', 'solved'):
                return
            for face_index in range(6):
                for sticker in range(9):
                    if idlist[0] == facelet_id[face_index][sticker // 3][sticker % 3] and sticker != 4:
                        cancel_guidance()
                        pause_scan()
                        canvas.itemconfig("current", fill=curcol)
                        scanner.edit(cols[face_index], sticker, curcol)
                        last_auto_revision = scanner.snapshot()['revision']
########################################################################################################################


# ######################################### functions to set the slider values #########################################
def set_rgb_L(val):
    vision_params.rgb_L = int(val)


def set_orange_L(val):
    vision_params.orange_L = int(val)


def set_orange_H(val):
    vision_params.orange_H = int(val)


def set_yellow_H(val):
    vision_params.yellow_H = int(val)


def set_green_H(val):
    vision_params.green_H = int(val)


def set_blue_H(val):
    vision_params.blue_H = int(val)


def set_sat_W(val):
    vision_params.sat_W = int(val)


def set_val_W(val):
    vision_params.val_W = int(val)


def set_sigma_C(val):
    vision_params.sigma_C = int(val)


def set_delta_C(val):
    vision_params.delta_C = int(val)


def transfer():
    """Transfer the facelet colors detected by the opencv vision to the GUI editor."""
    cancel_guidance()
    scanner.save_current()
    refresh_scan()


def pause_scan():
    """Input: none. Output: pause acquisition while editing or solving a cube."""
    auto_scan.set(False)
    scanner.set_enabled(False)


def toggle_scan():
    """Input: checkbox value. Output: enable or pause automatic face capture."""
    if auto_scan.get():
        cancel_guidance()
    scanner.set_enabled(auto_scan.get())


def rescan_current():
    """Input: current camera face. Output: clear that saved face and resume capture."""
    state = scanner.snapshot()
    if state['current']:
        cancel_guidance()
        scanner.forget(state['current'][4])
        auto_scan.set(True)
        scanner.set_enabled(True)


def rotate_current():
    """Input: current camera face. Output: rotate its saved grid clockwise."""
    state = scanner.snapshot()
    if state['current']:
        cancel_guidance()
        scanner.rotate(state['current'][4])


last_saved = {}


def refresh_scan():
    """Input: scanner snapshot. Output: update Tk widgets on the GUI thread."""
    global last_saved
    state = scanner.snapshot()
    guidance = guide.snapshot()
    faces = cube_faces(guidance['cube']) if guidance['cube'] else state['faces']
    if guidance['phase'] == 'solved' and state['faces'] != faces:
        scanner.set_verified_faces(faces)
        state = scanner.snapshot()
    for center in COLORS:
        face = faces.get(center)
        if face == last_saved.get(center):
            continue
        index = cols.index(center)
        values = face or ('grey',) * 4 + (center,) + ('grey',) * 4
        for sticker, color in enumerate(values):
            canvas.itemconfig(facelet_id[index][sticker // 3][sticker % 3], fill=color)
        if face:
            vision_params.cube_col[center] = [list(face[row:row+3]) for row in (0, 3, 6)]
        else:
            vision_params.cube_col.pop(center, None)
    last_saved = faces
    counts = Counter(color for values in faces.values() for color in values)
    for face_index, center in enumerate(COLORS):
        for sticker, color in enumerate(faces.get(center, ())):
            conflict = counts[color] > 9 and guidance['phase'] in ('idle', 'error')
            canvas.itemconfig(facelet_id[face_index][sticker // 3][sticker % 3],
                              outline='darkorange' if conflict else 'black', width=3 if conflict else 1)
    text = vision2.camera_error or f"{len(state['faces'])}/6 - {state['message']}"
    if solving:
        text = 'Checking scan and waiting for the TCP solver...'
    elif guidance['phase'] != 'idle':
        text = guidance['message']
    if vision2.camera_error:
        text = vision2.camera_error
    scan_status.set(text)
    active = guidance['phase'] in ('align', 'turn', 'verify')
    bsolve.config(state=DISABLED if solving or active else NORMAL)
    for button in (btransfer, bclean, brandom, rescan_button, rotate_button, auto_scan_button):
        button.config(state=DISABLED if solving or active else NORMAL)
    if active:
        orientation_status.set('One arrow: turn one layer 90 degrees. Three arrows: rotate the whole cube.')
    elif state['current']:
        center = state['current'][4]
        top = {'yellow': 'orange', 'white': 'red', 'red': 'yellow',
               'green': 'yellow', 'blue': 'yellow', 'orange': 'yellow'}[center]
        orientation_status.set(f"Showing {center}: the adjacent {top} face must be at the top edge.")


def poll_scan():
    """Input: none. Output: refresh scan widgets every 100 milliseconds."""
    receive_solution()
    refresh_scan()
    state = scanner.snapshot()
    if auto_guide.get() and len(state['faces']) == 6 and not solving and guide.snapshot()['phase'] == 'idle':
        if state['revision'] != last_auto_revision:
            solve()
    root.after(100, poll_scan)


def close_client():
    """Input: close-window event. Output: stop camera acquisition and close Tk."""
    cancel_guidance()
    vision2.camera_stop.set()
    root.destroy()

# ######################################################################################################################

#  ###################################### Generate and display the TK_widgets ##########################################


root = Tk()
root.wm_title("Solver Client")
canvas = Canvas(root, width=12 * width + 20, height=9 * width + 20)
canvas.pack()
bsolve = Button(text="Solve", height=2, width=10, relief=RAISED, command=solve)
bsolve_window = canvas.create_window(10 + 10.5 * width, 10 + 6.5 * width, anchor=NW, window=bsolve)
bclean = Button(text="Clean", height=1, width=10, relief=RAISED, command=clean)
bclean_window = canvas.create_window(10 + 10.5 * width, 10 + 7.5 * width, anchor=NW, window=bclean)
bempty = Button(text="Empty", height=1, width=10, relief=RAISED, command=empty)
bempty_window = canvas.create_window(10 + 10.5 * width, 10 + 8 * width, anchor=NW, window=bempty)
brandom = Button(text="Random", height=1, width=10, relief=RAISED, command=random)
brandom_window = canvas.create_window(10 + 10.5 * width, 10 + 8.5 * width, anchor=NW, window=brandom)
display = Text(height=7, width=39)
text_window = canvas.create_window(10 + 6.5 * width, 10 + .5 * width, anchor=NW, window=display)
hp = Label(text='    Hostname and Port')
hp_window = canvas.create_window(10 + 0 * width, 10 + 0.6 * width, anchor=NW, window=hp)
txt_host = Text(height=1, width=20)
txt_host_window = canvas.create_window(10 + 0 * width, 10 + 1 * width, anchor=NW, window=txt_host)
txt_host.insert(INSERT, DEFAULT_HOST)
txt_port = Text(height=1, width=20)
txt_port_window = canvas.create_window(10 + 0 * width, 10 + 1.5 * width, anchor=NW, window=txt_port)
txt_port.insert(INSERT, DEFAULT_PORT)
canvas.bind("<Button-1>", click)
create_facelet_rects(width)
create_colorpick_rects(width)

s_orange_L = Scale(root, from_=1, to=14, length=width * 1.4, showvalue=0, label='red-orange', orient=HORIZONTAL,
                   command=set_orange_L)
canvas.create_window(10, 12 + 6.0 * width, anchor=NW, window=s_orange_L)
s_orange_L.set(vision_params.orange_L)

s_orange_H = Scale(root, from_=8, to=40, length=width * 1.4, showvalue=0, label='orange-yellow', orient=HORIZONTAL,
                   command=set_orange_H)
canvas.create_window(10, 12 + 6.6 * width, anchor=NW, window=s_orange_H)
s_orange_H.set(vision_params.orange_H)

s_yellow_H = Scale(root, from_=31, to=80, length=width * 1.4, showvalue=0, label='yellow-green', orient=HORIZONTAL,
                   command=set_yellow_H)
canvas.create_window(10, 12 + 7.2 * width, anchor=NW, window=s_yellow_H)
s_yellow_H.set(vision_params.yellow_H)

s_green_H = Scale(root, from_=70, to=120, length=width * 1.4, showvalue=0, label='green-blue', orient=HORIZONTAL,
                  command=set_green_H)
canvas.create_window(10, 12 + 7.8 * width, anchor=NW, window=s_green_H)
s_green_H.set(vision_params.green_H)

s_blue_H = Scale(root, from_=120, to=180, length=width * 1.4, showvalue=0, label='blue-red', orient=HORIZONTAL,
                 command=set_blue_H)
canvas.create_window(10, 12 + 8.4 * width, anchor=NW, window=s_blue_H)
s_blue_H.set(vision_params.blue_H)

s_rgb_L = Scale(root, from_=0, to=140, length=width * 1.4, showvalue=0, label='black-filter', orient=HORIZONTAL,
                command=set_rgb_L)
canvas.create_window(10 + width * 1.5, 12 + 6 * width, anchor=NW, window=s_rgb_L)
s_rgb_L.set(vision_params.rgb_L)

s_sat_W = Scale(root, from_=120, to=0, length=width * 1.4, showvalue=0, label='white-filter s', orient=HORIZONTAL,
                command=set_sat_W)
canvas.create_window(10 + width * 1.5, 12 + 6.6 * width, anchor=NW, window=s_sat_W)
s_sat_W.set(vision_params.sat_W)

s_val_W = Scale(root, from_=80, to=255, length=width * 1.4, showvalue=0, label='white-filter v', orient=HORIZONTAL,
                command=set_val_W)
canvas.create_window(10 + width * 1.5, 12 + 7.2 * width, anchor=NW, window=s_val_W)
s_val_W.set(vision_params.val_W)

s_sigma_C = Scale(root, from_=30, to=0, length=width * 1.4, showvalue=0, label='color-filter \u03c3', orient=HORIZONTAL,
                  command=set_sigma_C)
canvas.create_window(10 + width * 1.5, 12 + 7.8 * width, anchor=NW, window=s_sigma_C)
s_sigma_C.set(vision_params.sigma_C)

s_delta_C = Scale(root, from_=10, to=0, length=width * 1.4, showvalue=0, label='color-filter \u03b4', orient=HORIZONTAL,
                  command=set_delta_C)
canvas.create_window(10 + width * 1.5, 12 + 8.4 * width, anchor=NW, window=s_delta_C)
s_delta_C.set(vision_params.delta_C)

btransfer = Button(text="Webcam import", height=2, width=13, relief=RAISED, command=transfer)
canvas.create_window(10 + 0.5 * width, 10 + 2.1 * width, anchor=NW, window=btransfer)

scan_controls = Frame(root)
scan_controls.pack(fill=X, padx=10, pady=4)
auto_scan = BooleanVar(value=True)
auto_scan_button = Checkbutton(scan_controls, text="Auto scan", variable=auto_scan, command=toggle_scan)
auto_scan_button.pack(side=LEFT)
rescan_button = Button(scan_controls, text="Rescan shown face", command=rescan_current)
rescan_button.pack(side=LEFT, padx=4)
rotate_button = Button(scan_controls, text="Rotate saved face 90", command=rotate_current)
rotate_button.pack(side=LEFT, padx=4)
Button(scan_controls, text="New scan", command=empty).pack(side=LEFT, padx=4)
auto_guide = BooleanVar(value=True)
Checkbutton(scan_controls, text="Auto guide after 6 faces", variable=auto_guide).pack(side=LEFT, padx=4)
scan_status = StringVar(value="Show a face and hold still")
Label(root, textvariable=scan_status, wraplength=720).pack(padx=10, pady=3)
orientation_status = StringVar(value="Reference: yellow U, red F, green R. Rotate the whole cube while scanning.")
Label(root, textvariable=orientation_status, wraplength=720).pack(padx=10, pady=(0, 8))
root.protocol("WM_DELETE_WINDOW", close_client)
root.after(100, poll_scan)

root.mainloop()
########################################################################################################################
