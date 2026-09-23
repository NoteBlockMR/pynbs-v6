from collections import Counter
from pathlib import Path

import pytest

import pynbs


@pytest.mark.parametrize("end", [0, 61, 155, 156, 255, 256, 32767])
def test_stopper_encoding(tmp_path, end):
    song = pynbs.new_file()
    note = song.add_sound_stopper(12, 2, 42, end)
    assert note.panning + 100 == (end + 100) % 256
    assert note.velocity == (end // 256 + 100) % 256
    assert note.pitch == 42
    song.save(tmp_path / "event.nbs")
    loaded = pynbs.read(tmp_path / "event.nbs")
    assert list(loaded.iter_events()) == [pynbs.SoundStopper(12, 2, 42, end)]
    assert loaded.get_custom_instrument(loaded.notes[0]).name == "Sound Stopper"


def test_stopper_playback_range():
    event = pynbs.SoundStopper(0, 0, 42, 61)
    assert not event.affects_layer(40)
    assert event.affects_layer(41)
    assert event.affects_layer(60)
    assert not event.affects_layer(61)
    assert pynbs.SoundStopper(0, 0, 0, 0).affects_layer(100)
    assert pynbs.SoundStopper(0, 0, 42, 1).affects_layer(41)


def test_event_creation_and_sorting(tmp_path):
    song = pynbs.new_file()
    song.add_sound_stopper(20, 3)
    song.add_sound_stopper(20, 1, 1, 62)
    song.add_tempo_change(0, 0, 34.4)
    assert len(song.instruments) == 2
    song.save(tmp_path / "events.nbs")
    loaded = pynbs.read(tmp_path / "events.nbs")
    assert loaded.header.song_length == 20
    assert [(n.tick, n.layer) for n in loaded.notes] == [(0, 0), (20, 1), (20, 3)]
    assert list(loaded.iter_events())[0] == pynbs.TempoChange(0, 0, 34.4)


@pytest.mark.parametrize("version", range(6))
@pytest.mark.parametrize("use_new_instrument", [True, False])
def test_downgrade_instrument_mapping(tmp_path, version, use_new_instrument):
    song = pynbs.new_file()
    song.instruments.append(pynbs.Instrument(0, "Custom", "custom.ogg"))
    song.notes.append(pynbs.Note(1, 0, 20, 45))
    if use_new_instrument:
        song.notes.insert(0, pynbs.Note(0, 0, 19, 45))
    song.save(tmp_path / "old.nbs", version=version)
    loaded = pynbs.read(tmp_path / "old.nbs")
    assert loaded.header.default_instruments == (10 if version == 0 else 16)
    assert loaded.get_custom_instrument(loaded.notes[-1]).name == "Custom"
    if use_new_instrument:
        assert loaded.get_custom_instrument(loaded.notes[0]).name == "Oxidized Trumpet"
    assert song.notes[-1].instrument == 20
    assert len(song.instruments) == 1


def test_lossy_event_downgrade_rejected_before_open(tmp_path):
    song = pynbs.new_file()
    song.add_sound_stopper(0, 0)
    path = tmp_path / "existing.nbs"
    path.write_bytes(b"keep")
    with pytest.raises(ValueError, match="Event instruments"):
        song.save(path, version=3)
    assert path.read_bytes() == b"keep"


def test_solo_layer_roundtrip(tmp_path):
    song = pynbs.new_file()
    song.layers[0].lock = 2
    song.save(tmp_path / "solo.nbs")
    assert pynbs.read(tmp_path / "solo.nbs").layers[0].lock == 2


def test_occupied_event_position_is_rejected():
    song = pynbs.new_file()
    song.notes.append(pynbs.Note(0, 0, 0, 45))
    with pytest.raises(ValueError, match="already occupies"):
        song.add_sound_stopper(0, 0)
    assert len(song.notes) == 1
    assert song.instruments == []


@pytest.mark.parametrize("version", range(7))
def test_visual_events_roundtrip(tmp_path, version):
    song = pynbs.new_file()
    song.add_toggle_rainbow(1, 0)
    song.add_color_change(2, 0, 0, 127, 255)
    song.add_toggle_background_accent(3, 0)
    song.add_show_save_popup(4, 0)
    song.add_toggle_rainbow(5, 0)
    assert len(song.instruments) == 4
    assert song.instruments[1].name == "Change Color to #007FFF"
    assert all(ins.file == "" and not ins.press_key for ins in song.instruments)
    path = tmp_path / "visual.nbs"
    song.save(path, version=version)
    assert list(pynbs.read(path).iter_events()) == [
        pynbs.ToggleRainbow(1, 0),
        pynbs.ColorChange(2, 0, 0, 127, 255),
        pynbs.ToggleBackgroundAccent(3, 0),
        pynbs.ShowSavePopup(4, 0),
        pynbs.ToggleRainbow(5, 0),
    ]


@pytest.mark.parametrize(
    "name, expected",
    [
        ("change color TO #aBcD01", [pynbs.ColorChange(0, 0, 171, 205, 1)]),
        ("Change Color to #000000 suffix", [pynbs.ColorChange(0, 0, 0, 0, 0)]),
        ("Change Color to #ZZ0000", []),
        ("Change Color to #FFF", []),
        ("Change Color to #000000 Change Color to #FFFFFF", []),
        ("toggle rainbow", []),
        ("Ordinary custom instrument", []),
    ],
)
def test_event_name_dispatch(name, expected):
    song = pynbs.new_file()
    song.instruments.append(pynbs.Instrument(0, name, ""))
    song.notes.append(pynbs.Note(0, 0, 20, 45))
    assert list(song.iter_events()) == expected
    assert song.instruments[0].name == name
    assert len(song.notes) == 1


@pytest.mark.parametrize("color", [(-1, 0, 0), (0, 256, 0), (0, 0, 1.5)])
def test_invalid_color_does_not_add_event(color):
    song = pynbs.new_file()
    with pytest.raises(ValueError, match="RGB"):
        song.add_color_change(0, 0, *color)
    assert song.notes == []
    assert song.instruments == []


def test_supplied_song_roundtrip(tmp_path):
    source = Path(__file__).resolve().parents[2] / "song.nbs"
    if not source.exists():
        pytest.skip("User-provided song is not distributed with the package")
    song = pynbs.read(source)
    assert (len(song.notes), len(song.layers), len(song.instruments)) == (
        81196,
        178,
        25,
    )
    events = list(song.iter_events())
    assert Counter(type(e).__name__ for e in events) == {
        "SoundStopper": 968,
        "TempoChange": 1,
    }
    assert events[1] == pynbs.SoundStopper(256, 1, 42, 61)
    output = tmp_path / "roundtrip.nbs"
    song.save(output)
    assert output.read_bytes() == source.read_bytes()
    song.save(output, version=5)
    old = pynbs.read(output)
    assert list(old.iter_events()) == events
    assert old.header.default_instruments == 16
    assert len(old.instruments) == 29
