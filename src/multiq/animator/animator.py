"""Multi-tile animator, based on the animator in ZAC."""

import logging

from matplotlib.animation import FFMpegWriter, FuncAnimation
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.gridspec import GridSpec
import bisect

from zac.ds.architecture import Architecture

from multiq.compiler.tile import Tile
from multiq.configuration import MultiQConfig

FPS = 60
INIT_FRM = int(FPS * 0.2)
PT_MICRON = 8  # scaling factor: points per micron
MUS_PER_FRM = 150 / FPS  # microseconds per frame
MUS_PER_FRM_SLOW = 7 / FPS  # slow motion used during Rydberg gates
CANVAS_PADDING = 0.5
TILE_PADDING = 0.1
RYDBERG_PADDING = 3

RYDBERG_COLOR = 'b'
SLM_COLOR = 'g'
QUBIT_COLOR = 'k'
AOD_COLORS = ['r', 'c', 'm', 'y']
AOD_TRANS = 0.7

logger = logging.getLogger("multiq")


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
        slm_xs = []
        slm_ys = []
        for slm_id, slm_arr in self.architecture.dict_SLM.items():
            for r in range(slm_arr.n_r):
                for c in range(slm_arr.n_c):
                    x, y = self.architecture.exact_SLM_location(slm_id, r, c)
                    slm_xs.append(x)
                    slm_ys.append(y)

        self.ax.scatter(
            slm_xs, slm_ys, marker='o', s=40, facecolor='none',
            edgecolor=SLM_COLOR
        )

        self.qubit_xs = []
        self.qubit_ys = []
        for q in self.code["instructions"][0]["init_locs"]:
            x, y = self.architecture.exact_SLM_location(q[1], q[2], q[3])
            self.qubit_xs.append(x)
            self.qubit_ys.append(y)

        self.qubit_scat = self.ax.scatter(
            self.qubit_xs, self.qubit_ys, marker='.', c=QUBIT_COLOR)

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

        self.qubit_1qGate = []
        self.row_1qGate_rects = []

        return

    def update(self, f: int):
        true_frame = f - INIT_FRM  # skip the initial frozen frames

        interval_ends = [interval[0] for interval in self.piecewise_schedule]
        index = bisect.bisect_right(interval_ends, true_frame)

        if index >= len(self.piecewise_schedule):
            return

        tmp = self.piecewise_schedule[index]
        # Remaining frames times the frame duration, subtracted from the end time of the period.
        true_time = tmp[2] - (
            tmp[0] - true_frame) * (
                MUS_PER_FRM_SLOW if tmp[1] else MUS_PER_FRM)

        self.inst_str = ''
        for rect in self.entanglemet_rect:
            rect.set_width(0)
            rect.set_height(0)
        for gate in self.qubit_1qGate:
            gate.remove()
        for rect in self.row_1qGate_rects:
            rect.remove()
        self.row_1qGate_rects = []
        self.qubit_1qGate = []
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
                    elif inst["type"] == "row1qGate":
                        self.update_row1qGate(inst)
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
                (1, 0, 0, ratio * AOD_TRANS)
            )
        for row_id, row_y in zip(inst["row_id"], inst["row_y"]):
            self.aod_row_plots[aod_id][row_id].set_ydata((row_y, ))
            self.aod_row_plots[aod_id][row_id].set_color(
                (1, 0, 0, ratio * AOD_TRANS)
            )

    def update_deactivate(self, ratio: float, time: float, inst: dict, aod_id: int):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {time:.2f}'
        for col_id in inst["col_id"]:
            self.aod_col_plots[aod_id][col_id].set_color(
                (1, 0, 0, (1-ratio)*AOD_TRANS)
            )
        for row_id in inst["row_id"]:
            self.aod_row_plots[aod_id][row_id].set_color(
                (1, 0, 0, (1-ratio)*AOD_TRANS)
            )

    def update_move(self, ratio: float, time: float, inst: dict, qubit_coord, aod_id: int):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {time:.2f}'

        # smoothstep
        def interpolate(r: float, begin: int, end: int):
            D = end - begin
            return begin + 3*D*(r**2) - 2*D*(r**3)

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

    def update_row1qGate(self, inst: dict):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {inst["end_time"]:.2f}'
        row_index = inst["row"]
        if not inst["locs"]:
            return

        first_loc = inst["locs"][0] # (q_id, slm_id, r, c)
        slm_id_for_y = first_loc[1]
        col_id_for_y = first_loc[3]  # assumes the SLM has at least this many columns

        y_centre = None
        row_height = 10
        try:
            y_centre = self.architecture.exact_SLM_location(slm_id_for_y, row_index, col_id_for_y)[1]
            if slm_id_for_y in self.architecture.dict_SLM:
                slm_array = self.architecture.dict_SLM[slm_id_for_y]
                if slm_array.n_r > row_index + 1:
                     y_center_next_row = self.architecture.exact_SLM_location(slm_id_for_y, row_index + 1, col_id_for_y)[1]
                     row_height = abs(y_center_next_row - y_centre)
                elif row_index > 0 and slm_array.n_r > row_index - 1:
                     y_center_prev_row = self.architecture.exact_SLM_location(slm_id_for_y, row_index - 1, col_id_for_y)[1]
                     row_height = abs(y_centre - y_center_prev_row)
        except (IndexError, KeyError):
            logger.warning(f"SLM locations not accurate in animator. Can't draw row 1q gate pulse.")

        if y_centre is None:
             return

        rect_x = self.architecture.arch_range[0][0]
        rect_y = y_centre - row_height / 2
        rect_width = self.architecture.arch_range[1][0] - self.architecture.arch_range[0][0]
        rect_height = row_height

        rect = matplotlib.patches.Rectangle(
            (rect_x, rect_y),
            rect_width,
            rect_height,
            linewidth=0,
            edgecolor='none',
            facecolor=(0, 1, 0, 0.3)
        )
        self.ax.add_patch(rect)
        self.row_1qGate_rects.append(rect)
 

    def update_1qGate(self, inst: dict):
        self.inst_str += f' | {inst["id"]} {inst["type"]} \n elapsed time: {inst["end_time"]:.2f}'

        for g in inst['gates']:
            q = g['q']
            x = self.qubit_xs[q]
            y = self.qubit_ys[q]
            self.qubit_1qGate.append(self.ax.scatter(
                x, y, s=300, color=(0, 1, 0, 0.5)))

    def create_schedule(self):
        """Build a piecewise frame schedule that uses slow motion during Rydberg gates."""

        self.piecewise_schedule = [(0, 0, 0), ]
        last_end_time = 0
        for inst in self.code["instructions"]:
            if inst["type"] == "rydberg":

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


class Animator:
    def __init__(self, config: MultiQConfig, grid_rows, grid_cols):
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.config = config

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

        self.fig = self.setup_canvas(
            tiles, scaling_factor, inches_per_micron_calc=PT_MICRON / plt.rcParams['figure.dpi'])
        self.inst_str = ''

        self.anims: dict[tuple[int, int], TileAnimation | None] = {
            (r, c): None for r in range(self.grid_rows) for c in range(self.grid_cols)}
        for r, row in enumerate(tiles):
            for c, tile in enumerate(row):
                if tile:
                    self.anims[(r, c)] = TileAnimation(
                        tile.result_json, tile.architecture, self.axes_map[(r, c)])

        schedules_durations = {}
        for (r_root, c_root), anim_instance in self.anims.items():
            if anim_instance is not None:
                schedules_durations[(r_root, c_root)
                                    ] = anim_instance.create_schedule()

        n_frames = 0
        if schedules_durations:
            n_frames = max(schedules_durations.values())

        anim = FuncAnimation(
            self.fig,
            self.update,
            init_func=self.initial_frame,
            frames=INIT_FRM + n_frames,
        )
        anim.save(f'{output}/animation.mp4', writer=FFMpegWriter(FPS))
        exit(0)

    def setup_canvas(self, tiles: list[list[Tile | None]], scaling_factor: int, inches_per_micron_calc: float):
        """Set up the figure and one subplot per tile."""

        max_phys_width_per_grid_cell = 0
        max_phys_height_per_grid_cell = 0
        default_arch_for_empty = None

        for r_idx in range(self.grid_rows):
            for c_idx in range(self.grid_cols):
                tile = tiles[r_idx][c_idx]
                if tile:
                    if not default_arch_for_empty:
                        default_arch_for_empty = tile.architecture
                    phys_w = tile.architecture.arch_range[1][0] - \
                        tile.architecture.arch_range[0][0]
                    phys_h = tile.architecture.arch_range[1][1] - \
                        tile.architecture.arch_range[0][1]
                    grid_w_span = tile.width

                    max_phys_width_per_grid_cell = max(
                        max_phys_width_per_grid_cell, phys_w / grid_w_span)
                    max_phys_height_per_grid_cell = max(
                        max_phys_height_per_grid_cell, phys_h)

        if max_phys_width_per_grid_cell == 0 and default_arch_for_empty:
            max_phys_width_per_grid_cell = default_arch_for_empty.arch_range[
                1][0] - default_arch_for_empty.arch_range[0][0]
        if max_phys_height_per_grid_cell == 0 and default_arch_for_empty:
            max_phys_height_per_grid_cell = default_arch_for_empty.arch_range[
                1][1] - default_arch_for_empty.arch_range[0][1]
        if max_phys_width_per_grid_cell == 0:
            max_phys_width_per_grid_cell = 50
        if max_phys_height_per_grid_cell == 0:
            max_phys_height_per_grid_cell = 50

        effective_cell_width_um = max_phys_width_per_grid_cell + 2 * CANVAS_PADDING
        effective_cell_height_um = max_phys_height_per_grid_cell + 2 * CANVAS_PADDING

        total_figure_width_um = self.grid_cols * effective_cell_width_um + \
            max(0, self.grid_cols - 1) * TILE_PADDING
        total_figure_height_um = self.grid_rows * effective_cell_height_um + \
            max(0, self.grid_rows - 1) * TILE_PADDING

        fig_width_inches = total_figure_width_um * inches_per_micron_calc
        fig_height_inches = total_figure_height_um * inches_per_micron_calc

        fig = plt.figure(figsize=(fig_width_inches, fig_height_inches))
        gs = GridSpec(self.grid_rows, self.grid_cols, figure=fig)

        self.axes_map: dict[tuple[int, int], plt.Axes] = {}
        processed_cells = set()

        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                if (r, c) in processed_cells:
                    continue

                tile = tiles[r][c]
                if tile:
                    tile_grid_width_span = tile.width
                    ax = fig.add_subplot(gs[r, c: c + tile_grid_width_span])

                    current_tile_arch = tile.architecture
                    ax.set_xlim([current_tile_arch.arch_range[0][0] - CANVAS_PADDING,
                                 current_tile_arch.arch_range[1][0] + CANVAS_PADDING])
                    ax.set_ylim([current_tile_arch.arch_range[0][1] - CANVAS_PADDING,
                                 current_tile_arch.arch_range[1][1] + CANVAS_PADDING])
                    ax.grid(True, linestyle=':', alpha=0.4, color='grey')
                    self.axes_map[(r, c)] = ax

                    for k_col_offset in range(tile_grid_width_span):
                        processed_cells.add((r, c + k_col_offset))
                else:
                    ax = fig.add_subplot(gs[r, c])
                    ax.axis('off')
                    processed_cells.add((r, c))

                if (r, c) in self.axes_map:
                    self.axes_map[(r, c)].set_xticks([])
                    self.axes_map[(r, c)].set_yticks([])
                    self.axes_map[(r, c)].set_aspect('equal', adjustable='box')

        fig.tight_layout(
            pad=0.5,
            h_pad=TILE_PADDING * inches_per_micron_calc,
            w_pad=TILE_PADDING * inches_per_micron_calc,
            rect=[0.02, 0.02, 0.97, 0.97]
        )

        border_rect = matplotlib.patches.Rectangle(
            (0.01, 0.01), 0.98, 0.98,
            transform=fig.transFigure,
            edgecolor='black',
            linewidth=1.0,
            fill=False,
            clip_on=False,
            zorder=1000
        )
        fig.add_artist(border_rect)
        return fig

    def initial_frame(self):
        for anim_obj in self.anims.values():
            if anim_obj:
                anim_obj.initial_frame()

    def update(self, f: int):
        for anim_obj in self.anims.values():
            if anim_obj:
                anim_obj.update(f)
