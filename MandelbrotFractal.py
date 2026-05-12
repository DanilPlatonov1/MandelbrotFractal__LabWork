import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from multiprocessing import Pool, cpu_count
from PIL import Image, ImageTk
import time


# ПАРАМЕТРЫ ФРАКТАЛА
WIDTH = 1200
HEIGHT = 800
MAX_ITER = 500


# ВЫЧИСЛЕНИЕ ФРАКТАЛА
def fractal(c, max_iter, fractal_type="Mandelbrot", julia_c=complex(-0.7, 0.27015)):

    if fractal_type == "Julia":
        z = c
        c = julia_c
    else:
        z = 0

    for n in range(max_iter):

        if fractal_type == "Mandelbrot":
            z = z * z + c

        elif fractal_type == "Julia":
            z = z * z + c

        elif fractal_type == "Burning Ship":
            z = complex(abs(z.real), abs(z.imag))
            z = z * z + c

        elif fractal_type == "Tricorn":
            z = (z.conjugate() ** 2) + c

        elif fractal_type == "Multibrot":
            z = (z ** 3) + c

        if abs(z) > 2:
            return n

    return max_iter


# ЦВЕТА
def get_color(iteration, max_iter):
    if iteration == max_iter:
        return (0, 0, 0)

    t = iteration / max_iter

    r = int(9 * (1 - t) * t * t * t * 255)
    g = int(15 * (1 - t) * (1 - t) * t * t * 255)
    b = int(8.5 * (1 - t) * (1 - t) * (1 - t) * t * 255)

    return (r, g, b)


# ПОСЛЕДОВАТЕЛЬНЫЙ РЕНДЕР
def render_sequential(width, height, max_iter,
                      re_start, re_end,
                      im_start, im_end,
                      fractal_type):

    image = Image.new("RGB", (width, height))
    pixels = image.load()

    for y in range(height):
        for x in range(width):

            re = re_start + (x / width) * (re_end - re_start)
            im = im_start + (y / height) * (im_end - im_start)

            c = complex(re, im)

            m = fractal(c, max_iter, fractal_type)

            pixels[x, y] = get_color(m, max_iter)

    return image


# ПАРАЛЛЕЛЬНЫЙ РЕНДЕР
def compute_row(args):
    y, width, height, max_iter, re_start, re_end, im_start, im_end, fractal_type = args

    row = []

    for x in range(width):

        re = re_start + (x / width) * (re_end - re_start)
        im = im_start + (y / height) * (im_end - im_start)

        c = complex(re, im)

        m = fractal(c, max_iter, fractal_type)

        row.append(get_color(m, max_iter))

    return y, row


# GUI
class MandelbrotApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Параллельный рендеринг множества Мандельброта")

        self.width = WIDTH
        self.height = HEIGHT

        self.re_start = -2.0
        self.re_end = 1.0
        self.im_start = -1.2
        self.im_end = 1.2

        self.fractal_type = tk.StringVar(value="Mandelbrot")
        self.max_iter = MAX_ITER

        self.image = None
        self.photo = None

        self.zoom_rect = None
        self.start_x = None
        self.start_y = None

        self.create_widgets()

    # СОЗДАНИЕ ЭЛЕМЕНТОВ GUI
    def create_widgets(self):

        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        tk.Label(control_frame, text="Процессы:").pack(side=tk.LEFT)
        self.process_var = tk.IntVar(value=cpu_count())

        process_spin = tk.Spinbox(
            control_frame,
            from_=1,
            to=cpu_count(),
            textvariable=self.process_var,
            width=5
        )
        process_spin.pack(side=tk.LEFT, padx=5)

        tk.Label(control_frame, text="Разрешение:").pack(side=tk.LEFT, padx=(20, 0))
        self.resolution_var = tk.StringVar(value="1200x800")
        resolution_combo = ttk.Combobox(
            control_frame,
            textvariable=self.resolution_var,
            values=[
                "800x600",
                "1200x800",
                "1920x1080",
                "3840x2160"
            ],
            width=12,
            state="readonly"
        )
        resolution_combo.pack(side=tk.LEFT, padx=5)

        tk.Label(control_frame, text="Фрактал:").pack(side=tk.LEFT, padx=(20, 0))

        fractal_combo = ttk.Combobox(
            control_frame,
            textvariable=self.fractal_type,
            values=[
                "Mandelbrot",
                "Julia",
                "Burning Ship",
                "Tricorn",
                "Multibrot"
            ],
            width=15,
            state="readonly"
        )
        fractal_combo.pack(side=tk.LEFT, padx=5)
        fractal_combo.bind("<<ComboboxSelected>>", self.change_fractal)

        # Кнопки
        sequential_btn = tk.Button(
            control_frame,
            text="Обычный рендер",
            command=self.run_sequential
        )
        sequential_btn.pack(side=tk.LEFT, padx=10)

        parallel_btn = tk.Button(
            control_frame,
            text="Параллельный рендер",
            command=self.run_parallel
        )
        parallel_btn.pack(side=tk.LEFT)

        reset_btn = tk.Button(
            control_frame,
            text="Сброс Zoom",
            command=self.reset_view
        )
        reset_btn.pack(side=tk.LEFT, padx=10)

        save_btn = tk.Button(
            control_frame,
            text="Сохранить PNG",
            command=self.save_image
        )
        save_btn.pack(side=tk.LEFT)

        self.info_label = tk.Label(
            self.root,
            text="Готов к рендерингу",
            font=("Arial", 11)
        )
        self.info_label.pack(pady=5)

        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg="black"
        )
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.zoom_start)
        self.canvas.bind("<B1-Motion>", self.zoom_drag)
        self.canvas.bind("<ButtonRelease-1>", self.zoom_end)

    def update_resolution(self):
        resolution = self.resolution_var.get()
        width, height = resolution.split("x")

        self.width = int(width)
        self.height = int(height)

        self.canvas.config(width=self.width, height=self.height)

    # ОТОБРАЖЕНИЕ ИЗОБРАЖЕНИЯ
    def display_image(self):
        self.photo = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    # ОБЫЧНЫЙ РЕНДЕР
    def run_sequential(self):

        self.update_resolution()
        self.info_label.config(text="Выполняется обычный рендер...")
        self.root.update()
        start_time = time.time()

        self.image = render_sequential(
            self.width,
            self.height,
            self.max_iter,
            self.re_start,
            self.re_end,
            self.im_start,
            self.im_end,
            self.fractal_type.get()
        )

        end_time = time.time()
        self.display_image()
        elapsed = end_time - start_time

        self.info_label.config(
            text=f"Обычный рендер завершен за {elapsed:.2f} сек"
        )

    # ПАРАЛЛЕЛЬНЫЙ РЕНДЕР
    def run_parallel(self):
        self.update_resolution()
        process_count = self.process_var.get()

        self.info_label.config(
            text=f"Параллельный рендер ({process_count} процессов)..."
        )
        self.root.update()

        start_time = time.time()

        image = Image.new("RGB", (self.width, self.height))
        pixels = image.load()

        args = [
            (
                y,
                self.width,
                self.height,
                self.max_iter,
                self.re_start,
                self.re_end,
                self.im_start,
                self.im_end,
                self.fractal_type.get()
            )
            for y in range(self.height)
        ]

        with Pool(processes=process_count) as pool:
            results = pool.map(compute_row, args)

        for y, row in results:
            for x, color in enumerate(row):
                pixels[x, y] = color

        self.image = image
        end_time = time.time()
        self.display_image()
        elapsed = end_time - start_time

        self.info_label.config(
            text=f"Параллельный рендер завершен за {elapsed:.2f} сек"
        )

    def save_image(self):
        if self.image is None:
            messagebox.showwarning("Ошибка", "Сначала выполните рендеринг")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")]
        )

        if filename:
            self.image.save(filename)
            messagebox.showinfo("Успех", "Изображение сохранено")

    def zoom_start(self, event):
        self.start_x = event.x
        self.start_y = event.y

        if self.zoom_rect:
            self.canvas.delete(self.zoom_rect)

        self.zoom_rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="white"
        )

    def zoom_drag(self, event):
        if self.zoom_rect:
            self.canvas.coords(
                self.zoom_rect,
                self.start_x,
                self.start_y,
                event.x,
                event.y
            )

    def zoom_end(self, event):
        end_x = event.x
        end_y = event.y

        if abs(end_x - self.start_x) < 10 or abs(end_y - self.start_y) < 10:
            return

        new_re_start = self.re_start + (min(self.start_x, end_x) / self.width) * (
                self.re_end - self.re_start)

        new_re_end = self.re_start + (max(self.start_x, end_x) / self.width) * (
                self.re_end - self.re_start)

        new_im_start = self.im_start + (min(self.start_y, end_y) / self.height) * (
                self.im_end - self.im_start)

        new_im_end = self.im_start + (max(self.start_y, end_y) / self.height) * (
                self.im_end - self.im_start)

        self.re_start = new_re_start
        self.re_end = new_re_end
        self.im_start = new_im_start
        self.im_end = new_im_end
        self.run_parallel()

    def reset_view(self):
        self.re_start = -2.0
        self.re_end = 1.0
        self.im_start = -1.2
        self.im_end = 1.2
        self.run_parallel()

    def change_fractal(self, event=None):
        self.reset_view()


# ЗАПУСК
if __name__ == "__main__":
    root = tk.Tk()
    app = MandelbrotApp(root)
    root.mainloop()
