# pynbs

[English](README.md) | 한국어

[OpenNBS/pynbs](https://github.com/OpenNBS/pynbs)를 기반으로 **NBS 파일 형식 v6와 NoteBlockStudio 3.12.0-beta.5의 이벤트 악기**를 지원하도록 확장한 포크입니다. 저장소 이름은 `pynbs-v6`이지만 Python에서는 `import pynbs`로 사용합니다.

곡의 노트·메타데이터 분석, 곡 생성과 편집, 파일 형식 변환, Sound Stopper 및 Tempo Changer를 해석하는 도구 개발에 사용할 수 있습니다. 오디오 플레이어·음원 렌더러·마인크래프트 모드는 아닙니다.

## 지원 기능

- NBS **v0~v6** 읽기와 쓰기. 새 파일과 기본 저장 형식은 **v6**입니다.
- 기본 악기 20개. 트럼펫 계열 4종의 ID는 **16~19**입니다.
- Sound Stopper, Tempo Changer 및 화면 효과 이벤트의 생성·해석 API.
- 레이어의 일반·잠금·솔로 상태 보존.
- 구버전 저장 시 기본 악기와 커스텀 악기 인덱스 변환.
- Python 표준 라이브러리만 사용하는 실행 코드.

호환성 기준은 NoteBlockStudio **3.12.0-beta.5**입니다. 이후 파일 형식의 변경까지 지원한다는 뜻은 아닙니다.

## 설치

**Python 3.8 이상, 4.0 미만**을 사용하세요. 이 포크를 설치하려면 다음 GitHub 주소를 지정합니다. 이 명령에는 Git이 필요합니다.

```bash
python -m pip install "git+https://github.com/NoteBlockMR/pynbs-v6.git"
```

`pip install pynbs`는 PyPI의 패키지를 선택하므로 이 포크의 설치를 보장하지 않습니다. 로컬에서 수정하며 사용하려면 다음과 같이 설치하세요.

```bash
git clone https://github.com/NoteBlockMR/pynbs-v6.git
cd pynbs-v6
python -m pip install -e .
```

실제로 불러오는 경로와 이벤트 API를 확인할 수 있습니다.

```python
import pynbs

print(pynbs.__file__)
assert hasattr(pynbs.File, "add_sound_stopper")
assert pynbs.new_file().header.version == 6
```

배포 환경을 고정하려면 설치 URL 뒤에 `@<commit>`을 붙여 특정 커밋을 지정하세요.

## 빠른 시작: 생성 → 저장 → 읽기

멜로디 레이어와 이벤트 레이어를 만들고, 첫 번째 레이어의 소리를 중단하는 이벤트를 추가합니다. 기본 템포가 초당 10틱이므로 템포 변경이 없다면 tick 10은 시작 후 1초입니다.

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

세 번째 원시 노트는 스토퍼 이벤트입니다. 이벤트 추가는 파일에 데이터를 기록하는 작업이며, Python에서 소리를 직접 중단하지 않습니다. 실제 동작은 플레이어가 구현해야 합니다.

## 곡 읽기와 편집

```python
import pynbs

song = pynbs.read("example.nbs")
print(song.header.song_name, song.header.tempo)
song.header.song_author = "New author"

for tick, chord in song:
    print(tick, [(note.layer, note.key) for note in chord])

song.save("edited.nbs", version=6)
```

`read()`는 `File` 객체를 반환합니다. `notes`는 이벤트를 포함한 원시 노트 목록이며 직접 수정한 순서를 유지합니다. `for tick, chord in song`은 틱과 레이어 순으로 정렬해 같은 틱의 노트들을 묶어 반환합니다. 이벤트 노트도 이 반복에 포함됩니다.

### 데이터 구조

| 속성 | 내용 |
| --- | --- |
| `song.header` | `Header`: 버전, 제목, 제작자, 초기 템포, 반복 설정 등 |
| `song.notes` | `Note` 목록: 일반 음표와 원시 이벤트 노트 |
| `song.layers` | `Layer` 목록: 레이어 이름, 상태, 볼륨, 패닝 |
| `song.instruments` | `Instrument` 목록: 커스텀 악기만 포함 |

#### Header

| 속성 | 설명 |
| --- | --- |
| `version`, `default_instruments` | 파일 형식 버전과 기본 악기 수 |
| `song_length` | 저장 시 가장 큰 노트 틱으로 계산하는 값. 초 단위가 아닙니다. |
| `song_layers` | 레이어 레코드 수. 저장 시 `len(song.layers)`로 계산합니다. |
| `song_name`, `song_author`, `original_author` | 곡 제목, 제작자, 원작자 |
| `description`, `song_origin` | 설명과 원본 MIDI/스키매틱 파일명 |
| `tempo`, `time_signature` | 초기 템포(초당 틱 수, BPM 아님), 박자 정보 |
| `loop`, `max_loop_count`, `loop_start` | 반복 여부, 반복 횟수(0은 무한), 반복 시작 틱 |
| `auto_save`, `auto_save_duration` | 자동 저장 설정과 간격(분). 이 라이브러리가 자동 저장을 실행하지는 않습니다. |
| `minutes_spent`, `left_clicks`, `right_clicks` | 편집 시간과 클릭 횟수 |
| `blocks_added`, `blocks_removed` | 추가·제거한 블록 수 |

#### Note

| 속성 | 설명 |
| --- | --- |
| `tick`, `layer` | 0부터 시작하는 틱과 레이어 ID |
| `instrument` | 절대 악기 인덱스. 기본 악기 ID 또는 기본 악기 수 + 커스텀 인덱스 |
| `key` | 음높이 0~87 |
| `velocity` | 일반 음표의 세기 0~100 |
| `panning` | 일반 음표의 패닝 -100~100 |
| `pitch` | 일반 음표의 미세 음정. 센트 단위이며 일반 사용 범위는 -1200~1200 |

이벤트는 `velocity`, `panning`, `pitch`에 별도 데이터를 인코딩합니다. 일반 음표 범위로 일괄 보정하면 이벤트가 손상될 수 있습니다.

#### Layer와 Instrument

- `Layer(id, name="", lock=0, volume=100, panning=0)`
- `Instrument(id, name, file, pitch=45, press_key=True)`

`Layer.lock`은 **0: 일반, 1: 잠금, 2: 솔로**입니다. 기존 `False`/`True` 입력도 허용하지만 솔로도 참으로 평가되므로 잠금 여부는 `layer.lock == 1`로 검사하세요.

`Instrument.id`는 커스텀 악기의 0부터 시작하는 인덱스입니다. `file`은 사운드 파일명, `pitch`는 기준 음높이, `press_key`는 재생 마커가 지날 때 피아노 건반 표시 여부입니다. 실제 저장 순서는 목록 순서이므로 레이어와 커스텀 악기는 ID 순서로 관리하세요.

## 이벤트 생성과 해석

| 생성 메서드 | `iter_events()` 결과 | 의미 |
| --- | --- | --- |
| `add_sound_stopper(tick, layer, start_layer=0, end_layer=0)` | `SoundStopper` | 지정 레이어의 활성 소리 중단 |
| `add_tempo_change(tick, layer, tempo)` | `TempoChange` | 초당 틱 수 변경 |
| `add_toggle_rainbow(tick, layer)` | `ToggleRainbow` | 무지개 강조 색상 전환 |
| `add_color_change(tick, layer, red, green, blue)` | `ColorChange` | RGB 강조 색상 설정 |
| `add_toggle_background_accent(tick, layer)` | `ToggleBackgroundAccent` | 배경 강조 전환 |
| `add_show_save_popup(tick, layer)` | `ShowSavePopup` | 저장 알림 표시. 실제 파일 저장 아님 |

```python
import pynbs

song = pynbs.new_file(song_name="Event example")
song.notes.append(pynbs.Note(tick=0, layer=0, instrument=16, key=45))
song.add_sound_stopper(tick=16, layer=1, start_layer=1, end_layer=1)
song.add_tempo_change(tick=32, layer=1, tempo=20.0)
song.add_toggle_rainbow(tick=40, layer=1)
song.add_color_change(tick=48, layer=1, red=255, green=128, blue=0)
song.add_toggle_background_accent(tick=56, layer=1)
song.add_show_save_popup(tick=64, layer=1)
song.save("events.nbs")

for event in pynbs.read("events.nbs").iter_events():
    print(type(event).__name__, event.tick, event.layer)
```

- 생성 메서드는 원시 `Note`를 반환합니다. 같은 이름의 이벤트 악기를 재사용하고 없는 레이어를 추가합니다.
- 이벤트를 놓을 틱·레이어에 이미 노트가 있으면 `ValueError`가 발생합니다. 이벤트 전용 레이어를 사용하면 관리하기 쉽습니다.
- `iter_events()`는 틱·레이어 순으로 해석된 이벤트를 반환합니다. 원시 노트는 `song.notes`에 그대로 남습니다.
- `get_custom_instrument(note)`는 노트의 커스텀 악기를 반환합니다. 기본 악기 또는 잘못된 인덱스면 `None`입니다.
- 토글 이벤트는 상태를 뒤집으며 명시적인 켜기/끄기 값을 저장하지 않습니다. 색상마다 별도 커스텀 악기가 사용됩니다.
- 색상 인식은 대소문자를 무시하는 이름 검색과 고정 RGB 위치를 따릅니다. 잘못된 RGB 이름은 해석 결과에서 제외되지만 원시 노트와 악기 이름은 보존됩니다. 나머지 이벤트 이름은 대소문자를 구분합니다.

### Sound Stopper의 레이어 번호

이벤트의 위치인 `tick`과 `layer`는 **0부터 시작**합니다. 중단 대상인 `start_layer`, `end_layer`는 **1부터 시작하며 양 끝을 포함**합니다.

- `start_layer=1, end_layer=1`: Python의 레이어 ID 0을 중단합니다.
- `start_layer=0`: 모든 소리를 중단합니다.
- 끝이 시작보다 작으면 시작 레이어만 중단합니다.
- 생성 API의 범위 입력은 0~32767입니다.
- `event.affects_layer(layer)`에는 **0부터 시작하는 레이어 ID**를 전달합니다.

### Tempo Changer

`tempo`는 BPM이 아니라 **초당 틱 수**이며, 가장 가까운 1/15틱/초 단위로 양자화됩니다. `round(tempo * 15)`가 1~32767에 들어가는 유한한 값이어야 합니다. 템포 변경이 있는 곡의 실제 재생 시간은 초기 템포만으로 계산할 수 없습니다.

## 커스텀 악기

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

파일마다 기본 악기 수가 다를 수 있으므로 커스텀 악기의 시작 ID를 20으로 고정하지 마세요. `song.header.default_instruments`를 사용하세요.

NBS 파일에는 음원 경로만 기록되며 OGG 데이터는 포함되지 않습니다. 플레이어에 음원을 별도로 제공해야 합니다. 일반 노트를 새 레이어에 직접 추가한다면 `Layer`도 직접 추가하세요. 이벤트 생성 메서드만 누락된 레이어를 자동 생성합니다.

## 저장과 버전 변환

```python
import pynbs

song = pynbs.read("events.nbs")
song.save("events-v6.nbs", version=6)
song.save("events-v5.nbs", version=5)
```

| 항목 | 동작 |
| --- | --- |
| 읽기 | v0~v6 지원. 6보다 큰 버전은 `ValueError` |
| 기본 저장 | 읽어 온 파일의 버전과 무관하게 v6. 다른 형식은 `version`으로 지정 |
| 기본 악기 수 | 새 v6 파일은 20개. 기존 파일의 악기 수와 인덱스는 읽을 때 유지되며 v6 저장만으로 20개가 되지는 않음 |
| 구버전 변환 | 커스텀 악기 인덱스를 조정하고 사용 중인 새 기본 악기를 커스텀으로 표현. 해당 음원은 별도로 필요 |
| Sound Stopper / Tempo Changer | v4 이상으로만 저장 가능. v0~v3 대상은 출력 파일을 열기 전에 `ValueError` |
| 화면 효과 이벤트 | 이름에 저장된 데이터를 v0~v6에서 보존. 실제 실행은 플레이어 지원에 따름 |
| 구버전의 제한 | 음표별 세기·패닝·미세 음정 등 지원하지 않는 정보가 유실될 수 있음 |
| 문자열 | 현재 구현은 UTF-8이 아닌 **CP1252** 사용. 한글 등 표현할 수 없는 문자는 저장 불가 |

`save()`는 메모리상의 헤더 버전·곡 길이·레이어 수를 갱신합니다. 변경 전 객체가 별도로 필요하면 파일을 다시 읽으세요. 변환 검사를 먼저 수행하더라도 다른 쓰기 오류는 파일을 연 뒤 발생할 수 있으므로 원본 보존이 필요하면 새 경로에 저장하세요.

여러 파일을 원본과 다른 폴더에 v6로 저장하는 예시입니다.

```python
from pathlib import Path
import pynbs

output = Path("converted")
output.mkdir(exist_ok=True)
for source in Path(".").glob("*.nbs"):
    pynbs.read(source).save(output / source.name, version=6)
```

## 자주 묻는 질문

**파일을 읽었는데 소리가 나지 않아요.**
이 라이브러리는 파일 데이터만 처리합니다. 음원 로딩·재생, 템포 이벤트 적용, 레이어 잠금/솔로 처리, 스토퍼 범위의 활성 소리 중단은 플레이어에서 구현해야 합니다.

**이벤트 추가 시 `ValueError`가 발생해요.**
같은 틱·레이어에 노트가 있는지 확인하세요. 잘못된 범위·RGB·템포 값이나 커스텀 악기 슬롯 부족도 원인이 될 수 있습니다. 예외 메시지에 원인이 표시됩니다.

**한글 메타데이터가 저장되지 않아요.**
현재 문자열 인코딩이 CP1252이기 때문입니다. 저장할 이름과 설명에는 해당 인코딩으로 표현 가능한 문자를 사용하세요. 한국어 문서 제공과 NBS 문자열의 Unicode 지원은 별개입니다.

**구버전 플레이어에서 같은 효과가 나오나요?**
파일에 이벤트 데이터가 남아 있어도 플레이어가 이를 해석하지 않으면 효과가 실행되지 않습니다. 새 기본 악기를 커스텀으로 바꿔 저장했다면 음원 파일도 제공해야 합니다.

## 개발과 테스트

저장소 루트에서 Poetry로 개발 의존성을 설치하고 테스트할 수 있습니다.

```bash
poetry install
poetry run pytest
poetry run isort pynbs tests
poetry run black pynbs tests
```

기능 제안과 오류는 이 저장소의 Issues에서 논의해 주세요. 자세한 데이터 구조는 [pynbs/file.py](pynbs/file.py), 형식 배경은 [NBS 명세](https://opennbs.org/nbs)를 참고하세요.

라이선스: [MIT](LICENSE). 원본 프로젝트: [OpenNBS/pynbs](https://github.com/OpenNBS/pynbs).
