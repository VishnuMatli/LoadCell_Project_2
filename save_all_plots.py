import os
import sys
import queue
import threading
import zipfile
import numpy as np
import matplotlib
from xml.sax.saxutils import escape as xml_escape

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, scrolledtext

import main_plot_program as app

OUTPUT_ROOT = "plots"
WORKBOOK_NAME = "bandwidth_summary.xlsx"
FIGSIZE = (14, 8)
DPI = 140

WINDOW_STYLES = {
    "triangular": {"color": "#e4572e", "face": "#fff5ef"},
    "rectangular": {"color": "#7b4f01", "face": "#fff8e8"},
    "hamming": {"color": "#0c7a46", "face": "#f1fbf7"},
    "hanning": {"color": "#1f6feb", "face": "#f3f8ff"},
    "blackman": {"color": "#6f42c1", "face": "#f7f3ff"},
    "kaiser": {"color": "#b23a48", "face": "#fff2f3"},
    "parks_mcclellan": {"color": "#2c7da0", "face": "#f0fbff"},
    "frequency_sampling": {"color": "#3a7d44", "face": "#f2fff2"},
    "least_squares": {"color": "#8a5a44", "face": "#fff7f2"},
}


class ExportStats:
    def __init__(self, total_files, total_jobs):
        self.total_files = total_files
        self.total_jobs = total_jobs
        self.completed_files = 0
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.current_file = ""
        self.current_window = ""

    @property
    def remaining_files(self):
        return max(self.total_files - self.completed_files, 0)

    @property
    def remaining_jobs(self):
        return max(self.total_jobs - self.completed_jobs, 0)


def sanitize_name(name):
    return name.replace(os.sep, "_").replace(" ", "_")


def visible_bandwidth(series):
    if series is None or len(series) == 0:
        return 0.0
    return float(np.nanmax(series) - np.nanmin(series))


def full_limits(series):
    if series is None or len(series) == 0:
        return 0.0, 1.0
    y_min = float(np.nanmin(series))
    y_max = float(np.nanmax(series))
    span = y_max - y_min
    pad = max(span * 0.12, 0.1)
    return y_min - pad, y_max + pad


def column_letter(index):
    result = ""
    current = index
    while current >= 0:
        current, remainder = divmod(current, 26)
        result = chr(65 + remainder) + result
        current -= 1
    return result


def build_xlsx(rows, headers, output_path, sheet_name="Bandwidths"):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    def cell_ref(row_index, column_index):
        return f"{column_letter(column_index)}{row_index}"

    def cell_xml(value, row_index, column_index):
        ref = cell_ref(row_index, column_index)
        if value is None:
            value = ""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{ref}" s="1"><v>{value:.2f}</v></c>'
        text = xml_escape(str(value))
        return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'

    sheet_rows = []
    all_rows = [headers] + rows
    for row_index, row in enumerate(all_rows, start=1):
        cells = [cell_xml(value, row_index, column_index) for column_index, value in enumerate(row)]
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{xml_escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )

    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        '</Relationships>'
    )

    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="1"><numFmt numFmtId="164" formatCode="0.00"/></numFmts>'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '</cellXfs>'
        '</styleSheet>'
    )

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as workbook_zip:
        workbook_zip.writestr("[Content_Types].xml", content_types_xml)
        workbook_zip.writestr("_rels/.rels", root_rels_xml)
        workbook_zip.writestr("xl/workbook.xml", workbook_xml)
        workbook_zip.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        workbook_zip.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        workbook_zip.writestr("xl/styles.xml", styles_xml)


def build_bandwidth_rows(records):
    rows = []
    for record in records:
        rows.append([
            record.get("file", ""),
            record.get("window", ""),
            record.get("status", ""),
            record.get("raw_bandwidth", 0.0),
            record.get("filtered_bandwidth", 0.0),
            record.get("raw_min", 0.0),
            record.get("raw_max", 0.0),
            record.get("filtered_min", 0.0),
            record.get("filtered_max", 0.0),
            record.get("output_path", ""),
        ])
    return rows


def save_plot_for_file_and_window(base_filename, window_method):
    raw = app.load_raw_data(base_filename)
    filtered = app.load_filtered_data(base_filename, window_method)

    raw_bw = visible_bandwidth(raw)
    filtered_bw = visible_bandwidth(filtered)
    raw_x = np.arange(len(raw))
    filtered_x = np.arange(len(filtered))

    style = WINDOW_STYLES.get(window_method, {"color": "#1f6feb", "face": "#f3f8ff"})

    fig, axes = plt.subplots(2, 1, figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("#eef3fb")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.12, hspace=0.30)

    axes[0].set_facecolor("#fffdf9")
    axes[1].set_facecolor(style["face"])

    axes[0].plot(raw_x, raw, color="#e4572e", linewidth=1.5, label="Raw Data")
    axes[1].plot(filtered_x, filtered, color=style["color"], linewidth=1.5, label=f"Filtered ({window_method})")

    raw_ylim = full_limits(raw)
    filtered_ylim = full_limits(filtered)
    axes[0].set_ylim(*raw_ylim)
    axes[1].set_ylim(*filtered_ylim)

    axes[0].grid(True, color="#d8dfe8", linestyle="--", linewidth=0.7, alpha=0.85)
    axes[1].grid(True, color="#d8dfe8", linestyle="--", linewidth=0.7, alpha=0.85)

    axes[0].set_title(f"Raw ADC Data - {base_filename}", fontsize=12, weight="bold", color="#243043")
    axes[0].set_ylabel("Weight", color="#243043")
    axes[0].legend(loc="upper right", frameon=True, facecolor="white")

    axes[1].set_title(f"FIR Filtered Data ({window_method}) - {base_filename}", fontsize=12, weight="bold", color="#243043")
    axes[1].set_xlabel("Sample Index", color="#243043")
    axes[1].set_ylabel("Weight", color="#243043")
    axes[1].legend(loc="upper right", frameon=True, facecolor="white")

    summary = (
        f"Raw bandwidth: {raw_bw:.2f}    |    Filtered bandwidth: {filtered_bw:.2f}    |    "
        f"Samples: {len(raw)}"
    )
    fig.text(0.5, 0.04, summary, ha="center", va="center", fontsize=10, weight="bold", color="#243043")

    out_dir = os.path.join(OUTPUT_ROOT, window_method)
    os.makedirs(out_dir, exist_ok=True)
    out_name = f"plot_{window_method}_{sanitize_name(base_filename)}.png"
    out_path = os.path.join(out_dir, out_name)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    return out_path, raw_bw, filtered_bw


def collect_export_jobs(files):
    jobs = []
    for base_filename in files:
        windows = app.available_windows_for_file(base_filename)
        for window_method in windows:
            jobs.append((base_filename, window_method))
    return jobs


class ExportProgressGUI:
    def __init__(self, files):
        self.files = files
        self.jobs = collect_export_jobs(files)
        self.stats = ExportStats(total_files=len(files), total_jobs=len(self.jobs))
        self.queue = queue.Queue()
        self.records = []
        self.root = tk.Tk()
        self.root.title("Plot Export Progress")
        self.root.geometry("860x560")
        self.root.minsize(760, 500)
        self.root.configure(bg="#162233")

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#162233")
        style.configure("TLabel", background="#162233", foreground="#eef4ff")
        style.configure("Title.TLabel", background="#162233", foreground="#ffffff", font=("TkDefaultFont", 16, "bold"))
        style.configure("Meta.TLabel", background="#162233", foreground="#c7d6ef", font=("TkDefaultFont", 10))
        style.configure("TButton", padding=6)
        style.configure("Horizontal.TProgressbar", thickness=20)

        self.status_var = tk.StringVar(value="Ready to export plots.")
        self.detail_var = tk.StringVar(value="No job started yet.")
        self.counts_var = tk.StringVar(value="Files: 0/0 | Windows: 0/0")
        self.file_var = tk.StringVar(value="-")
        self.window_var = tk.StringVar(value="-")
        self.remaining_var = tk.StringVar(value="Remaining files: 0 | Remaining windows: 0")

        self._build_ui()
        self.root.after(150, self.start_export)
        self.root.after(250, self._poll_queue)

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(container, text="Batch Plot Export Progress", style="Title.TLabel")
        header.pack(anchor="w")

        subtitle = ttk.Label(
            container,
            text="Creates one full plot image per input file and window method, then stores it in plots/<window>/.",
            style="Meta.TLabel",
            wraplength=780,
        )
        subtitle.pack(anchor="w", pady=(6, 14))

        card = tk.Frame(container, bg="#1d2d42", bd=0, highlightthickness=0)
        card.pack(fill=tk.X, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        labels = [
            ("Current file", self.file_var),
            ("Current window", self.window_var),
            ("Counts", self.counts_var),
            ("Remaining", self.remaining_var),
        ]
        for i, (label_text, variable) in enumerate(labels):
            row = tk.Frame(card, bg="#1d2d42")
            row.grid(row=i // 2, column=i % 2, sticky="ew", padx=14, pady=10)
            tk.Label(row, text=label_text, bg="#1d2d42", fg="#8ea6c8", font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
            tk.Label(row, textvariable=variable, bg="#1d2d42", fg="#ffffff", font=("TkDefaultFont", 11)).pack(anchor="w", pady=(2, 0))

        progress_frame = ttk.Frame(container)
        progress_frame.pack(fill=tk.X, pady=(4, 10))

        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor="w")
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(6, 4))

        self.detail_label = ttk.Label(progress_frame, textvariable=self.detail_var, style="Meta.TLabel", wraplength=780)
        self.detail_label.pack(anchor="w")

        log_frame = ttk.Frame(container)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        ttk.Label(log_frame, text="Export Log", style="Meta.TLabel").pack(anchor="w", pady=(0, 4))
        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            height=14,
            bg="#0f1723",
            fg="#d9e6ff",
            insertbackground="#ffffff",
            relief="flat",
            font=("TkDefaultFont", 10),
        )
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.configure(state="disabled")

        button_row = ttk.Frame(container)
        button_row.pack(fill=tk.X, pady=(12, 0))

        self.start_button = ttk.Button(button_row, text="Start / Restart", command=self.start_export)
        self.start_button.pack(side=tk.LEFT)

        ttk.Button(button_row, text="Close", command=self.root.destroy).pack(side=tk.RIGHT)

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def enqueue(self, kind, payload):
        self.queue.put((kind, payload))

    def start_export(self):
        if hasattr(self, "worker") and self.worker.is_alive():
            self.log("[GUI] Export already running.")
            return

        self.stats = ExportStats(total_files=len(self.files), total_jobs=len(self.jobs))
        self.progress_bar["maximum"] = max(self.stats.total_jobs, 1)
        self.progress_bar["value"] = 0
        self.file_var.set("-")
        self.window_var.set("-")
        self.counts_var.set("Files: 0/{} | Windows: 0/{}".format(self.stats.total_files, self.stats.total_jobs))
        self.remaining_var.set(f"Remaining files: {self.stats.remaining_files} | Remaining windows: {self.stats.remaining_jobs}")
        self.status_var.set("Starting export...")
        self.detail_var.set("Preparing jobs...")
        self.log("[GUI] Starting batch export...")

        self.worker = threading.Thread(target=self._run_export, daemon=True)
        self.worker.start()

    def _run_export(self):
        if not self.files:
            self.enqueue("error", "No input files found.")
            return

        for file_index, base_filename in enumerate(self.files, start=1):
            windows = app.available_windows_for_file(base_filename)
            if not windows:
                self.enqueue("log", f"[EXPORT] Skipping {base_filename}: no filtered outputs found.")
                self.enqueue("file_done", {"base_filename": base_filename, "file_index": file_index, "skipped": True})
                continue

            for window_method in windows:
                self.enqueue(
                    "job_start",
                    {"base_filename": base_filename, "window_method": window_method, "file_index": file_index},
                )
                try:
                    out_path, raw_bw, filtered_bw = save_plot_for_file_and_window(base_filename, window_method)
                    raw_data = app.load_raw_data(base_filename)
                    filtered_data = app.load_filtered_data(base_filename, window_method)
                    self.enqueue(
                        "job_done",
                        {
                            "base_filename": base_filename,
                            "window_method": window_method,
                            "out_path": out_path,
                            "raw_bw": raw_bw,
                            "filtered_bw": filtered_bw,
                            "raw_min": float(np.nanmin(raw_data)),
                            "raw_max": float(np.nanmax(raw_data)),
                            "filtered_min": float(np.nanmin(filtered_data)),
                            "filtered_max": float(np.nanmax(filtered_data)),
                            "file_index": file_index,
                        },
                    )
                except Exception as exc:
                    self.enqueue(
                        "job_failed",
                        {"base_filename": base_filename, "window_method": window_method, "error": str(exc), "file_index": file_index},
                    )

            self.enqueue("file_done", {"base_filename": base_filename, "file_index": file_index, "skipped": False})

        self.enqueue("all_done", None)

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                self._handle_event(kind, payload)
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _handle_event(self, kind, payload):
        if kind == "log":
            self.log(payload)
            return

        if kind == "error":
            self.status_var.set("Export failed")
            self.detail_var.set(payload)
            self.log(f"[ERROR] {payload}")
            return

        if kind == "job_start":
            self.stats.current_file = payload["base_filename"]
            self.stats.current_window = payload["window_method"]
            self.file_var.set(payload["base_filename"])
            self.window_var.set(payload["window_method"])
            self.status_var.set("Exporting plot...")
            self.detail_var.set(
                f"Processing file {payload['file_index']}/{self.stats.total_files}: {payload['base_filename']}"
            )
            self.log(f"[EXPORT] Processing {payload['base_filename']} / {payload['window_method']}")
            return

        if kind == "job_done":
            self.stats.completed_jobs += 1
            self.progress_bar["value"] = self.stats.completed_jobs
            self.stats.current_file = payload["base_filename"]
            self.stats.current_window = payload["window_method"]
            self.file_var.set(payload["base_filename"])
            self.window_var.set(payload["window_method"])
            self.status_var.set("Export complete for current plot")
            self.detail_var.set(
                f"Saved {os.path.basename(payload['out_path'])} | raw bw={payload['raw_bw']:.2f} | filtered bw={payload['filtered_bw']:.2f}"
            )
            self.log(
                f"[EXPORT] Saved {payload['out_path']} | raw bw={payload['raw_bw']:.2f} | filtered bw={payload['filtered_bw']:.2f}"
            )
            self.records.append(
                {
                    "file": payload["base_filename"],
                    "window": payload["window_method"],
                    "status": "saved",
                    "raw_bandwidth": payload["raw_bw"],
                    "filtered_bandwidth": payload["filtered_bw"],
                    "raw_min": payload["raw_min"],
                    "raw_max": payload["raw_max"],
                    "filtered_min": payload["filtered_min"],
                    "filtered_max": payload["filtered_max"],
                    "output_path": payload["out_path"],
                }
            )
            self._refresh_counts()
            return

        if kind == "job_failed":
            self.stats.failed_jobs += 1
            self.stats.completed_jobs += 1
            self.progress_bar["value"] = self.stats.completed_jobs
            self.status_var.set("Export encountered an error")
            self.detail_var.set(f"Failed: {payload['base_filename']} / {payload['window_method']}")
            self.log(f"[EXPORT] Failed for {payload['base_filename']} / {payload['window_method']}: {payload['error']}")
            self.records.append(
                {
                    "file": payload["base_filename"],
                    "window": payload["window_method"],
                    "status": f"failed: {payload['error']}",
                    "raw_bandwidth": 0.0,
                    "filtered_bandwidth": 0.0,
                    "raw_min": 0.0,
                    "raw_max": 0.0,
                    "filtered_min": 0.0,
                    "filtered_max": 0.0,
                    "output_path": "",
                }
            )
            self._refresh_counts()
            return

        if kind == "file_done":
            self.stats.completed_files = max(self.stats.completed_files, payload["file_index"])
            if payload.get("skipped"):
                self.log(f"[EXPORT] Skipped file: {payload['base_filename']}")
            else:
                self.log(f"[EXPORT] Completed file: {payload['base_filename']}")
            self._refresh_counts()
            return

        if kind == "all_done":
            workbook_path = os.path.join(OUTPUT_ROOT, WORKBOOK_NAME)
            try:
                build_xlsx(
                    build_bandwidth_rows(self.records),
                    [
                        "File",
                        "Window",
                        "Status",
                        "Raw Bandwidth",
                        "Filtered Bandwidth",
                        "Raw Min",
                        "Raw Max",
                        "Filtered Min",
                        "Filtered Max",
                        "Output Path",
                    ],
                    workbook_path,
                    sheet_name="Bandwidths",
                )
                self.log(f"[GUI] Bandwidth workbook saved to {workbook_path}")
            except Exception as exc:
                self.log(f"[GUI] Failed to save bandwidth workbook: {exc}")
            self.status_var.set("All exports completed")
            self.detail_var.set(
                f"Finished exporting {self.stats.completed_jobs} plot(s) with {self.stats.failed_jobs} failure(s). Workbook: {workbook_path}"
            )
            self.log(
                f"[GUI] Export complete. Jobs={self.stats.completed_jobs}, Failures={self.stats.failed_jobs}"
            )
            return

    def _refresh_counts(self):
        self.counts_var.set(
            f"Files: {self.stats.completed_files}/{self.stats.total_files} | Windows: {self.stats.completed_jobs}/{self.stats.total_jobs}"
        )
        self.remaining_var.set(
            f"Remaining files: {self.stats.remaining_files} | Remaining windows: {self.stats.remaining_jobs}"
        )

    def run(self):
        self.root.mainloop()


def main():
    files = app.list_available_input_files()
    if not files:
        print("[EXPORT] No input files found in adc_data/ or client_files/.")
        sys.exit(1)

    print(f"[EXPORT] Found {len(files)} input file(s). Launching progress GUI...")
    ExportProgressGUI(files).run()


if __name__ == "__main__":
    main()
