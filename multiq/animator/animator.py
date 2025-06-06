"""
This file contains the implementation of the animator class, 
which allows multiple tiles to be shown side-by-side. It is 
based upon the animator in ZAC but has been extended and cleaned-up.
"""

from matplotlib.animation import FFMpegWriter, FuncAnimation
import matplotlib.pyplot as plt
import matplotlib
import bisect

from zac.ds.architecture import Architecture

from multiq.compiler.tile import Tile

# constants for animation
FPS = 60  # frames per second
INIT_FRM = int(FPS * 0.2)  # initial empty frames, 1/5 second now
PT_MICRON = 8  # scaling factor: points per micron
MUS_PER_FRM = 150 / FPS  # microseconds per frame
MUS_PER_FRM_SLOW = 7 / FPS  # in slow motion, i.e., Rydberg
# Padding between outer-most tile and graph axes
CANVAS_PADDING = 2
# Padding between each tile
TILE_PADDING = 1
# Padding around each entanglement zone
RYDBERG_PADDING = 3

# colors
RYDBERG_COLOR = 'b'
SLM_COLOR = 'g'
QUBIT_COLOR = 'k'
AOD_COLORS = ['r', 'c', 'm', 'y']  # max 4 aods so far
AOD_TRANS = 0.7


class TileAnimation:
    def __init__(self, code: dict, architecture: Architecture, ax):
        self.code = code
        self.inst_str = ""
        self.ax = ax
        self.architecture = architecture
        self.title = self.ax.set_title('')

        self.entanglement_rect_range = [
            (
                (
                    range_pair[0][0] - RYDBERG_PADDING,
                    range_pair[0][1] - RYDBERG_PADDING
                ),
                range_pair[1][0] - range_pair[0][0] + 2 * RYDBERG_PADDING,
                range_pair[1][1] - range_pair[0][1] + 2 * RYDBERG_PADDING,
            )
            for range_pair in self.architecture.rydberg_range
        ]

    def initial_frame(self):
        # find all slms
        slm_xs = []
        slm_ys = []
        for slm_id, slm_arr in self.architecture.dict_SLM.items():
            for r in range(slm_arr.n_r):
                for c in range(slm_arr.n_c):
                    x, y = self.architecture.exact_SLM_location(slm_id, r, c)
                    slm_xs.append(x)
                    slm_ys.append(y)

        # draw slms
        self.ax.scatter(
            slm_xs, slm_ys, marker='o', s=40, facecolor='none',
            edgecolor=SLM_COLOR
        )

        # initialize qubits
        self.qubit_xs = []
        self.qubit_ys = []
        for q in self.code["instructions"][0]["init_locs"]:
            x, y = self.architecture.exact_SLM_location(q[1], q[2], q[3])
            self.qubit_xs.append(x)
            self.qubit_ys.append(y)

        # draw qubits
        self.qubit_scat = self.ax.scatter(
            self.qubit_xs, self.qubit_ys, marker='.', c=QUBIT_COLOR)

        # initialize aod cols
        self.aod_col_plots = {
            aod_id: [
                self.ax.axvline(
                    0,
                    self.architecture.arch_range[0][1],
                    self.architecture.arch_range[1][1],
                    c=(0, 0, 0, 0),
                    ls='--'
                ) for _ in range(aod.n_c)
            ] for aod_id, aod in self.architecture.dict_AOD.items()
        }

        # initilize aod rows
        self.aod_row_plots = {
            aod_id: [
                self.ax.axhline(
                    0,
                    self.architecture.arch_range[0][0],
                    self.architecture.arch_range[1][0],
                    c=(0, 0, 0, 0),
                    ls='--'
                ) for _ in range(aod.n_r)
            ] for aod_id, aod in self.architecture.dict_AOD.items()
        }

        # initialize Rydberg zones
        self.entanglemet_rect = []
        for entangle_zone in self.entanglement_rect_range:
            rect = matplotlib.patches.Rectangle(
                entangle_zone[0],
                entangle_zone[1],
                entangle_zone[2],
                linewidth=1,
                edgecolor='none',
                facecolor=(0, 0, 1, 0.3)
            )
            self.ax.add_patch(rect)
            self.entanglemet_rect.append(rect)

        # initialize single qubit gates
        self.qubit_1qGate = []
        return

    def update(self, f: int):  # f is the frame
        true_frame = f - INIT_FRM  # consider the initial frozen frames

        # get which piecewise schedule f is in
        interval_ends = [interval[0] for interval in self.piecewise_schedule]
        index = bisect.bisect_right(interval_ends, true_frame)

        if index >= len(self.piecewise_schedule):
            # Our tile has finished but the animation continues for another tile
            return

        tmp = self.piecewise_schedule[index]
        # calculate true time of this frame: tmp[2] is the end time of this
        # period. tmp[0] is the end frame of this period. So we deduct the
        # remianing time from tmp[2]. The remaining time is calculated as the
        # product of remaining frames=tmp[0]-true_frame, and the sampling rate
        # which depends on whether this period is regular or slow motion.
        true_time = tmp[2] - (
            tmp[0] - true_frame) * (
                MUS_PER_FRM_SLOW if tmp[1] else MUS_PER_FRM)

        self.inst_str = ''
        # reset Rydberg zones to trivial
        for rect in self.entanglemet_rect:
            rect.set_width(0)
            rect.set_height(0)
        # reset 1qGate to trivial
        for gate in self.qubit_1qGate:
            gate.remove()
        self.qubit_1qGate = []
        # reset AOD color to trivial
        for aod_id, aod in self.architecture.dict_AOD.items():
            for r in range(aod.n_r):
                self.aod_row_plots[aod_id][r].set_color((0, 0, 0, 0))
            for c in range(aod.n_c):
                self.aod_col_plots[aod_id][c].set_color((0, 0, 0, 0))

        if f >= INIT_FRM:
            for inst in self.code["instructions"][1:]:
                if true_time >= inst["begin_time"] and true_time < inst["end_time"]:
                    if inst["type"] == "rydberg":
                        self.update_rydberg(inst)
                    elif inst["type"] == "rearrangeJob":
                        self.update_arrangement(true_time, inst)
                    elif inst['type'] == '1qGate':
                        self.update_1qGate(inst)
                    else:
                        raise ValueError(f"unknown inst type {inst['type']}")
        self.title.set_text(self.inst_str)
        return

    def update_rydberg(self, inst: dict):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {inst["begin_time"]:.2f}'
        self.entanglemet_rect[inst["zone_id"]].set_width(
            self.entanglement_rect_range[inst["zone_id"]][1]
        )
        self.entanglemet_rect[inst["zone_id"]].set_height(
            self.entanglement_rect_range[inst["zone_id"]][2]
        )

    def update_arrangement(self, time: float, inst: dict):
        self.inst_str += f' | {inst["id"]} {inst["type"]}'
        for detail_inst in inst["insts"]:
            if time >= detail_inst["begin_time"] and time < detail_inst["end_time"]:
                ratio = (time - detail_inst["begin_time"]) / (
                    detail_inst["end_time"] - detail_inst["begin_time"])
                if detail_inst["type"] == "activate":
                    return self.update_activate(
                        ratio, time, detail_inst, inst["aod_id"])
                elif detail_inst["type"] == "deactivate":
                    return self.update_deactivate(
                        ratio, time, detail_inst, inst["aod_id"])
                elif detail_inst["type"].startswith("move"):
                    return self.update_move(
                        ratio,
                        time,
                        detail_inst,
                        zip(
                            detail_inst["begin_coord"],
                            detail_inst["end_coord"],
                        ),
                        inst["aod_id"],
                    )

    def update_activate(self, ratio: float, time: float, inst: dict, aod_id: int):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {time:.2f}'
        for col_id, col_x in zip(inst["col_id"], inst["col_x"]):
            self.aod_col_plots[aod_id][col_id].set_xdata((col_x, ))
            self.aod_col_plots[aod_id][col_id].set_color(
                # (self.AOD_COLORS[aod_id], ratio*self.AOD_TRANS) # !
                (1, 0, 0, ratio * AOD_TRANS)
            )
        for row_id, row_y in zip(inst["row_id"], inst["row_y"]):
            self.aod_row_plots[aod_id][row_id].set_ydata((row_y, ))
            self.aod_row_plots[aod_id][row_id].set_color(
                # (self.AOD_COLORS[aod_id], ratio*self.AOD_TRANS) # !
                (1, 0, 0, ratio * AOD_TRANS)
            )

    def update_deactivate(self, ratio: float, time: float, inst: dict, aod_id: int):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {time:.2f}'
        for col_id in inst["col_id"]:
            self.aod_col_plots[aod_id][col_id].set_color(
                # (self.AOD_COLORS[aod_id], (1-ratio)*self.AOD_TRANS) # !
                (1, 0, 0, (1-ratio)*AOD_TRANS)
            )
        for row_id in inst["row_id"]:
            self.aod_row_plots[aod_id][row_id].set_color(
                # (self.AOD_COLORS[aod_id], (1-ratio)*self.AOD_TRANS) # !
                (1, 0, 0, (1-ratio)*AOD_TRANS)
            )

    def update_move(self, ratio: float, time: float, inst: dict, qubit_coord, aod_id: int):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {time:.2f}'

        # smoothstep
        def interpolate(r: float, begin: int, end: int):
            D = end - begin
            return begin + 3*D*(r**2) - 2*D*(r**3)

        # update qubit
        for begin_coords_row, end_coords_row in qubit_coord:
            for begin_coords, end_coords in zip(
                    begin_coords_row, end_coords_row):
                q_id = begin_coords["id"]
                self.qubit_xs[q_id] = interpolate(
                    ratio, begin_coords["x"], end_coords["x"])
                self.qubit_ys[q_id] = interpolate(
                    ratio, begin_coords["y"], end_coords["y"])
                self.qubit_scat.set_offsets(
                    list(zip(self.qubit_xs, self.qubit_ys)))

        # update AOD
        for row_id, row_begin_y, row_end_y in zip(
                inst["row_id"], inst["row_y_begin"], inst["row_y_end"]):
            self.aod_row_plots[aod_id][row_id].set_ydata(
                (interpolate(ratio, row_begin_y, row_end_y), ))
            self.aod_row_plots[aod_id][row_id].set_color(
                AOD_COLORS[aod_id]
            )
        for col_id, col_begin_x, col_end_x in zip(
                inst["col_id"], inst["col_x_begin"], inst["col_x_end"]):
            self.aod_col_plots[aod_id][col_id].set_xdata(
                (interpolate(ratio, col_begin_x, col_end_x), ))
            self.aod_col_plots[aod_id][col_id].set_color(
                AOD_COLORS[aod_id]
            )

    def update_1qGate(self, inst: dict):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {inst["end_time"]:.2f}'

        for g in inst['gates']:
            q = g['q']
            x = self.qubit_xs[q]
            y = self.qubit_ys[q]
            self.qubit_1qGate.append(self.ax.scatter(
                x, y, s=300, color=(0, 1, 0, 0.5)))

    def create_schedule(self):
        """
        each frame is a sample on the time axis. There are two sampling rates
        one is regular, one is slow motion. The latter is used when Rydberg
        is happening because Rydberg is so fast that it won't appear in the
        video is using the regular sampling rate.

        The time axis looks like this:

        |_____________|...|_______________|...|_________|...|__________|

        where each | will be an entry in self.piecewise_schedule. The _ stands
        for regular period, the . stands for slow motion periods. 

        In piecewise_schedule consists of 3-tuples. the first number is the
        frame at the | The second number is whether the period before the | is
        slow motion (1) or not (0). The third number is the real time at the | 
        """

        self.piecewise_schedule = [(0, 0, 0), ]  # add the first trivial entry
        last_end_time = 0
        for inst in self.code["instructions"]:
            if inst["type"] == "rydberg":

                # add the entry corresponding to the regular period before
                last_end_frame = self.piecewise_schedule[-1][0]
                self.piecewise_schedule.append(
                    (
                        last_end_frame + round(
                            (
                                inst["begin_time"] - last_end_time
                            ) / MUS_PER_FRM),
                        0,
                        inst["begin_time"]
                    )
                )

                # add the entry corresponding to the slow period for this inst
                last_end_frame = self.piecewise_schedule[-1][0]
                self.piecewise_schedule.append(
                    (
                        last_end_frame + round(
                            (
                                inst["end_time"] - inst["begin_time"]
                            ) / MUS_PER_FRM_SLOW),
                        1,
                        inst["end_time"]
                    )
                )
                last_end_time = inst["end_time"]

        # add an entry of the left over runtime after the last rydberg
        if self.code["runtime"] > last_end_time:
            last_end_frame = self.piecewise_schedule[-1][0]
            self.piecewise_schedule.append(
                (
                    last_end_frame + round(
                        (
                            self.code["runtime"] - last_end_time
                        ) / MUS_PER_FRM),
                    0,
                    self.code["runtime"]
                )
            )
        return self.piecewise_schedule[-1][0]


class Animator():
    def __init__(self, architecture: Architecture, grid_rows, grid_cols):
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.architecture = architecture
        matplotlib.use('Agg')

    def multi_animate(
            self,
            tiles: list[list[Tile | None]],
            output: str,
            scaling_factor: int = PT_MICRON,
            font_size: int = 10,
            ffmpeg: str = 'ffmpeg'):

        matplotlib.rcParams.update({'font.size': font_size})
        plt.rcParams['animation.ffmpeg_path'] = ffmpeg

        self.fig, self.axes = self.setup_canvas(scaling_factor)
        self.inst_str = ''

        # Create the animation classes for the tiles
        self.anims: dict[tuple[int,int], TileAnimation | None] = {(r,c) : None for r in range(self.grid_rows) for c in range(self.grid_cols)}
        for r, row in enumerate(tiles):
            for c, tile in enumerate(row):
                if tile is not None:
                    self.anims[(r,c)] = TileAnimation(tile.result_json, self.architecture, self.axes[r][c])


        # self.tiles = [TileAnimation(
        #    tiles_codes[i], self.architecture, self.axes[i]) for i in range(self.n_tiles)]

        # Use longest tile anim as frame count
        schedules = {(r,c): t.create_schedule() if t is not None else 0 for (r,c), t in self.anims.items()}
        n_frames = max(schedules.values())

        anim = FuncAnimation(
            self.fig,
            self.update,
            init_func=self.initial_frame,
            frames=INIT_FRM + n_frames,
        )
        anim.save(output, writer=FFMpegWriter(FPS))

    def setup_canvas(self, scaling_factor: int):
        """set up various objects before actually drawing."""
        # unit conversion factor from um to inches for figsize
        # scaling_factor is PT_MICRON (points per micron)
        # plt.rcParams['figure.dpi'] is points per inch
        # inches_per_micron = (points / micron) / (points / inch) = inches / micron
        inches_per_micron = scaling_factor / plt.rcParams['figure.dpi']

        tile_native_width_um = (self.architecture.arch_range[1][0] -
                                self.architecture.arch_range[0][0])
        tile_native_height_um = (self.architecture.arch_range[1][1] -
                                 self.architecture.arch_range[0][1])

        # Effective width/height of one subplot's content area in microns,
        # including the CANVAS_PADDING that expands its xlim/ylim.
        subplot_content_width_um = tile_native_width_um + 2 * CANVAS_PADDING
        subplot_content_height_um = tile_native_height_um + 2 * CANVAS_PADDING

        # Total figure size in inches.
        # This accounts for all tiles and the TILE_PADDING space between them.
        total_figure_width_inches = (self.grid_cols * subplot_content_width_um +
                                     max(0, self.grid_cols - 1) * TILE_PADDING) * inches_per_micron
        total_figure_height_inches = (self.grid_rows * subplot_content_height_um +
                                      max(0, self.grid_rows - 1) * TILE_PADDING) * inches_per_micron

        fig, axes = plt.subplots(
            self.grid_rows, self.grid_cols,
            figsize=(total_figure_width_inches, total_figure_height_inches),
            squeeze=False  # Ensures axes is always a 2D numpy array
        )

        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                ax = axes[r][c]
                # Set the limits for each subplot based on architecture range and canvas padding
                ax.set_xlim([
                    self.architecture.arch_range[0][0] - CANVAS_PADDING,
                    self.architecture.arch_range[1][0] + CANVAS_PADDING
                ])
                ax.set_ylim([
                    self.architecture.arch_range[0][1] - CANVAS_PADDING,
                    self.architecture.arch_range[1][1] + CANVAS_PADDING
                ])

                # Optional: Remove ticks and labels for a cleaner look
                ax.set_xticks([])
                ax.set_yticks([])
                # ax.axis('off') # This would also remove the title set by TileAnimation's update
                ax.set_aspect('equal', adjustable='box') # Ensure consistent scaling

        plt.tight_layout()

        return fig, axes

    # Initial frame over all subplots
    def initial_frame(self):
        for t in self.anims.values():
            if t is not None:
                t.initial_frame()

    def update(self, f: int):  # f is the frame
        for t in self.anims.values():
                if t is not None:
                    t.update(f)
