import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte, GLib, Gdk

class TerminalWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shell by GroupXyz")
        self.set_default_size(800, 600)

        self.set_border_width(0)

        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)

        self.notebook = Gtk.Notebook()
        self.notebook.set_border_width(0)  # Remove border width for notebook
        self.add(self.notebook)

        self.tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.plus_button = Gtk.Button(label="+")
        self.plus_button.set_size_request(40, 30)  # Adjust size as needed
        self.plus_button.connect("clicked", self.on_add_tab_button_clicked)

        self.add_terminal_tab()

        self.update_tab_bar()

        self.connect("key-press-event", self.on_key_press)

    def add_terminal_tab(self):
        """Add a new terminal tab."""
        terminal = Vte.Terminal()
        terminal.set_size_request(800, 600)
        terminal.set_scroll_on_output(True)
        terminal.set_scrollback_lines(1000)

        self.apply_custom_css(terminal)

        terminal.connect("child-exited", self.on_child_exited)
        terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            None,  # Working directory
            ["/bin/bash"],  # Command to run
            None,  # Environment variables
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,  # Child setup function
            None,  # Child setup user data
            -1,  # Timeout (-1 for no timeout)
            None,  # Cancellable
            self.on_spawn_complete,  # Callback function
            terminal  # User data for the callback
        )

        tab_label = Gtk.Box()
        tab_label_text = Gtk.Label(label=f"Terminal {self.notebook.get_n_pages() + 1}")
        close_button = Gtk.Button(label="x")
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.connect("clicked", self.on_tab_close, terminal)
        tab_label.pack_start(tab_label_text, True, True, 0)
        tab_label.pack_end(close_button, False, False, 0)
        tab_label.show_all()

        self.notebook.append_page(terminal, tab_label)
        self.notebook.set_current_page(self.notebook.get_n_pages() - 1)
        self.update_tab_bar()

    def apply_custom_css(self, terminal):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            VteTerminal {
                font-family: Monospace;
                font-size: 12pt;
            }
        """)
        style_context = terminal.get_style_context()
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def on_spawn_complete(self, terminal, success, child_pid):
        if not success:
            print("Failed to spawn the terminal process.")

    def on_child_exited(self, terminal, status):
        print("Child process exited with status:", status)
        page_num = self.notebook.page_num(terminal)
        if page_num != -1:
            self.notebook.remove_page(page_num)
        if self.notebook.get_n_pages() == 0:
            Gtk.main_quit()

    def on_tab_close(self, button, terminal):
        page_num = self.notebook.page_num(terminal)
        if page_num != -1:
            self.notebook.remove_page(page_num)
        if self.notebook.get_n_pages() == 0:
            Gtk.main_quit()

    def on_add_tab_button_clicked(self, button):
        self.add_terminal_tab()

    def update_tab_bar(self):
        for child in self.tab_box.get_children():
            self.tab_box.remove(child)
        
        for i in range(self.notebook.get_n_pages()):
            tab_label = self.notebook.get_tab_label(self.notebook.get_nth_page(i))
            if tab_label:  # Ensure tab_label is not None
                self.tab_box.pack_start(tab_label, True, True, 0)

        self.tab_box.pack_end(self.plus_button, False, False, 0)
        self.tab_box.show_all()

    def on_key_press(self, widget, event):
        keyval = event.keyval
        state = event.state

        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        if ctrl and keyval == Gdk.KEY_T:
            self.add_terminal_tab()
        elif ctrl and keyval == Gdk.KEY_W:
            current_page = self.notebook.get_current_page()
            if current_page != -1:
                terminal = self.notebook.get_nth_page(current_page)
                self.on_tab_close(None, terminal)
        elif ctrl and keyval == Gdk.KEY_Q:
            Gtk.main_quit()

if __name__ == "__main__":
    win = TerminalWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
