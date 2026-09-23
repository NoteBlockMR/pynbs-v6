# NoteBlockStudio 3.12.0-beta.5 호환성 점검

제공된 로컬 소스와 `../song.nbs`를 기준으로 점검했습니다.

## 반영 사항

- NBS v6 및 기본 악기 20개: Trumpet 계열 4종의 ID는 16–19입니다.
- Sound Stopper 생성·해석 API. 커스텀 악기 이름으로 식별하며 고정 ID를 가정하지 않습니다.
- Tempo Changer 생성·해석 API. 피치 절댓값 / 15가 초당 틱 수입니다.
- 레이어 상태 2(솔로) 보존. 기존 `== 1` 변환은 이 상태를 유실했습니다.
- 구버전 저장 시 커스텀 악기 ID 변환. 사용 중인 새 기본 악기는 커스텀 악기로 저장합니다.
- 피치·범위 데이터가 필요한 Sound Stopper/Tempo Changer의 v0–v3 저장은 명시적으로 거부합니다.
- 정렬되지 않은 노트의 마지막 화음 정렬 및 곡 길이 계산을 수정했습니다.
- 패키지 내부 버전 문자열을 기존 패키지 메타데이터의 1.1.0-beta.0과 맞췄습니다.

## song.nbs 결과

| 항목 | 값 |
| --- | --- |
| 포맷 / 기본 악기 수 | 6 / 20 |
| 노트 / 레이어 / 커스텀 악기 | 81,196 / 178 / 25 |
| Sound Stopper / Tempo Changer | 968 / 1 |
| 일반 / 잠금 / 솔로 레이어 | 142 / 15 / 21 |
| 최초 스토퍼 | tick 256, layer 1, 대상 레이어 42–61 (1부터 시작) |
| 템포 이벤트 | tick 0, 34.4 ticks/s |

기존 파서도 원시 노트는 읽었지만, 이벤트 의미를 제공하지 않았고 솔로
레이어를 저장할 때 잃었습니다. 수정 후 v6 재저장 결과는 원본 676,977바이트와
완전히 같습니다. v5 저장에서는 트럼펫 4종이 커스텀으로 바뀌어 악기 수가
29개가 되며 이벤트는 동일하게 유지됩니다. 원본 파일은 수정하지 않았습니다.

## sounds 경로 점검

곡에 기록된 23개 오디오 파일 경로는 `minecraft/...` 하위 경로인데,
제공된 `../sounds`는 파일이 한 폴더에 모여 있습니다. 기록된 상대 경로 그대로
찾으면 모두 일치하지 않습니다. 파일명만 비교하면 21개가 일치하며 다음은
일치하지 않습니다.

- `minecraft/dig/grass1.ogg`: 폴더에는 `glass1.ogg`가 있습니다.
- `minecraft/mob/zombie/woodbreak.ogg`: 폴더에는 `trimmed_woodbreak.ogg`가 있습니다.

두 파일이 의도한 대체 음원인지는 확인할 수 없으므로 경로와 원본 음원을
자동 변경하지 않았습니다. 실제 재생 시 경로 재배치 또는 악기 경로 수정이
필요합니다. pynbs는 오디오 재생 엔진이 아니며, 플레이어에서 이벤트를 처리해야 합니다.

## 구현 근거 (상위 NoteBlockStudio-3.12.0-beta.5 폴더)

- `scripts/macros/macros.gml`: NBS 버전 6.
- `scripts/control_create/control_create.gml`: 기본 악기 순서.
- `scripts/open_song_nbs/open_song_nbs.gml`, `scripts/save_song/save_song.gml`: 읽기/쓰기 및 구버전 악기 변환.
- `scripts/short_to_panning_velocity/short_to_panning_velocity.gml`, `scripts/panning_velocity_to_short/panning_velocity_to_short.gml`: 스토퍼 끝 레이어 인코딩.
- `scripts/draw_window_edit_sound_stopper/draw_window_edit_sound_stopper.gml`: 범위 입력 및 시작 레이어 저장.
- `scripts/remove_emitters/remove_emitters.gml`: 0이면 전체 중지, 양끝 포함, 끝값 보정.
- `scripts/control_step/control_step.gml`: 템포와 스토퍼 재생 처리.
- `scripts/control_draw/control_draw.gml`: 레이어 상태 2는 솔로.

`tests/test_events.py`에 이벤트 경계값, 구버전 변환, 솔로 상태, 실제 곡의
바이트 단위 재저장 검증을 포함했습니다. 실제 곡 테스트는 상위 폴더에
`song.nbs`가 있을 때 실행되며 곡 파일은 패키지에 복제하지 않습니다.

## 추가 화면 효과 이벤트

재생 분기와 `custom_instrument_is_event()`를 추가 점검해 다음 4종도 반영했습니다.

| 악기 이름 | 생성 API | 해석 결과 |
| --- | --- | --- |
| `Toggle Rainbow` | `add_toggle_rainbow(tick, layer)` | `ToggleRainbow` |
| `Change Color to #RRGGBB` | `add_color_change(tick, layer, red, green, blue)` | `ColorChange` |
| `Toggle Background Accent` | `add_toggle_background_accent(tick, layer)` | `ToggleBackgroundAccent` |
| `Show Save Popup` | `add_show_save_popup(tick, layer)` | `ShowSavePopup` |

무지개 강조 색상 전환, RGB 강조 색상 설정, 배경 강조 전환, 저장 알림 표시를
뜻합니다. 저장 알림은 실제 파일을 저장하지 않습니다. 이름에 데이터가 들어가므로
v0–v6 저장에서 보존되지만, 화면 효과 실행 여부는 사용하는 플레이어에 달려 있습니다.
기존 `song.nbs`에는 이 4종이 없으므로 생성한 테스트 곡으로 각 포맷의 저장·읽기를
검증합니다. 원본 곡 재저장 검증도 계속 실행합니다.

이로써 제공된 소스의 이벤트 판별·재생 분기에 있는 6종 모두 API로 지원합니다.
잘못된 RGB 이름은 원시 데이터로 보존하고 해석된 이벤트 목록에서는 제외합니다.
