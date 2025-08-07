import gi
import subprocess
import functools
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

UBUNTU_ORANGE = "#E95420"
GRAY = "#CCCCCC"

class SelectableBox(Gtk.Frame):
    def __init__(self, label, idx, on_select, selected=False):
        super().__init__()
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self.set_name("selectablebox")
        self.eventbox = Gtk.EventBox()
        self.label = Gtk.Label(label)
        self.eventbox.add(self.label)
        self.add(self.eventbox)
        self.idx = idx
        self.on_select = on_select
        self.selected = selected
        self.eventbox.connect("button-press-event", self.handle_click)
        self.set_size_request(80, 60)
        self.label.show()
        self.eventbox.show()
        self.show()
        self.update_style()

    def handle_click(self, widget, event):
        self.on_select(self, self.idx)

    def set_selected(self, selected):
        self.selected = selected
        self.update_style()

    def update_style(self):
        css = (
            "#selectablebox {"
            "background-color: #CCCCCC;"
            "border-radius: 8px;"
            "border: 2px solid white;"
            "padding: 0px;"
            "}"
        )
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        self.get_style_context().add_provider(style_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.label.set_markup(f'<span foreground="black">{self.label.get_text()}</span>')

class MyWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="adb遥控")
        self.set_border_width(10)
        self.set_name("mainwindow")
        self.set_default_size(700, 400)
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        self.add(grid)
        self.screen_width = None
        self.screen_height = None
        # 3行2列，A~F顺序与屏幕区域一致
        self.selectable_positions = [
            (0, 0, "A"), (0, 1, "B"),
            (1, 0, "C"), (1, 1, "D"),
            (2, 0, "E"), (2, 1, "F")
        ]
        self.selectable_boxes = []
        for idx, (row, col, label) in enumerate(self.selectable_positions):
            box = SelectableBox(label, idx, self.on_select, selected=(idx==0))
            self.selectable_boxes.append(box)
            grid.attach(box, col, row, 1, 1)
        # (0,2) 上滑按钮
        up_btn = Gtk.Button(label="上滑")
        up_btn.connect("clicked", self.on_up_btn_clicked)
        grid.attach(up_btn, 2, 0, 1, 1)
        # (1,2) 锁屏键按钮
        lock_btn = Gtk.Button(label="锁屏键")
        lock_btn.connect("clicked", self.on_lock_btn_clicked)
        grid.attach(lock_btn, 2, 1, 1, 1)
        # (2,2) 下滑按钮
        down_btn = Gtk.Button(label="下滑")
        down_btn.connect("clicked", self.on_down_btn_clicked)
        grid.attach(down_btn, 2, 2, 1, 1)
        # (2,3) 返回按钮
        back_btn = Gtk.Button(label="返回")
        back_btn.connect("clicked", self.on_back_btn_clicked)
        grid.attach(back_btn, 3, 2, 1, 1)
        # (0,3) 刷新按钮
        refresh_btn = Gtk.Button(label="刷新")
        refresh_btn.connect("clicked", self.on_refresh_btn_clicked)
        grid.attach(refresh_btn, 3, 0, 1, 1)
        # (1,3) 屏幕信息标签
        self.screen_info_label = Gtk.Label("")
        grid.attach(self.screen_info_label, 3, 1, 1, 1)
        self.set_dynamic_bg()  # 初始化时设置背景色
        self.update_screen_info()

    def on_select(self, selected_box, idx):
        for i, box in enumerate(self.selectable_boxes):
            box.set_selected(box is selected_box)
        if self.screen_width and self.screen_height:
            x, y = self.region_centers[idx]
            cmd = ["adb", "shell", "input", "tap", str(x), str(y)]
            print(f"执行命令: {' '.join(cmd)}")
            subprocess.Popen(cmd)

    def on_up_btn_clicked(self, button):
        subprocess.Popen(["adb", "shell", "input", "swipe", "500", "1500", "500", "500"])  # 上滑

    def on_down_btn_clicked(self, button):
        subprocess.Popen(["adb", "shell", "input", "swipe", "500", "500", "500", "1500"])  # 下滑

    def on_lock_btn_clicked(self, button):
        subprocess.Popen(["adb", "shell", "input", "keyevent", "26"])  # 锁屏

    def on_back_btn_clicked(self, button):
        cmd = ["adb", "shell", "input", "keyevent", "4"]
        print(f"执行命令: {' '.join(cmd)}")
        subprocess.Popen(cmd)

    def on_refresh_btn_clicked(self, button):
        self.set_dynamic_bg()
        self.update_screen_info()

    def update_screen_info(self):
        # 获取设备屏幕尺寸
        try:
            result = subprocess.run(["adb", "shell", "wm", "size"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            print(f"adb shell wm size 输出: {result.stdout.strip()}")
            if result.returncode == 0 and "Physical size" in result.stdout:
                size = result.stdout.strip().split(":")[-1].strip()
                self.screen_info_label.set_text(f"屏幕尺寸: {size}")
                w, h = size.split('x')
                self.screen_width = int(w)
                self.screen_height = int(h)
                print(f"解析到的屏幕宽高: w={self.screen_width}, h={self.screen_height}")
                self.calc_region_centers()
            else:
                self.screen_info_label.set_text("无法获取屏幕尺寸")
                self.screen_width = self.screen_height = None
        except Exception as e:
            print(f"获取屏幕尺寸异常: {e}")
            self.screen_info_label.set_text("无法获取屏幕尺寸")
            self.screen_width = self.screen_height = None

    def calc_region_centers(self):
        # 3行2列，6个区域，计算中心点，顺序与A~F一致
        if self.screen_width and self.screen_height:
            w = self.screen_width
            h = self.screen_height
            region_w = w // 2
            region_h = h // 3
            self.region_centers = [
                (region_w//2, region_h//2),                # A (0,0)
                (region_w+region_w//2, region_h//2),       # B (0,1)
                (region_w//2, region_h+region_h//2),       # C (1,0)
                (region_w+region_w//2, region_h+region_h//2), # D (1,1)
                (region_w//2, region_h*2+region_h//2),     # E (2,0)
                (region_w+region_w//2, region_h*2+region_h//2) # F (2,1)
            ]
            print(f"region_centers: {self.region_centers}")
        else:
            self.region_centers = [(0,0)]*6
            print("region_centers: 全为(0,0)")

    def set_dynamic_bg(self):
        # 检查adb设备数量
        try:
            result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            lines = result.stdout.strip().split("\n")
            devices = [line for line in lines[1:] if line.strip() and '\tdevice' in line]
            if len(devices) == 1:
                color = "#d4e7c5"  # 淡绿
            elif len(devices) == 0:
                color = "#ffe5e5"  # 淡红
            else:
                color = "#fff9d1"  # 淡黄
        except Exception:
            color = "#ffe5e5"  # adb异常也视为无设备
        css = f"#mainwindow {{ background-color: {color}; }}".encode()
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        self.get_style_context().add_provider(style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

if __name__ == "__main__":
    win = MyWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
