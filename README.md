# pynbs

English | [한국어](README_KO.md)

[![CI](https://github.com/NoteBlockMR/pynbs-v6/actions/workflows/main.yml/badge.svg)](https://github.com/NoteBlockMR/pynbs-v6/actions/workflows/main.yml)

This repository is a fork of [OpenNBS/pynbs](https://github.com/OpenNBS/pynbs),
extended for **NBS format v6 and NoteBlockStudio 3.12.0-beta.5 event instruments**.
The Python import name remains `pynbs`; `pynbs-v6` is the repository name.

Use it to inspect songs, edit notes and metadata, generate NBS files, and build
tools that interpret Sound Stopper, Tempo Changer, and visual events. It is a
file-format library, not an audio player, sound renderer, or Minecraft mod.

> A simple python library to read and write [.nbs files](https://opennbs.org/nbs)
> from [Open Note Block Studio](https://opennbs.org/).

`pynbs` makes it possible to easily iterate over Note Block Studio songs.

```python
import pynbs

for tick, chord in pynbs.read('demo_song.nbs'):
    print(tick, [note.key for note in chord])
```

You can also use `pynbs` to generate new songs programmatically.

```python
import pynbs

new_file = pynbs.new_file(song_name='Hello world')
new_file.notes.extend([
    pynbs.Note(tick=i, layer=0, instrument=0, key=i + 35) for i in range(10)
])

new_file.save('new_file.nbs')
```

## Installation

Use **Python 3.8 or later (below 4.0)**. There are no third-party runtime
dependencies. Install this fork directly from GitHub; the command requires Git:

```bash
python -m pip install "git+https://github.com/NoteBlockMR/pynbs-v6.git"
```

`pip install pynbs` selects the package on PyPI, not specifically this fork.
For local development:

```bash
git clone https://github.com/NoteBlockMR/pynbs-v6.git
cd pynbs-v6
python -m pip install -e .
```

Confirm which copy Python imports and whether the event API is available:

```python
import pynbs

print(pynbs.__file__)
assert hasattr(pynbs.File, "add_sound_stopper")
assert pynbs.new_file().header.version == 6
```

For repeatable deployments, replace the Git URL with
`git+https://github.com/NoteBlockMR/pynbs-v6.git@<commit>` using a specific commit.

This fork reads and writes **NBS versions 0–6**. New files and `save()` default
to v6. The compatibility target is the implementation in NoteBlockStudio
3.12.0-beta.5; support for future format changes is not implied.

## Quick start: create, save, and read

This example creates a melody and an event on a separate layer, then reads the
saved file back. At the default tempo of 10 ticks/second, tick 10 is one second
after tick 0, provided no tempo changes occur.

```python
import pynbs

song = pynbs.new_file(song_name="Example melody", song_author="Your name", tempo=10.0)
song.layers = [pynbs.Layer(0, "Melody"), pynbs.Layer(1, "Events")]
song.notes.extend([
    pynbs.Note(tick=0, layer=0, instrument=0, key=45),
    pynbs.Note(tick=10, layer=0, instrument=0, key=49),
])
song.add_sound_stopper(tick=20, layer=1, start_layer=1, end_layer=1)
song.save("example.nbs", version=6)

loaded = pynbs.read("example.nbs")
print(loaded.header.song_name, len(loaded.notes))  # Example melody 3
for event in loaded.iter_events():
    if isinstance(event, pynbs.SoundStopper):
        print(event.tick, event.affects_layer(0))  # 20 True
```

The third raw note is the stopper itself. Creating an event stores its data;
it does not stop audio inside Python. A player must implement that behavior.

### NBS v6 and event instruments

New files use version 6 and 20 built-in instruments, including the four trumpet
variants (IDs 16–19). Loaded files retain their original instrument indices.
Saving to v0–v5 remaps custom indices and, if needed, includes the newer built-in
instruments as custom instruments. Their `.ogg` files must be available to the
player. Sound Stopper and Tempo Changer notes require v4 or later; saving them to older formats raises
`ValueError` before opening the destination.

```python
song = pynbs.new_file()
song.notes.append(pynbs.Note(tick=0, layer=0, instrument=16, key=45))
song.add_sound_stopper(tick=16, layer=0, start_layer=1, end_layer=1)
song.add_tempo_change(tick=32, layer=0, tempo=20.0)
song.save("events.nbs")

for event in pynbs.read("events.nbs").iter_events():
    if isinstance(event, pynbs.SoundStopper):
        print(event.tick, event.start_layer, event.end_layer)
    elif isinstance(event, pynbs.TempoChange):
        print(event.tick, event.tempo)
```

`tick` and `layer` are zero-based. Stopping ranges use NBS's **one-based,
inclusive** layer numbers; `start_layer=0` stops all sounds. The creation API
accepts endpoints 0–32767, matching the editor. `event.affects_layer(layer)`
accepts a zero-based layer ID and follows NBS playback behavior, including
clamping an end below the start to the start. Tempo is in ticks per second and
is quantized to 1/15 tick per second.

Both creation methods return the raw `Note`, reuse an existing event instrument
by name, and create missing layers. An occupied tick/layer raises `ValueError`.
`iter_events()` yields events in tick/layer order; raw event notes remain in
`song.notes`. `get_custom_instrument(note)` resolves an absolute note instrument
index to its custom `Instrument`, or returns `None` for a built-in/invalid index.

The four additional UI events implemented in NoteBlockStudio 3.12.0-beta.5 are
also supported. Each method returns a raw `Note`; `iter_events()` returns the
corresponding typed event:

| Creation method | Event type | NBS effect |
| --- | --- | --- |
| `add_toggle_rainbow(tick, layer)` | `ToggleRainbow` | Toggle rainbow accent colors |
| `add_color_change(tick, layer, red, green, blue)` | `ColorChange` | Set accent color (RGB integers 0–255) |
| `add_toggle_background_accent(tick, layer)` | `ToggleBackgroundAccent` | Toggle background accent |
| `add_show_save_popup(tick, layer)` | `ShowSavePopup` | Display “Song saved”; no actual save |

```python
song.add_toggle_rainbow(tick=40, layer=0)
song.add_color_change(tick=48, layer=0, red=255, green=128, blue=0)
song.add_toggle_background_accent(tick=56, layer=0)
song.add_show_save_popup(tick=64, layer=0)
song.save("visual-events.nbs")
```

These events encode their action in the custom instrument name, so they can be
stored in v0–v6 without losing event data. Older players may not implement the
effects. Toggle events flip the current state; they do not encode an explicit
on/off value. A separate custom instrument is used for each color.
Color recognition follows NBS's case-insensitive name search and fixed RGB
positions; malformed RGB values are omitted from `iter_events()` but their raw
notes and instrument names remain intact. Other event names are case-sensitive.

`Layer.lock` preserves all three states: `0` normal, `1` locked, `2` solo.
Existing `False`/`True` inputs still work. Code checking lock state should compare
to `1`, since a solo layer is also truthy.

This library reads and writes song data; it does not play audio. A consuming
player must apply tempo changes, layer solo/lock rules, and stop active sounds
on the layers selected by each `SoundStopper` event.

## Basic usage

### Reading files

You can use the `read()` function to read and parse a specific NBS file.

```python
demo_song = pynbs.read('demo_song.nbs')
```

The `read()` function returns a `pynbs` file object. These objects have several
attributes that mirror the binary structure of NBS files.

#### Header

The first attribute is `header`, the file header. It contains information about
the file.

```python
header = demo_song.header
```

Attribute                   | Type    | Details
:---------------------------|:--------|:------------------------------------------------
`header.version`            | `int`   | The NBS version this file was saved on.
`header.default_instruments`| `int`   | The amount of instruments from vanilla Minecraft in the song.
`header.song_length`        | `int`   | Stored tick position; on save, this implementation uses the highest note tick (not seconds).
`header.song_layers`        | `int`   | The number of layer records; recalculated from `len(song.layers)` on save.
`header.song_name`          | `str`   | The name of the song.
`header.song_author`        | `str`   | The author of the song.
`header.original_author`    | `str`   | The original song author of the song.
`header.description`        | `str`   | The description of the song.
`header.tempo`              | `float` | Initial tempo in ticks per second, not BPM.
`header.auto_save`          | `bool`  | Whether auto-saving has been enabled.
`header.auto_save_duration` | `int`   | The amount of minutes between each auto-save.
`header.time_signature`     | `int`   | The time signature of the song.
`header.minutes_spent`      | `int`   | The amount of minutes spent on the project.
`header.left_clicks`        | `int`   | The amount of times the user has left-clicked.
`header.right_clicks`       | `int`   | The amount of times the user has right-clicked.
`header.blocks_added`       | `int`   | The amount of times the user has added a block.
`header.blocks_removed`     | `int`   | The amount of times the user has removed a block.
`header.song_origin`        | `str`   | The file name of the original MIDI or schematic.
`header.loop`               | `bool`  | Whether the song should loop back to the start after ending.
`header.max_loop_count`     | `int`   | The amount of times to loop. 0 = infinite.
`header.loop_start`         | `int`   | The tick the song will loop back to at the end of playback.

> The [NBS specification](https://opennbs.org/nbs) provides format background. See [pynbs/file.py](pynbs/file.py) for this fork’s exact encoding behavior.

#### Notes

The `notes` attribute holds raw notes, including event notes. Direct edits may leave this list unsorted; song iteration sorts by tick and layer.

```python
first_note = demo_song.notes[0]
```

Attribute         | Type  | Details
:---------------- |:------|:------------------------------------------------
`note.tick`       | `int` | The tick at which the note plays.
`note.layer`      | `int` | The ID of the layer in which the note is placed.
`note.instrument` | `int` | The absolute instrument index: built-in index or built-in count + custom index.
`note.key`        | `int` | The key of the note. (between 0 and 87)
`note.velocity`   | `int` | The velocity of the note. (between 0 and 100)
`note.panning`    | `int` | The stereo panning of the note. (between -100 and 100)
`note.pitch`      | `int` | The detune of the note, in cents. (between -1200 and 1200)

#### Layers

The `layers` attribute holds a list of all the layers of the song in order.

```python
first_layer = demo_song.layers[0]
```

Attribute         | Type  | Details
:-----------------|:------|:------------------------
`layer.id`        | `int` | The ID of the layer.
`layer.name`      | `str` | The name of the layer.
`layer.lock`      | `int` | 0 = normal, 1 = locked, 2 = solo (boolean inputs also accepted).
`layer.volume`    | `int` | The volume of the layer.
`layer.panning`   | `int` | The stereo panning of the layer.

#### Instruments

The `instruments` attribute holds a list of all the custom instruments of the
song in order.

```python
first_custom_instrument = demo_song.instruments[0]
```

Attribute              | Type   | Details
:----------------------|:-------|:----------------------------------------------------------
`instrument.id`        | `int`  | The ID of the instrument.
`instrument.name`      | `str`  | The name of the instrument.
`instrument.file`      | `str`  | The name of the sound file of the instrument.
`instrument.pitch`     | `int`  | The pitch of the instrument. (between 0 and 87)
`instrument.press_key` | `bool` | Whether the piano should automatically press keys with the instrument when the marker passes them.

### Iterating over songs

Iterating over a `pynbs` file object yields consecutively all the chords of the song with
the associated tick.

```python
for tick, chord in demo_song:
    ...
```

`chord` is a list of all the notes that play during the tick `tick`.

### Creating new files

You can create new files using the `new_file()` function. The function lets
you specify header attributes with keyword arguments.

```python
new_file = pynbs.new_file(song_name='Hello world')
new_file.notes.append(pynbs.Note(tick=10, layer=0, instrument=0, key=45))
```

The function returns a new `pynbs` file object that you can now edit
programmatically.

### Saving files

You can use the `save()` method to encode and write the file to a specified
location.

```python
new_file.save('new_file.nbs')
```

By default, the file will be saved in the latest NBS version available.
To save the file in an older version, you can use the `version` parameter:

```python
# This will save the song in the classic format.
new_file.save('new_file.nbs', version=0)
```

(Keep in mind some of the song properties may be lost when saving in older versions.)

### Upgrading old files

The `read()` function supports versions 0–6. Write upgraded files to a separate
directory to keep your originals:

```python
from pathlib import Path
import pynbs

output = Path("converted")
output.mkdir(exist_ok=True)
for source in Path(".").glob("*.nbs"):
    pynbs.read(source).save(output / source.name, version=6)
```

## Working with custom instruments

`song.instruments` contains custom instruments only. Its list positions are
zero-based; a note uses an **absolute** instrument index. Use the loaded header’s
`default_instruments` instead of assuming every file has 20 built-ins.

```python
import pynbs

song = pynbs.new_file(song_name="Custom instrument example")
custom_id = len(song.instruments)
song.instruments.append(pynbs.Instrument(
    id=custom_id, name="Soft bell", file="soft_bell.ogg", pitch=45,
))
note = pynbs.Note(
    tick=0, layer=0,
    instrument=song.header.default_instruments + custom_id,
    key=45,
)
song.notes.append(note)
assert song.get_custom_instrument(note).name == "Soft bell"
song.save("custom.nbs")
```

An NBS file stores the sound filename, not its audio bytes. Supply the OGG file
separately to the player. Keep custom instrument and layer records in ID order;
when appending ordinary notes on a new layer, add the corresponding `Layer`
yourself. Event creation helpers create missing layers automatically.

## Format and playback compatibility

| Topic | Behavior in this fork |
| --- | --- |
| Reading | Versions 0–6; a version greater than 6 raises `ValueError`. |
| Default save | v6, even for a file loaded from an older format. Use `version=...` explicitly to choose. |
| Built-in instruments | New v6 files use 20. Older files retain their original built-in count and indices when loaded; saving as v6 does not force them to 20. |
| Downgrading | `save(..., version=5)` remaps custom indices. Newer built-ins used by the song are represented as custom instruments; their audio must be supplied separately. |
| Sound Stopper / Tempo Changer | Require v4+ on save. A v0–v3 target raises `ValueError` before opening the destination. |
| Visual events | Their name-based data can be stored in v0–v6. Whether they execute depends on the player. |
| Older formats | Unsupported fields such as per-note velocity, panning, or detune can be lost. Format conversion does not guarantee identical playback. |
| Layer state | `0` normal, `1` locked, `2` solo. Use `layer.lock == 1` for locked, not a general truthiness check. |
| Text | The current reader/writer uses **CP1252**, not UTF-8. Korean and other unrepresentable text cannot be written. |

`save()` updates the in-memory header’s version, song length, and layer count.
Use a fresh `read()` if you need a separate unmodified object. Conversion
validation is not a guarantee of an atomic write: other write errors can occur
after the destination opens. Save to a new path when preserving an original.

## Common questions

**Why does the stopper affect a different layer?**
`Note.layer` and `SoundStopper.layer` are zero-based positions, while
`start_layer` and `end_layer` are one-based target ranges. An event on layer 1
can stop layer 0 by using `start_layer=1, end_layer=1`.

**Why does adding an event raise `ValueError`?**
Only one note may occupy the requested event tick/layer. Use a dedicated event
layer or a different tick. Invalid range/RGB/tempo values and exhausted custom
instrument slots can also raise this error. Read the exception message.

**Why do event notes have unusual velocity, panning, or pitch values?**
These fields hold encoded event data. Use `iter_events()` to interpret them;
do not normalize them as ordinary audio-note values.

**Why is there no sound?**
This library does not load OGG files or play audio. Your player must resolve
sound files and handle event ordering, tempo changes, and layer state. Ordinary
song iteration includes event notes; use `iter_events()` to identify them.

**Why is Korean text not saved?**
This implementation encodes strings with CP1252. Use representable metadata;
the presence of Korean documentation does not imply Unicode file encoding support.

## Contributing

Contributions are welcome. Make sure to first open an issue discussing the problem or the new feature before creating a pull request. The project uses [`poetry`](https://python-poetry.org/).

```bash
$ poetry install
```

You can run the tests with `poetry run pytest`.

```bash
$ poetry run pytest
```

The code follows the [`black`](https://github.com/psf/black) code style. Import statements are sorted with [`isort`](https://pycqa.github.io/isort/).

```bash
$ poetry run isort pynbs tests
$ poetry run black pynbs tests
$ poetry run black --check pynbs tests
```

---

License - [MIT](LICENSE). Based on [OpenNBS/pynbs](https://github.com/OpenNBS/pynbs).
