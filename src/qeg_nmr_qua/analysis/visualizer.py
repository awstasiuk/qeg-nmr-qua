"""
Pulse Sequence Visualizer for NMR experiments built with the Experiment API.

Parses the command list stored in an :class:`~qeg_nmr_qua.experiment.experiment.Experiment`
subclass and renders the sequence as a timing diagram, similar to NMR textbook figures:
one horizontal track per element, with filled rectangles for pulses and proportional
spacing for delays.
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker

# ── colour / style constants ──────────────────────────────────────────────────
_CMAP = plt.cm.tab10.colors  # cycling palette for elements
_FLOQUET_PASTEL = plt.cm.Pastel1.colors
_FLOQUET_ALPHA = 0.55  # floquet block fill transparency
_PULSE_ALPHA = 0.85  # normal pulse fill transparency
_SWEPT_ALPHA = 0.55  # swept pulse fill transparency

# Minimum visible rectangle width as a fraction of total sequence time.
_MIN_RECT_FRAC = 0.008

# ── phase helpers ─────────────────────────────────────────────────────────────


def _phase_deg(phase_frac: float) -> float:
    """Phase fraction of 2π → degrees in [0, 360)."""
    return (float(phase_frac) % 1.0) * 360.0


def _phase_label(phase_frac: float) -> str:
    """Return a compact axis label for a phase fraction of 2π.

    NMR convention: 0 → 'x', 90 → 'y', 180 → '-x', 270 → '-y', else '<N>°'.
    """
    deg = round(_phase_deg(phase_frac)) % 360
    _NAMED = {0: "x", 90: "y", 180: "-x", 270: "-y"}
    return _NAMED.get(deg, f"{deg}°")


class SequenceVisualizer:
    """Renders the pulse sequence stored in an :class:`~Experiment` as a timing diagram.

    One horizontal track is drawn per element.  Pulses appear as filled rectangles
    whose widths are proportional to their duration; delays provide the spacing between
    them.  Swept / looped parameters are indicated by hatching and a layer label.
    Floquet sequences are shown as a single wide block by default; call
    :meth:`show_floquet_pulses` to expand them into individual pulses.

    Parameters
    ----------
    experiment:
        An *Experiment* (or subclass) instance whose ``_commands`` list has been
        populated via the ``add_*`` family of methods.
    settings:
        :class:`~ExperimentSettings` instance associated with the experiment.
    config:
        :class:`~OPXConfig` instance associated with the experiment.
    """

    def __init__(self, experiment, settings, config):
        self.experiment = experiment
        self.settings = settings
        self.config = config

        self._floquet_labels: dict[int, str] = {}
        self._show_floquet_pulses: bool = False
        self._title: str | None = None
        self._fig: plt.Figure | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def set_floquet_labels(self, labels: dict | list):
        """Assign human-readable labels to Floquet sequence blocks.

        Parameters
        ----------
        labels:
            *dict* mapping 0-based Floquet-command indices to label strings,
            **or** a *list* of strings applied to Floquet commands in order of
            appearance.
        """
        if isinstance(labels, list):
            self._floquet_labels = {i: lbl for i, lbl in enumerate(labels)}
        else:
            self._floquet_labels = dict(labels)

    def show_floquet_pulses(self):
        """Expand Floquet blocks into individual pulse rectangles.

        By default each :meth:`~Experiment.add_floquet_sequence` call is rendered
        as a single wide rectangle annotated with the number of repetitions.
        Calling this method switches to individual-pulse mode.
        """
        self._show_floquet_pulses = True

    def set_title(self, title: str):
        """Set the figure suptitle."""
        self._title = title

    def save_image(self, path: str):
        """Save the most recently produced figure to *path*.

        Raises
        ------
        RuntimeError
            If :meth:`plot` has not been called yet.
        """
        if self._fig is None:
            raise RuntimeError("Call plot() before save_image().")
        self._fig.savefig(path, bbox_inches="tight", dpi=150)
        print(f"Saved visualization to: {path}")

    def plot(self) -> plt.Figure:
        """Build and display the pulse-sequence timing diagram.

        Returns
        -------
        matplotlib.figure.Figure
        """
        events, element_order, total_us, seq_end_us = self._parse_commands()

        if not element_order:
            print("No pulse/sequence commands found – nothing to plot.")
            return None

        n_rows = len(element_order)
        fig_w = max(10.0, total_us / 0.6)
        fig, axes = plt.subplots(
            n_rows,
            1,
            figsize=(fig_w, 2.4 * n_rows + 0.8),
            squeeze=False,
            sharex=True,
        )
        ax_map = {el: axes[i][0] for i, el in enumerate(element_order)}
        color_map = {el: _CMAP[i % 10] for i, el in enumerate(element_order)}

        min_w = max(seq_end_us * _MIN_RECT_FRAC, 0.004)  # 4 ns minimum

        for ev in events:
            etype = ev["type"]
            if etype in ("pulse", "floquet"):
                self._draw_pulse_event(ev, ax_map, color_map, min_w, total_us)
            elif etype == "z_rotation":
                self._draw_zrot_event(ev, ax_map)
            elif etype == "readout":
                self._draw_readout_event(ev, ax_map, color_map, total_us)

        # ── per-row cosmetics ─────────────────────────────────────────────
        for el in element_order:
            ax = ax_map[el]
            ax.set_xlim(-seq_end_us * 0.05, total_us * 1.02)
            ax.set_ylim(0.0, 1.85)
            ax.set_yticks([])
            ax.set_ylabel(
                el, fontsize=10, rotation=0, ha="right", va="center", labelpad=8
            )
            ax.axhline(0.5, color="black", linewidth=1.5, zorder=0)
            for spine in ("top", "right", "left"):
                ax.spines[spine].set_visible(False)
            # vertical separator between sequence and readout regions
            ax.axvline(
                seq_end_us, color="#aaaaaa", linewidth=1.0, linestyle=":", zorder=1
            )

        # ── x-axis ticks only over sequence region ────────────────────────
        bottom_ax = axes[-1][0]
        _loc = ticker.MaxNLocator(nbins=6, steps=[1, 2, 5, 10])
        seq_ticks = [t for t in _loc.tick_values(0.0, seq_end_us) if t <= seq_end_us]
        bottom_ax.set_xticks(seq_ticks)
        bottom_ax.set_xticklabels([f"{t:g}" for t in seq_ticks])
        # 5 minor subdivisions per major interval, kept within sequence region
        if len(seq_ticks) >= 2:
            _major_step = seq_ticks[1] - seq_ticks[0]
            _minor_step = _major_step / 5.0
            _minor = np.arange(0.0, seq_end_us + _minor_step * 0.5, _minor_step)
            _minor = [v for v in _minor if v not in seq_ticks and v <= seq_end_us]
            bottom_ax.xaxis.set_minor_locator(ticker.FixedLocator(_minor))
        bottom_ax.set_xlabel("Time (µs)", fontsize=10)

        if self._title:
            fig.suptitle(self._title, fontsize=12, fontweight="bold", y=1.01)

        # ── loop legend ───────────────────────────────────────────────────
        legend_handles = self._build_loop_legend()
        if legend_handles:
            fig.legend(
                handles=legend_handles,
                loc="lower center",
                ncol=len(legend_handles),
                fontsize=8,
                framealpha=0.9,
                bbox_to_anchor=(0.5, -0.06),
            )

        fig.tight_layout()
        self._fig = fig
        plt.show()
        return fig

    # ── command parser ────────────────────────────────────────────────────────

    def _parse_commands(self):
        """Walk through experiment._commands and return draw-event list.

        Returns
        -------
        events : list[dict]
        element_order : list[str]   – ordered list of element names
        total_ns : float            – end time of last event (ns)
        """
        commands = self.experiment._commands
        all_elements = self._collect_elements(commands)
        element_order = self._order_elements(all_elements)

        t = {el: 0.0 for el in element_order}  # time cursor (ns) per element
        events: list[dict] = []
        floquet_idx = 0

        for cmd in commands:
            ctype = cmd["type"]

            # ---- pulse -------------------------------------------------------
            if ctype == "pulse":
                el = cmd["element"]
                length_ns = self._pulse_length_ns(cmd)
                label = self._build_pulse_label(cmd)
                is_swept = self._is_swept_pulse(cmd)
                layer_hint = self._primary_layer(cmd)
                events.append(
                    {
                        "type": "pulse",
                        "element": el,
                        "start": t[el],
                        "width": length_ns,
                        "label": label,
                        "is_swept": is_swept,
                        "layer": layer_hint,
                    }
                )
                t[el] += length_ns

            # ---- delay -------------------------------------------------------
            elif ctype == "delay":
                delay_ns = self._delay_ns(cmd)
                is_swept = "layer" in cmd
                # wait() in QUA advances all elements
                for el in element_order:
                    t[el] += delay_ns

            # ---- align -------------------------------------------------------
            elif ctype == "align":
                els = cmd.get("elements") or element_order
                max_t = max(t[el] for el in els)
                for el in els:
                    t[el] = max_t

            # ---- floquet / sequence -----------------------------------------
            elif ctype == "sequence":
                el = cmd["element"]
                phases = cmd["phases"]  # fraction of 2π, array
                delays = cmd["delays"]  # clock cycles, array
                pulse_len_ns = self._floquet_pulse_len_ns(cmd)
                reps = self._sequence_reps(cmd)
                is_swept = "layer" in cmd
                layer_hint = cmd.get("layer", None)

                if self._show_floquet_pulses:
                    n_show = max(1, int(reps))
                    for _ in range(n_show):
                        t[el] += delays[0] * 4  # leading gap
                        for phase, delay_cyc in zip(phases, delays[1:]):
                            lbl = f"{round(_phase_deg(phase))}°"
                            events.append(
                                {
                                    "type": "pulse",
                                    "element": el,
                                    "start": t[el],
                                    "width": pulse_len_ns,
                                    "label": lbl,
                                    "is_swept": False,
                                    "layer": None,
                                }
                            )
                            t[el] += pulse_len_ns + delay_cyc * 4
                else:
                    per_rep_ns = sum(delays) * 4 + len(phases) * pulse_len_ns
                    total_block_ns = reps * per_rep_ns
                    default_lbl = f"Floquet ×{reps}" + (" (swept)" if is_swept else "")
                    label = self._floquet_labels.get(floquet_idx, default_lbl)
                    events.append(
                        {
                            "type": "floquet",
                            "element": el,
                            "start": t[el],
                            "width": total_block_ns,
                            "label": label,
                            "is_swept": is_swept,
                            "layer": layer_hint,
                            "phases": phases,
                            "reps": reps,
                        }
                    )
                    t[el] += total_block_ns
                floquet_idx += 1

            # ---- z_rotation --------------------------------------------------
            elif ctype == "z_rotation":
                angle_deg = self._zrot_angle(cmd)
                is_swept = "layer" in cmd or "phase_cycle" in cmd
                for el in cmd["elements"]:
                    events.append(
                        {
                            "type": "z_rotation",
                            "element": el,
                            "x": t[el],
                            "label": f"Z({round(angle_deg)}°)",
                            "is_swept": is_swept,
                            "layer": cmd.get("layer", None),
                        }
                    )
                # Z rotations are instantaneous (frame rotation)

        # ── capture sequence end before adding readout ────────────────
        seq_end_ns = max(t.values()) if t else 0.0

        # ── append measurement block ───────────────────────────────────
        self._append_readout_event(events, t, element_order)

        total_ns = max(t.values()) if t else 100.0

        # ── convert all coordinates from ns → µs ─────────────────────────
        _SCALE = 1e-3
        for ev in events:
            for key in (
                "start",
                "width",
                "x",
                "dead_start",
                "dead_disp",
                "acq_start",
                "acq_width",
            ):
                if key in ev:
                    ev[key] = ev[key] * _SCALE

        total_us = total_ns * _SCALE
        seq_end_us = seq_end_ns * _SCALE
        return events, element_order, total_us, seq_end_us

    # ── drawing helpers ───────────────────────────────────────────────────────

    # Display cap for dead-time and FID sections (ns). Both sections are
    # compressed to these widths if the real duration exceeds them; a break
    # marker is drawn when compression is active.
    _DEAD_DISPLAY_MAX_NS: float = 6_000.0  # 6 µs
    _FID_DISPLAY_MAX_NS: float = 12_000.0  # 12 µs

    def _append_readout_event(self, events: list, t: dict, element_order: list):
        """Append a readout (acquisition) event after all pulse commands."""
        settings = getattr(self.experiment, "settings", None)
        probe = getattr(self.experiment, "probe_key", None)
        helper = getattr(self.experiment, "helper_key", None)

        readout_delay_ns = (
            float(getattr(settings, "readout_delay", 20_000)) if settings else 20_000.0
        )
        readout_end_ns = (
            float(getattr(settings, "readout_end", 256_000)) if settings else 256_000.0
        )
        readout_start_ns = (
            float(getattr(settings, "readout_start", 0)) if settings else 0.0
        )
        acq_width_ns = readout_end_ns - readout_start_ns

        t_end = max(t.values()) if t else 0.0

        # Compressed display widths (what actually gets drawn)
        dead_disp = min(readout_delay_ns, self._DEAD_DISPLAY_MAX_NS)
        fid_disp = min(acq_width_ns, self._FID_DISPLAY_MAX_NS)

        acq_start_display = t_end + dead_disp  # display position of acq start

        elements = [el for el in (probe, helper) if el and el in t]
        if not elements:
            elements = [el for el in element_order if el in t][:1]

        events.append(
            {
                "type": "readout",
                "elements": elements,
                # real values (ns, converted to µs later)
                "dead_start": t_end,
                "dead_real": readout_delay_ns,
                "acq_real": acq_width_ns,
                # display values (ns, converted to µs later)
                "dead_disp": dead_disp,
                "acq_start": acq_start_display,
                "acq_width": fid_disp,
                "dead_compressed": readout_delay_ns > self._DEAD_DISPLAY_MAX_NS,
                "fid_compressed": acq_width_ns > self._FID_DISPLAY_MAX_NS,
            }
        )
        for el in elements:
            t[el] = acq_start_display + fid_disp

    @staticmethod
    def _draw_break_marker(ax, x: float, y0: float, h: float, color: str = "#666"):
        """Draw a double-slash axis-break marker centred at (x, y0 + h/2)."""
        cy = y0 + h / 2
        half = h * 0.28
        gap = h * 0.06
        dx = h * 0.06
        for off in (-gap / 2, gap / 2):
            xs = [x + off - dx, x + off + dx]
            ys = [cy - half, cy + half]
            ax.plot(xs, ys, color=color, linewidth=1.2, zorder=5, clip_on=True)

    def _draw_readout_event(self, ev, ax_map, color_map, total_us):
        """Draw the dead-time gap, detector triangle, and compact dummy FID."""
        dead_start = ev["dead_start"]  # µs
        acq_start = ev["acq_start"]  # µs (display position)
        acq_width = ev["acq_width"]  # µs (compressed display width)
        dead_disp = ev["dead_disp"]  # µs (compressed dead-time width)
        dead_real_us = ev["dead_real"] * 1e-3
        acq_real_us = ev["acq_real"] * 1e-3
        dead_compressed = ev["dead_compressed"]
        fid_compressed = ev["fid_compressed"]

        # triangle: fixed fraction of FID display block
        tri_w = acq_width * 0.18
        y0, h = 0.18, 0.64
        cy = y0 + h / 2

        for el in ev["elements"]:
            ax = ax_map.get(el)
            if ax is None:
                continue

            # ── dashed dead-time line ─────────────────────────────────────
            ax.plot(
                [dead_start, acq_start],
                [cy, cy],
                color="#999999",
                linewidth=1.0,
                linestyle="dashed",
                zorder=1,
            )
            # label the dead-time duration in the middle of the gap
            dead_cx = dead_start + dead_disp / 2
            dead_label = f"{dead_real_us:.0f} µs" if dead_compressed else ""
            if dead_label:
                ax.text(
                    dead_cx,
                    cy + 0.14,
                    dead_label,
                    ha="center",
                    va="bottom",
                    fontsize=6.5,
                    color="#777777",
                    zorder=5,
                    clip_on=True,
                )
            # (no break markers – duration labels carry the annotation)

            # ── left-pointing triangle (detector symbol) ─────────────────
            triangle = plt.Polygon(
                [
                    [acq_start + tri_w, y0],
                    [acq_start + tri_w, y0 + h],
                    [acq_start, cy],
                ],
                closed=True,
                facecolor="#cccccc",
                edgecolor="black",
                linewidth=1.2,
                alpha=0.90,
                zorder=2,
            )
            ax.add_patch(triangle)

            # ── compact dummy FID ─────────────────────────────────────────
            fid_start = acq_start + tri_w
            fid_len = acq_width - tri_w
            if fid_len > 0:
                t_fid = np.linspace(0.0, fid_len, 300)
                tau = fid_len * 0.35
                n_cycles = 5
                freq = n_cycles / fid_len
                amp_fid = 0.22
                fid_y = (
                    amp_fid * np.exp(-t_fid / tau) * np.cos(2.0 * np.pi * freq * t_fid)
                    + cy
                )
                ax.plot(
                    fid_start + t_fid,
                    fid_y,
                    color="black",
                    linewidth=0.9,
                    zorder=3,
                    clip_on=True,
                )

            # ── label above the acquisition block ─────────────────────────
            cx = acq_start + acq_width / 2
            acq_label = f"Acq. ({acq_real_us:.0f} µs)" if fid_compressed else "Acq."
            ax.text(
                cx,
                y0 + h + 0.06,
                acq_label,
                ha="center",
                va="bottom",
                fontsize=8,
                zorder=4,
                clip_on=True,
            )

    def _draw_pulse_event(self, ev, ax_map, color_map, min_w, total_us):
        el = ev["element"]
        ax = ax_map[el]
        is_floquet = ev["type"] == "floquet"
        x = ev["start"]
        w = max(ev["width"], min_w)
        is_swept = ev["is_swept"]

        # color: solid for normal pulse, pastel for floquet block
        el_idx = list(color_map.keys()).index(el)
        face_color = _FLOQUET_PASTEL[el_idx % 9] if is_floquet else color_map[el]
        alpha = (
            _FLOQUET_ALPHA
            if is_floquet
            else (_SWEPT_ALPHA if is_swept else _PULSE_ALPHA)
        )
        hatch = "///" if is_swept else ("..." if is_floquet else "")

        rect = mpatches.FancyBboxPatch(
            (x, 0.18),
            w,
            0.64,
            boxstyle="square,pad=0",
            linewidth=1.5,
            edgecolor="black",
            facecolor=face_color,
            alpha=alpha,
            hatch=hatch,
            zorder=2,
        )
        ax.add_patch(rect)

        # annotation above the rectangle
        label = ev.get("label", "")
        cx = x + w / 2
        if label:
            ax.text(
                cx,
                0.88,
                label,
                ha="center",
                va="bottom",
                fontsize=8,
                zorder=3,
                clip_on=True,
            )

        # loop-layer badge below the rectangle
        if is_swept and ev.get("layer") is not None:
            ax.text(
                cx,
                0.12,
                f"L{ev['layer']}",
                ha="center",
                va="top",
                fontsize=6.5,
                color="#555555",
                zorder=3,
                clip_on=True,
            )

    def _draw_zrot_event(self, ev, ax_map):
        ax = ax_map[ev["element"]]
        x = ev["x"]
        ax.axvline(
            x,
            ymin=0.05,
            ymax=0.95,
            color="#cc3300",
            linewidth=1.2,
            linestyle="--",
            zorder=3,
        )
        ax.text(
            x,
            1.55,
            ev["label"],
            ha="center",
            va="bottom",
            fontsize=7,
            color="#cc3300",
            zorder=4,
            clip_on=True,
        )

    # ── loop-legend builder ───────────────────────────────────────────────────

    def _build_loop_legend(self) -> list:
        """Return legend patch handles describing each swept loop layer."""
        items = []
        var_vecs = getattr(self.experiment, "var_vec_lst", [])
        if not var_vecs:
            return items

        # find which layers are actually referenced
        seen_layers: set[int] = set()
        for cmd in self.experiment._commands:
            for key in ("layer", "phase_layer", "amplitude_layer", "length_layer"):
                if key in cmd:
                    seen_layers.add(cmd[key])

        for layer_idx in sorted(seen_layers):
            li = layer_idx - 1
            if li >= len(var_vecs) or var_vecs[li] is None:
                continue
            vec = var_vecs[li]
            vmin, vmax, n = vec[0], vec[-1], len(vec)
            label = f"Loop L{layer_idx}: {n} points  " f"[{vmin:.3g} → {vmax:.3g}]"
            patch = mpatches.Patch(
                facecolor="white",
                edgecolor="#444",
                hatch="///",
                linewidth=0.8,
                label=label,
            )
            items.append(patch)
        return items

    # ── element discovery ─────────────────────────────────────────────────────

    def _collect_elements(self, commands) -> set:
        els: set[str] = set()
        for cmd in commands:
            if cmd["type"] in ("pulse", "sequence"):
                els.add(cmd["element"])
            elif cmd["type"] == "z_rotation":
                for el in cmd["elements"]:
                    els.add(el)
        return els

    def _order_elements(self, elements: set) -> list:
        """Order: probe first, helper second, rest alphabetically."""
        probe = getattr(self.experiment, "probe_key", None)
        helper = getattr(self.experiment, "helper_key", None)
        ordered = []
        for key in (probe, helper):
            if key and key in elements:
                ordered.append(key)
        for el in sorted(elements):
            if el not in ordered:
                ordered.append(el)
        return ordered

    # ── length / duration resolution ──────────────────────────────────────────

    def _pulse_length_ns(self, cmd: dict) -> float:
        """Resolve pulse length in ns; use first loop value when swept."""
        if "length" in cmd:
            return cmd["length"] * 4.0
        if "length_layer" in cmd:
            li = cmd["length_layer"] - 1
            vec = self.experiment.var_vec_lst[li]
            scale = cmd.get("length_scale", 1)
            return vec[0] * scale * 4.0
        # look up default length in config
        el = cmd["element"]
        shape = cmd["shape"]
        pulse_name = self.config.elements.elements[el].operations.get(shape)
        if pulse_name and pulse_name in self.config.pulses.pulses:
            return float(self.config.pulses.pulses[pulse_name].length)
        return 40.0  # fallback

    def _delay_ns(self, cmd: dict) -> float:
        if "duration" in cmd:
            return cmd["duration"] * 4.0
        if "layer" in cmd:
            li = cmd["layer"] - 1
            vec = self.experiment.var_vec_lst[li]
            return vec[0] * cmd.get("scale", 1) * 4.0
        return 0.0

    def _floquet_pulse_len_ns(self, cmd: dict) -> float:
        el = cmd["element"]
        shape = cmd["shape"]
        pulse_name = self.config.elements.elements[el].operations.get(shape)
        if pulse_name and pulse_name in self.config.pulses.pulses:
            return float(self.config.pulses.pulses[pulse_name].length)
        return 40.0

    def _sequence_reps(self, cmd: dict) -> int:
        if "repetitions" in cmd:
            return int(cmd["repetitions"])
        if "layer" in cmd:
            li = cmd["layer"] - 1
            vec = self.experiment.var_vec_lst[li]
            return int(vec[0])
        return 1

    def _zrot_angle(self, cmd: dict) -> float:
        if "angle" in cmd:
            return _phase_deg(cmd["angle"])
        if "layer" in cmd:
            li = cmd["layer"] - 1
            vec = self.experiment.var_vec_lst[li]
            return _phase_deg(vec[0] * cmd.get("scale", 1))
        if "phase_cycle" in cmd:
            return _phase_deg(cmd["phase_cycle"][0])
        return 0.0

    # ── label builders ────────────────────────────────────────────────────────

    def _build_pulse_label(self, cmd: dict) -> str:
        """Compose the annotation shown above a pulse rectangle."""
        # ---- phase ----
        if "phase_cycle" in cmd:
            phases = cmd["phase_cycle"]
            lbls = [_phase_label(p) for p in phases[:4]]
            suffix = "…" if len(phases) > 4 else ""
            phase_lbl = f"cyc[{', '.join(lbls)}{suffix}]"
        elif "phase_layer" in cmd:
            li = cmd["phase_layer"] - 1
            vec = self.experiment.var_vec_lst[li]
            scale = cmd.get("phase_scale", 1)
            d0 = round(_phase_deg(vec[0] * scale))
            d1 = round(_phase_deg(vec[-1] * scale))
            phase_lbl = f"φ: {d0}°–{d1}°"
        elif "phase" in cmd:
            phase_lbl = _phase_label(cmd["phase"])
        else:
            phase_lbl = ""

        # ---- amplitude ----
        if "amplitude_layer" in cmd:
            li = cmd["amplitude_layer"] - 1
            vec = self.experiment.var_vec_lst[li]
            scale = cmd.get("amplitude_scale", 1)
            amp_lbl = f"A: {vec[0] * scale:.2g}–{vec[-1] * scale:.2g}"
        elif "amplitude" in cmd and abs(cmd["amplitude"] - 1.0) > 1e-6:
            amp_lbl = f"×{cmd['amplitude']:.3g}"
        else:
            amp_lbl = ""

        parts = [p for p in (phase_lbl, amp_lbl) if p]
        return "\n".join(parts)

    def _is_swept_pulse(self, cmd: dict) -> bool:
        return any(k in cmd for k in ("phase_layer", "amplitude_layer", "length_layer"))

    def _primary_layer(self, cmd: dict) -> int | None:
        for key in ("length_layer", "amplitude_layer", "phase_layer"):
            if key in cmd:
                return cmd[key]
        return None
