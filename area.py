import pickle
import re
import tkinter as tk
from abc import ABC, abstractmethod
from tkinter import filedialog as fd
from tkinter import ttk
from typing import Callable

# Custom datatype aliases
InputRow = tuple[float, float, float]
InputData = list[InputRow]
StoreRowType = tuple[tk.StringVar, tk.StringVar, tk.StringVar]
StorageType = dict[int, StoreRowType]


class Store:
    """class definition for Store. Store the core data and helps to transform
    data for file handling."""

    def __init__(self) -> None:
        self.storage: StorageType = {}

    @property
    def units(self):
        """an readonly class property which contains all the input unit data

        Returns:
            dict: database of unit convertion logic
        """
        return {
            0: {"name": "Inches", "symbol": "in", "calc": lambda x: x / (12**2)},
            1: {
                "name": "Centimeter",
                "symbol": "cm",
                "calc": lambda x: x * (0.032808399**2),
            },
        }

    def add(self, values: StoreRowType) -> Callable[[ttk.Frame], Callable[[], None]]:
        """Add a tuple of values to storage.

        Args:
            values (StoreRowType): tuple of values of entries

        Returns:
            Callable[[ttk.Frame], Callable[[], None]]: a callable function to be
        called when the row is to be destroyed.
        """
        id = len(self.storage)
        self.storage[id] = values

        # row destruction function
        def delete_row(frame: ttk.Frame) -> Callable[[], None]:
            def destroy():
                frame.destroy()
                del self.storage[id]

            return destroy

        return delete_row

    def clear(self):
        """clear the data in storage"""
        self.storage.clear()

    def to_float(self, strvar: tk.StringVar) -> float:
        """convert content in string variable instance to float

        Args:
            strvar (tk.StringVar): an instance of string variable

        Returns:
            float: converted float value
        """
        try:
            return float(strvar.get())
        except:
            return 0.0

    def values(self) -> InputData:
        """transform items in storage to iteratable list of basic datatypes.

        Returns:
            InputData: a datatype which is iteratable and serialisable
        """
        converted: InputData = []
        for _, row in self.storage.items():
            converted.append(tuple(self.to_float(r) for r in row))
        return converted


class Window(tk.Tk, ABC):
    """Base class which is used for creating tkinter UI with some abstract
    functions. This class inherits Tk root class and Abstract class.
    """

    def __init__(self, title, *args, input_data: InputData = [], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._config(title)
        self._set_variables()
        self._load_menu()
        self._load_bindings()
        self._load_window(input_data)
        self._calc()

    def _set_variables(self):
        """set variables for the UI to run."""
        self._input_frame = ttk.Frame(self)
        self._result = tk.StringVar(master=self)
        self._filetypes = (("Area files", "*.area"), ("All files", "*.*"))
        self._store = Store()
        self.unit_id = tk.IntVar(self, value=0)

    def _load_bindings(self):
        """add key binding to UI"""
        self.bind("<space>", self._calc)
        self.bind("<Return>", self._load_row)
        self.bind("<KP_Enter>", self._load_row)

    def _convert_to_feet(self, value: float) -> float:
        """convert the area value to square feets according to the unit selected.

        Args:
            value (float): area value

        Returns:
            float: area value in square feet
        """
        unit = self._store.units[self.unit_id.get()]
        return round(unit["calc"](value), 2)

    def _load_result(self, result: float):
        """set value of result widget to converted value

        Args:
            result (float): calculated value from input
        """
        unit = self._store.units[self.unit_id.get()]
        self._result.set(
            "Square {}: {}, Square Feets: {}".format(
                unit["name"], result, self._convert_to_feet(result)
            )
        )

    def _config(self, title: str):
        """set the UI configurations

        Args:
            title (str): title of the window
        """
        self.title(title)
        self.resizable(False, True)
        self.minsize(400, 111)

    def _load_menu(self):
        """add menu to UI"""
        self.menu = tk.Menu(self)
        self.menu.bind("<Control-q>", lambda e: self.menu.quit())
        self.config(menu=self.menu)

        # Menu items
        self.menu.add_command(label="New", command=self._new)
        self.menu.add_command(label="Open", command=self._load)
        self.menu.add_command(label="Save", command=self._save)
        self.menu.add_command(label="Exit", command=self.menu.quit)

    def _load_window(self, input_data: InputData):
        """create UI elements in the window.

        Args:
            input_data (InputData): initial data if given
        """

        # Add input unit
        unit_frame = ttk.Frame(self)
        unit_frame.pack(fill=tk.X)
        ttk.Label(unit_frame, text="Input unit: ", padding=4).pack(side=tk.LEFT)
        ttk.Radiobutton(
            unit_frame,
            text="Inch",
            variable=self.unit_id,
            value=0,
            padding=4,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            unit_frame,
            text="Centimeter",
            variable=self.unit_id,
            value=1,
            padding=4,
        ).pack(side=tk.LEFT)

        # Add entry button
        add_button = ttk.Button(self, text="Add Input Row", width=46)
        add_button["command"] = self._load_row
        add_button.pack(fill=tk.X)

        # Main entry frame
        self._input_frame.pack(expand=True, fill=tk.BOTH)
        if len(input_data) < 1:
            self._load_row()
        else:
            for row in input_data:
                self._load_row(values=row)

        # Caculate button
        add_button = ttk.Button(self, text="Calculate", width=46)
        add_button["command"] = self._calc
        add_button.pack(fill=tk.X)

        # Status bar
        ttk.Label(
            self, textvariable=self._result, relief=tk.SUNKEN, borderwidth=1
        ).pack(side=tk.BOTTOM, fill=tk.X)

    def _clear_input(self):
        """clear the input elements and clear the storage"""
        for child in self._input_frame.winfo_children():
            child.destroy()
        self._store.clear()

    def _validate_entry(self, new_val: str, val: str, key: str) -> bool:
        """validate if the value entered is a floating point value

        Args:
            new_val (str): the value resulted after the addition of key
            val (str): the value of the target before addition of key
            key (str): the key pressed by user

        Returns:
            bool: True if value typed is floating point. Otherwise False
        """
        is_digit = key.isdigit()
        if new_val == "":
            return True
        if val == "":
            return is_digit
        if not (is_digit or key == "."):
            return False
        r = re.match(r"^\d+\.?\d*$", new_val)
        if r:
            return True
        return False

    def _load_entry(
        self, frame: ttk.Frame, pos: int, focus=False, text=""
    ) -> tk.StringVar:
        """create a tkinter Entry widget using StringVar and return the StringVar.

        Args:
            frame (ttk.Frame): parent frame
            pos (int): column position in the row
            focus (bool, optional): should the element be focused on creation. Defaults to False.
            text (str, optional): initial text to be set in the entry widget. Defaults to "".

        Returns:
            tk.StringVar: text variable of the entry widget
        """
        self._text = tk.StringVar(master=self, value=text)
        self._widget = tk.Entry(
            frame,
            width=10,
            validate="key",
            validatecommand=(frame.register(self._validate_entry), "%P", "%s", "%S"),
            textvariable=self._text,
        )

        # add widget to grid
        self._widget.grid(row=0, column=pos, padx=4)

        # set focus of widget if True
        if focus:
            self._widget.focus_set()
        return self._text

    def _load_row(self, e=None, values: InputRow = tuple()):
        """add row of input fields and add the string variable to storage

        Args:
            e (Event, optional): key binding event. Defaults to None.
            values (InputRow, optional): initial input values for the row. Defaults to tuple().
        """
        length, width, count = 0.0, 0.0, 1.0
        if len(values) == 3:
            length, width, count = values

        # Defined local functions
        e = lambda x: "" if x == 0.0 else str(x)
        xlabel = lambda f, p: ttk.Label(f, text="x", width=1).grid(row=0, column=p)

        # Create row frame
        row = ttk.Frame(self._input_frame, padding=4)
        row.pack()

        # Create row elements
        text_length = self._load_entry(row, 0, True, text=e(length))
        xlabel(row, 1)
        text_width = self._load_entry(row, 2, text=e(width))
        xlabel(row, 3)
        text_count = self._load_entry(row, 4, text=e(count))

        # Add string variables to storage
        delete_row = self._store.add((text_length, text_width, text_count))

        # Delete button
        remove_button = ttk.Button(row, text="Delete")
        remove_button["command"] = delete_row(row)
        remove_button.grid(row=0, column=5, padx=4)

    @abstractmethod
    def _calc(self, e=None):
        """area calculation function to be implemented by the child class"""

    @abstractmethod
    def _new(self):
        """new window function to be implemented by the child class"""

    @abstractmethod
    def _load(self):
        """file load function to be implemented by the child class"""

    @abstractmethod
    def _save(self):
        """file save function to be implemented by the child class"""


class UI(Window):
    def __init__(self, app, *args, **kwargs):
        super().__init__(app.title, *args, input_data=app.input, **kwargs)
        self.app = app

    def __call__(self):
        self.mainloop()

    def _calc(self, e=None):
        """calculate the area from each row values and load result

        Args:
            e (Event, optional): key binding event. Defaults to None.
        """
        result = 0.0
        for row in self._store.values():
            result += row[0] * row[1] * row[2]
        self._load_result(result)

    def _new(self):
        """create new app window"""
        App()

    def _load(self):
        """load data from file"""
        data: InputData | None = None

        # run file open dialogue UI
        filename = fd.askopenfilename(
            title="Open a file",
            filetypes=self._filetypes,
            parent=self.menu,
        )

        # load binary file
        try:
            with open(filename, "rb") as fp:
                data = pickle.load(fp)
        except:
            print("Failed to load file")
            return

        # load data in to UI
        if data is not None:
            self._clear_input()
            unit, data = data[0], data[1:]
            self.unit_id.set(int(unit[2]))
            for row in data:
                self._load_row(values=row)
            self._calc()

    def _save(self):
        """save data to file"""

        # run file save dialogue UI
        filename = fd.asksaveasfilename(
            initialfile="Untitled.area",
            defaultextension=".area",
            filetypes=self._filetypes,
            parent=self.menu,
        )

        # get values from store and save it as binary file
        try:
            data = self._store.values()
            data.insert(0, (-1, -1, self.unit_id.get()))
            with open(filename, "wb") as fp:
                pickle.dump(data, fp)
        except:
            print("Failed to save file")


class App:
    """class defines an App with UI"""

    def __init__(self, entrylist: InputData = [], *args, **kwargs) -> None:
        self.title = "Area App"
        self.input = entrylist

        # Allow UI to create independent new windows
        tk.NoDefaultRoot()

        # create UI window and display it
        self.ui = UI(self, *args, **kwargs)
        self.ui()


if __name__ == "__main__":
    App()
