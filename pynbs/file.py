__all__ = [
    "read",
    "new_file",
    "Parser",
    "Writer",
    "File",
    "Header",
    "Note",
    "Layer",
    "Instrument",
    "SoundStopper",
    "TempoChange",
    "ToggleRainbow",
    "ColorChange",
    "ToggleBackgroundAccent",
    "ShowSavePopup",
]


from dataclasses import dataclass, replace
from math import isfinite
from struct import Struct

CURRENT_NBS_VERSION = 6

# control_create.gml, in on-disk instrument order.
DEFAULT_INSTRUMENTS = (
    ("Harp", "harp"),
    ("Double Bass", "dbass"),
    ("Bass Drum", "bdrum"),
    ("Snare Drum", "sdrum"),
    ("Click", "click"),
    ("Guitar", "guitar"),
    ("Flute", "flute"),
    ("Bell", "bell"),
    ("Chime", "icechime"),
    ("Xylophone", "xylobone"),
    ("Iron Xylophone", "iron_xylophone"),
    ("Cow Bell", "cow_bell"),
    ("Didgeridoo", "didgeridoo"),
    ("Bit", "bit"),
    ("Banjo", "banjo"),
    ("Pling", "pling"),
    ("Trumpet", "trumpet"),
    ("Exposed Trumpet", "trumpet_exposed"),
    ("Weathered Trumpet", "trumpet_weathered"),
    ("Oxidized Trumpet", "trumpet_oxidized"),
)

BYTE = Struct("<B")
SHORT = Struct("<H")
SSHORT = Struct("<h")
INT = Struct("<I")


@dataclass
class Instrument:
    id: int
    name: str
    file: str
    pitch: int = 45
    press_key: bool = True


@dataclass
class Note:
    tick: int
    layer: int
    instrument: int
    key: int
    velocity: int = 100
    panning: int = 0
    pitch: int = 0


@dataclass
class Layer:
    id: int
    name: str = ""
    lock: int = 0  # 0: normal, 1: locked, 2: solo (bool inputs remain valid)
    volume: int = 100
    panning: int = 0


@dataclass(frozen=True)
class SoundStopper:
    tick: int
    layer: int
    start_layer: int
    end_layer: int

    def affects_layer(self, layer):
        """Test a zero-based pynbs layer using NBS's playback rules."""
        start = max(0, self.start_layer)
        return start == 0 or start <= layer + 1 <= max(start, self.end_layer)


@dataclass(frozen=True)
class TempoChange:
    tick: int
    layer: int
    tempo: float


@dataclass(frozen=True)
class ToggleRainbow:
    tick: int
    layer: int


@dataclass(frozen=True)
class ColorChange:
    tick: int
    layer: int
    red: int
    green: int
    blue: int


@dataclass(frozen=True)
class ToggleBackgroundAccent:
    tick: int
    layer: int


@dataclass(frozen=True)
class ShowSavePopup:
    """Display the 'Song saved' message; does not save the file."""

    tick: int
    layer: int


_NAMED_EVENTS = {
    "Toggle Rainbow": ToggleRainbow,
    "Toggle Background Accent": ToggleBackgroundAccent,
    "Show Save Popup": ShowSavePopup,
}


def read(filename):
    with open(filename, "rb") as fileobj:
        return Parser(fileobj).read_file()


def new_file(**header):
    if "default_instruments" not in header:
        version = header.get("version", CURRENT_NBS_VERSION)
        header["default_instruments"] = 20 if version >= 6 else 16 if version else 10
    return File(Header(**header), [], [Layer(0, "", False, 100, 0)], [])


@dataclass
class Header:
    version: int = CURRENT_NBS_VERSION
    default_instruments: int = 20
    song_length: int = 0
    song_layers: int = 0
    song_name: str = ""
    song_author: str = ""
    original_author: str = ""
    description: str = ""
    tempo: float = 10.0
    auto_save: bool = False
    auto_save_duration: int = 10
    time_signature: int = 4
    minutes_spent: int = 0
    left_clicks: int = 0
    right_clicks: int = 0
    blocks_added: int = 0
    blocks_removed: int = 0
    song_origin: str = ""
    loop: bool = False
    max_loop_count: int = 0
    loop_start: int = 0


class File:
    def __init__(self, header, notes, layers, instruments):
        self.header = header
        self.notes = notes
        self.layers = layers
        self.instruments = instruments

    def get_custom_instrument(self, note):
        """Resolve a note's absolute instrument index to a custom instrument."""
        index = note.instrument - self.header.default_instruments
        return self.instruments[index] if 0 <= index < len(self.instruments) else None

    def iter_events(self):
        """Yield recognized playback/UI events in tick/layer order.

        Raw notes, including malformed color events, are always preserved.
        """
        for note in sorted(self.notes, key=lambda n: (n.tick, n.layer)):
            instrument = self.get_custom_instrument(note)
            if instrument is None:
                continue
            if instrument.name == "Sound Stopper":
                end = note.panning % 256 + ((note.velocity - 100) % 256) * 256
                yield SoundStopper(note.tick, note.layer, note.pitch, end)
            elif instrument.name == "Tempo Changer":
                yield TempoChange(note.tick, note.layer, abs(note.pitch) / 15)
            elif instrument.name in _NAMED_EVENTS:
                yield _NAMED_EVENTS[instrument.name](note.tick, note.layer)
            elif instrument.name.lower().count("change color to #") == 1:
                # NBS dispatch searches case-insensitively, then reads fixed positions.
                color = instrument.name[17:23]
                if len(color) == 6 and all(
                    c in "0123456789abcdefABCDEF" for c in color
                ):
                    yield ColorChange(
                        note.tick,
                        note.layer,
                        *(int(color[i : i + 2], 16) for i in (0, 2, 4)),
                    )

    def _add_event_note(self, name, tick, layer, velocity, panning, pitch):
        if not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative integer")
        if not isinstance(layer, int) or not 0 <= layer < 65535:
            raise ValueError("layer must be an integer between 0 and 65534")
        if any(n.tick == tick and n.layer == layer for n in self.notes):
            raise ValueError("A note already occupies this tick and layer")
        index = next(
            (i for i, ins in enumerate(self.instruments) if ins.name == name), None
        )
        if index is None:
            index = len(self.instruments)
            if index >= 255 or self.header.default_instruments + index > 255:
                raise ValueError("No free custom instrument slot")
            self.instruments.append(Instrument(index, name, "", press_key=False))
        while len(self.layers) <= layer:
            self.layers.append(Layer(len(self.layers)))
        note = Note(
            tick,
            layer,
            self.header.default_instruments + index,
            45,
            velocity,
            panning,
            pitch,
        )
        self.notes.append(note)
        return note

    def add_sound_stopper(self, tick, layer, start_layer=0, end_layer=0):
        """Add a stopper. Range is 1-based and inclusive; start=0 stops all."""
        for value in (start_layer, end_layer):
            if not isinstance(value, int) or not 0 <= value < 32768:
                raise ValueError("Stopping range must contain integers from 0 to 32767")
        pan = ((end_layer % 256 + 100) % 256) - 100
        vel = (end_layer // 256 + 100) % 256
        return self._add_event_note("Sound Stopper", tick, layer, vel, pan, start_layer)

    def add_tempo_change(self, tick, layer, tempo):
        """Add ticks/second tempo, quantized to the nearest 1/15 tick/second."""
        if not isfinite(tempo) or not 1 <= round(tempo * 15) <= 32767:
            raise ValueError(
                "tempo must fit a positive signed short after multiplying by 15"
            )
        return self._add_event_note(
            "Tempo Changer", tick, layer, 100, 0, round(tempo * 15)
        )

    def add_toggle_rainbow(self, tick, layer):
        """Toggle NBS's rainbow accent effect at this position."""
        return self._add_event_note("Toggle Rainbow", tick, layer, 100, 0, 0)

    def add_color_change(self, tick, layer, red, green, blue):
        """Set the NBS accent color using RGB components in the range 0..255."""
        if any(not isinstance(c, int) or not 0 <= c <= 255 for c in (red, green, blue)):
            raise ValueError("RGB components must be integers from 0 to 255")
        name = "Change Color to #{:02X}{:02X}{:02X}".format(red, green, blue)
        return self._add_event_note(name, tick, layer, 100, 0, 0)

    def add_toggle_background_accent(self, tick, layer):
        """Toggle NBS's background accent effect."""
        return self._add_event_note("Toggle Background Accent", tick, layer, 100, 0, 0)

    def add_show_save_popup(self, tick, layer):
        """Add a 'Song saved' notification event, without saving anything."""
        return self._add_event_note("Show Save Popup", tick, layer, 100, 0, 0)

    def update_header(self, version):
        self.header.version = version
        if self.notes:
            self.header.song_length = max(n.tick for n in self.notes)
        self.header.song_layers = len(self.layers)

    def save(self, filename, version=CURRENT_NBS_VERSION):
        # Validate/convert before opening the destination (and potentially truncating it).
        prepared = self._for_version(version)
        self.update_header(version)
        prepared.update_header(version)
        with open(filename, "wb") as fileobj:
            Writer(fileobj).encode_file(prepared, version)

    def _for_version(self, version):
        if version not in range(CURRENT_NBS_VERSION + 1):
            raise ValueError("Supported NBS versions are 0 through 6")
        if version < 4 and any(
            isinstance(event, (SoundStopper, TempoChange))
            for event in self.iter_events()
        ):
            raise ValueError(
                "Event instruments with pitch/range data require NBS version 4 or later"
            )
        target = (
            10
            if version == 0
            else 16
            if version < 6
            else self.header.default_instruments
        )
        source = self.header.default_instruments
        if source <= target:
            return File(replace(self.header), self.notes, self.layers, self.instruments)
        if source > len(DEFAULT_INSTRUMENTS):
            raise ValueError("Cannot downgrade unknown built-in instruments")
        extra = []
        if any(target <= n.instrument < source for n in self.notes):
            extra = [
                Instrument(i, name, sound + ".ogg")
                for i, (name, sound) in enumerate(DEFAULT_INSTRUMENTS[target:source])
            ]
        shift = source - target - len(extra)
        notes = [
            replace(n, instrument=n.instrument - shift) if n.instrument >= source else n
            for n in self.notes
        ]
        instruments = extra + [
            replace(ins, id=i + len(extra)) for i, ins in enumerate(self.instruments)
        ]
        if len(instruments) > 255:
            raise ValueError("Too many custom instruments for the target version")
        return File(
            replace(self.header, default_instruments=target),
            notes,
            self.layers,
            instruments,
        )

    def __iter__(self):
        if not self.notes:
            return
        chord = []
        ordered = sorted(self.notes, key=lambda n: (n.tick, n.layer))
        current_tick = ordered[0].tick

        for note in ordered:
            if note.tick == current_tick:
                chord.append(note)
            else:
                chord.sort(key=lambda n: n.layer)
                yield current_tick, chord
                current_tick, chord = note.tick, [note]
        yield current_tick, chord


class Parser:
    def __init__(self, fileobj):
        self.fileobj = fileobj

    def read_file(self):
        header = self.parse_header()
        version = header.version
        return File(
            header,
            list(self.parse_notes(version)),
            list(self.parse_layers(header.song_layers, version)),
            list(self.parse_instruments(version)),
        )

    def read_numeric(self, fmt):
        return fmt.unpack(self.fileobj.read(fmt.size))[0]

    def read_string(self):
        length = self.read_numeric(INT)
        return self.fileobj.read(length).decode(encoding="cp1252")

    def jump(self):
        value = -1
        while True:
            jump = self.read_numeric(SHORT)
            if not jump:
                break
            value += jump
            yield value

    def parse_header(self):
        song_length = self.read_numeric(SHORT)
        if song_length == 0:
            # A song length of 0 indicates the Open Note Block Studio format
            version = self.read_numeric(BYTE)
        else:
            version = 0

        if version > CURRENT_NBS_VERSION:
            raise ValueError("Unsupported NBS version: {}".format(version))

        return Header(
            version=version,
            default_instruments=self.read_numeric(BYTE) if version > 0 else 10,
            song_length=self.read_numeric(SHORT) if version >= 3 else song_length,
            song_layers=self.read_numeric(SHORT),
            song_name=self.read_string(),
            song_author=self.read_string(),
            original_author=self.read_string(),
            description=self.read_string(),
            tempo=self.read_numeric(SHORT) / 100.0,
            auto_save=self.read_numeric(BYTE) == 1,
            auto_save_duration=self.read_numeric(BYTE),
            time_signature=self.read_numeric(BYTE),
            minutes_spent=self.read_numeric(INT),
            left_clicks=self.read_numeric(INT),
            right_clicks=self.read_numeric(INT),
            blocks_added=self.read_numeric(INT),
            blocks_removed=self.read_numeric(INT),
            song_origin=self.read_string(),
            loop=self.read_numeric(BYTE) == 1 if version >= 4 else False,
            max_loop_count=self.read_numeric(BYTE) if version >= 4 else 0,
            loop_start=self.read_numeric(SHORT) if version >= 4 else 0,
        )

    def parse_notes(self, version):
        for current_tick in self.jump():
            for current_layer in self.jump():
                instrument = self.read_numeric(BYTE)
                key = self.read_numeric(BYTE)
                velocity = self.read_numeric(BYTE) if version >= 4 else 100
                panning = self.read_numeric(BYTE) - 100 if version >= 4 else 0
                pitch = self.read_numeric(SSHORT) if version >= 4 else 0
                yield Note(
                    current_tick,
                    current_layer,
                    instrument,
                    key,
                    velocity,
                    panning,
                    pitch,
                )

    def parse_layers(self, layers_count, version):
        for i in range(layers_count):
            name = self.read_string()
            lock = self.read_numeric(BYTE) if version >= 4 else 0
            volume = self.read_numeric(BYTE)
            panning = self.read_numeric(BYTE) - 100 if version >= 2 else 0
            yield Layer(i, name, lock, volume, panning)

    def parse_instruments(self, version):
        for i in range(self.read_numeric(BYTE)):
            name = self.read_string()
            sound_file = self.read_string()
            pitch = self.read_numeric(BYTE)
            press_key = self.read_numeric(BYTE) == 1
            yield Instrument(i, name, sound_file, pitch, press_key)


class Writer:
    def __init__(self, fileobj):
        self.fileobj = fileobj

    def encode_file(self, nbs_file, version):
        self.write_header(nbs_file, version)
        self.write_notes(nbs_file, version)
        self.write_layers(nbs_file, version)
        self.write_instruments(nbs_file, version)

    def encode_numeric(self, fmt, value):
        self.fileobj.write(fmt.pack(value))

    def encode_string(self, value):
        self.encode_numeric(INT, len(value))
        self.fileobj.write(value.encode(encoding="cp1252"))

    def write_header(self, nbs_file, version):
        header = nbs_file.header

        if version > 0:
            self.encode_numeric(SHORT, 0)
            self.encode_numeric(BYTE, version)
            self.encode_numeric(BYTE, header.default_instruments)
        else:
            self.encode_numeric(SHORT, header.song_length)
        if version >= 3:
            self.encode_numeric(SHORT, header.song_length)
        self.encode_numeric(SHORT, header.song_layers)
        self.encode_string(header.song_name)
        self.encode_string(header.song_author)
        self.encode_string(header.original_author)
        self.encode_string(header.description)

        self.encode_numeric(SHORT, int(header.tempo * 100))
        self.encode_numeric(BYTE, int(header.auto_save))
        self.encode_numeric(BYTE, header.auto_save_duration)
        self.encode_numeric(BYTE, header.time_signature)

        self.encode_numeric(INT, header.minutes_spent)
        self.encode_numeric(INT, header.left_clicks)
        self.encode_numeric(INT, header.right_clicks)
        self.encode_numeric(INT, header.blocks_added)
        self.encode_numeric(INT, header.blocks_removed)
        self.encode_string(header.song_origin)

        if version >= 4:
            self.encode_numeric(BYTE, int(header.loop))
            self.encode_numeric(BYTE, header.max_loop_count)
            self.encode_numeric(SHORT, header.loop_start)

    def write_notes(self, nbs_file, version):
        current_tick = -1

        for tick, chord in nbs_file:
            self.encode_numeric(SHORT, tick - current_tick)
            current_tick = tick
            current_layer = -1

            for note in chord:
                self.encode_numeric(SHORT, note.layer - current_layer)
                current_layer = note.layer
                self.encode_numeric(BYTE, note.instrument)
                self.encode_numeric(BYTE, note.key)
                if version >= 4:
                    self.encode_numeric(BYTE, note.velocity)
                    self.encode_numeric(BYTE, note.panning + 100)
                    self.encode_numeric(SSHORT, note.pitch)

            self.encode_numeric(SHORT, 0)
        self.encode_numeric(SHORT, 0)

    def write_layers(self, nbs_file, version):
        for layer in nbs_file.layers:
            self.encode_string(layer.name)
            if version >= 4:
                self.encode_numeric(BYTE, int(layer.lock))
            self.encode_numeric(BYTE, layer.volume)
            if version >= 2:
                self.encode_numeric(BYTE, layer.panning + 100)

    def write_instruments(self, nbs_file, version):
        self.encode_numeric(BYTE, len(nbs_file.instruments))
        for instrument in nbs_file.instruments:
            self.encode_string(instrument.name)
            self.encode_string(instrument.file)
            self.encode_numeric(BYTE, instrument.pitch)
            self.encode_numeric(BYTE, int(instrument.press_key))
