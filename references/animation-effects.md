# brand-pptx Phase F — PowerPoint 애니메이션 효과 주입 가이드

> 출처: One Skill PPT "PowerPoint Slide Zoom Tutorial" (youtube.com/watch?v=eog6CwB5wUs)
> 대상: brand-pptx skill 확장 모듈. html2pptx로 생성된 **정적 PPTX**에 OOXML 후처리로
> 영상의 7가지 애니메이션 효과를 주입한다.

---

## 0. 왜 후처리 주입인가 (아키텍처 결정)

brand-pptx 파이프라인(HTML → html2pptx → pptxgenjs)은 **애니메이션을 전혀 지원하지 않는다.**
pptxgenjs에는 transition/animation API가 없고, html2pptx는 레이아웃만 변환한다.
PowerPoint 애니메이션은 슬라이드 XML(`ppt/slides/slideN.xml`)의 두 요소에 존재한다:

| 요소 | 역할 |
|---|---|
| `<p:transition>` | 슬라이드 전환 (모핑, 자동 전환 등) |
| `<p:timing>` | 개체 애니메이션 트리 (이동 경로, 크게/작게, 회전, 페이드 등) |

따라서 워크플로는:

```
Phase A~E (기존 brand-pptx)          Phase F (이 문서)
HTML 슬라이드 → build_pptx.js  →  inject_animations.py --manifest animations.json
            output/deck.pptx   →  output/deck-animated.pptx → 검증(validate_pptx.py)
```

`inject_animations.py`는 zip을 열어 lxml로 슬라이드 XML을 직접 수정한다.
python-pptx는 패키지 무결성 검사와 도형 추가에만 보조적으로 사용한다.

### ⚠️ XML 요소 순서 계약 (위반 시 PowerPoint 복구 프롬프트)

`<p:sld>`의 자식 순서는 스키마 고정이다. 주입 시 반드시 이 순서로 삽입한다:

```
p:cSld → p:clrMapOvr → (mc:AlternateContent | p:transition) → p:timing → p:extLst
```

`<p:cTn>`의 자식 순서: `stCondLst → endCondLst → endSync → iterate → childTnLst → subTnLst`.
모든 `cTn/@id`는 **슬라이드 timing 트리 전체에서 유일**해야 하며,
`<p:spTgt spid="N"/>`의 N은 spTree에 실재하는 도형 id여야 한다.

---

## 1. 효과별 OOXML 레시피

### 1.1 슬라이드 배경 채우기 트릭 (영상의 핵심 기법)

영상 방법: 밝은 사진을 배경 서식으로 깔고 → 어두운 사진을 덮고 → 도형 채우기를
"슬라이드 배경 채우기"로 설정 → 도형이 밝은 배경을 "뚫어 보여주는" 창이 된다.

OOXML 구현 (2단계):

**(a) 슬라이드 배경 = 밝은 이미지.** `p:cSld`의 첫 자식으로 `p:bg` 삽입 + 이미지
파트/관계 추가:

```xml
<p:bg><p:bgPr>
  <a:blipFill><a:blip r:embed="rIdBG"/><a:stretch><a:fillRect/></a:stretch></a:blipFill>
  <a:effectLst/>
</p:bgPr></p:bg>
```

**(b) 도형에 `useBgFill="1"` 속성.** `<p:sp useBgFill="1">` — spPr에는 fill 요소를
넣지 않는다 (useBgFill이 fill을 대체).

**(b′) 어두운 커버 레이어 — 필수 (검증 루프에서 확인된 버그).**
html2pptx는 캔버스 색을 도형이 아니라 **`p:bg/p:bgPr`의 solidFill**로 깐다.
따라서 (a)에서 배경을 밝은 이미지로 교체하면 어두운 캔버스가 사라져
이미지가 전면 노출되고, useBgFill 도형은 배경과 동일한 채움이라 **완벽히
위장되어 보이지 않는다** (루프 1차에서 발견). 영상의 "어두운 사진 덮기" 단계를
그대로 구현해야 한다: 밝은 이미지를 PIL로 감광(brightness ≈ 0.42)한 사본을
`p:pic`으로 **spTree 인덱스 2** (nvGrpSpPr·grpSpPr 직후 = 최하단 도형,
모든 텍스트 아래)에 삽입한다. 레이어 순서:

```
bgPr(밝은 이미지) < dark-cover pic < useBgFill 도형(창) · 텍스트
```

### 1.2 timing 트리 골격 (모든 개체 애니메이션 공통)

"이전 효과와 함께 + 슬라이드 시작 시 자동 재생" 패턴의 골격:

```xml
<p:timing><p:tnLst><p:par>
  <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
    <p:seq concurrent="1" nextAc="seek">
      <p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>
        <p:par><p:cTn id="3" fill="hold">
          <p:stCondLst>
            <p:cond delay="indefinite"/>
            <p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>  <!-- 슬라이드 시작 시 발동 -->
          </p:stCondLst>
          <p:childTnLst>
            <p:par><p:cTn id="4" fill="hold">
              <p:stCondLst><p:cond delay="0"/></p:stCondLst>
              <p:childTnLst>
                <!-- ▼ 효과 노드들 (1.3~1.7) 이 자리에 나열 -->
              </p:childTnLst>
            </p:cTn></p:par>
          </p:childTnLst>
        </p:cTn></p:par>
      </p:childTnLst></p:cTn>
      <p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
      <p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>
    </p:seq>
  </p:childTnLst></p:cTn>
</p:par></p:tnLst></p:timing>
```

공통 속성 매핑 (영상 설정 → OOXML, **외부 효과 cTn에 부여**):

| 영상 설정 | OOXML 속성 |
|---|---|
| 이전 효과와 함께 시작 | `nodeType="withEffect"` |
| 슬라이드가 끝날 때까지 반복 | `repeatCount="indefinite"` |
| 자동 반복(되돌리기) | `autoRev="1"` |
| 부드럽게 시작/끝 | `accel="50000" decel="50000"` |
| 지연 0.4초 | 효과 cTn의 `<p:stCondLst><p:cond delay="400"/></p:stCondLst>` |
| 재생 시간 2초 | 내부 cBhvr cTn의 `dur="2000"` |

### 1.3 떠다니는 둥근 사각형 (직선 경로 위)

영상 [07:19–08:37]: 둥근 사각형 + 배경 채우기 + 위로 직선 경로, 자동 되돌리기,
반복, 2초, 복사본마다 0.4초 지연.

```xml
<p:par>
  <p:cTn id="10" presetID="0" presetClass="path" presetSubtype="0"
         repeatCount="indefinite" autoRev="1" accel="50000" decel="50000"
         fill="hold" nodeType="withEffect">
    <p:stCondLst><p:cond delay="400"/></p:stCondLst>
    <p:childTnLst>
      <p:animMotion origin="layout" path="M 0 0 L 0 -0.08 E" pathEditMode="relative" ptsTypes="">
        <p:cBhvr>
          <p:cTn id="11" dur="2000" fill="hold"/>
          <p:tgtEl><p:spTgt spid="SHAPE_ID"/></p:tgtEl>
          <p:attrNameLst><p:attrName>ppt_x</p:attrName><p:attrName>ppt_y</p:attrName></p:attrNameLst>
        </p:cBhvr>
      </p:animMotion>
    </p:childTnLst>
  </p:cTn>
</p:par>
```

- 경로 좌표는 **슬라이드 크기 대비 비율** (`-0.08` = 위로 슬라이드 높이의 8%).
- 도형 생성: `prstGeom prst="roundRect"` + `<a:avLst><a:gd name="adj" fmla="val 50000"/></a:avLst>`(완전 둥글게) + `useBgFill="1"` + `rot`(기울임, 1도 = 60000).

### 1.4 위로만 자라는 막대 (크게/작게 + 보정 경로 콤보)

영상 [10:11–13:11]: 크게/작게는 중심 기준이라 위아래로 동시에 늘어남 →
**세로 125% 크게/작게 + 위로 가는 짧은 직선 경로를 같은 도형에 중첩**해 보정.
두 효과 모두 동일한 dur/autoRev/repeat/smooth/delay를 가져야 동기화된다.

```xml
<!-- 효과 A: 세로만 크게/작게 -->
<p:par><p:cTn id="20" presetID="6" presetClass="emph" presetSubtype="0"
       repeatCount="indefinite" autoRev="1" accel="50000" decel="50000"
       fill="hold" nodeType="withEffect">
  <p:stCondLst><p:cond delay="0"/></p:stCondLst>
  <p:childTnLst><p:animScale>
    <p:cBhvr><p:cTn id="21" dur="2000" fill="hold"/>
      <p:tgtEl><p:spTgt spid="BAR_ID"/></p:tgtEl></p:cBhvr>
    <p:by x="100000" y="125000"/>   <!-- 가로 100% 유지, 세로 125% -->
  </p:animScale></p:childTnLst>
<!-- ⚠️ p:by는 CT_TLPoint — x/y 속성을 가진 빈 요소다. <p:by><a:pt/></p:by> 형태로
     쓰면 ECMA-376 스키마 위반 → PowerPoint 복구 프롬프트 위험 (XSD 검증으로 발견된 버그). -->
</p:cTn></p:par>
<!-- 효과 B: 보정용 상승 경로 (막대 높이 증가분의 절반만큼) -->
<p:par><p:cTn id="22" presetID="0" presetClass="path" presetSubtype="0"
       repeatCount="indefinite" autoRev="1" accel="50000" decel="50000"
       fill="hold" nodeType="withEffect">
  <p:stCondLst><p:cond delay="0"/></p:stCondLst>
  <p:childTnLst><p:animMotion origin="layout" path="M 0 0 L 0 -0.02 E" pathEditMode="relative" ptsTypes="">
    <p:cBhvr><p:cTn id="23" dur="2000" fill="hold"/>
      <p:tgtEl><p:spTgt spid="BAR_ID"/></p:tgtEl>
      <p:attrNameLst><p:attrName>ppt_x</p:attrName><p:attrName>ppt_y</p:attrName></p:attrNameLst>
    </p:cBhvr></p:animMotion></p:childTnLst>
</p:cTn></p:par>
```

보정량 공식: `dy = -(막대높이px × 0.125) / 2 / 720` (LAYOUT_WIDE 기준 슬라이드 높이 720px).

### 1.5 떠올라 터지는 버블 (경로 + 페이드 아웃 중첩)

영상 [15:05–16:55]: 원 + 배경 채우기 → 위로 직선(부드럽게 시작/끝 **없음**) +
같은 원에 페이드(종료) 중첩. 동일 2초, 함께 시작, 반복. autoRev 없음(터지고 리셋).

```xml
<!-- 효과 A: 상승 (1.3과 동일, 단 accel/decel/autoRev 없음) -->
<!-- 효과 B: 페이드 아웃 -->
<p:par><p:cTn id="30" presetID="10" presetClass="exit" presetSubtype="0"
       repeatCount="indefinite" fill="hold" nodeType="withEffect">
  <p:stCondLst><p:cond delay="0"/></p:stCondLst>
  <p:childTnLst><p:animEffect transition="out" filter="fade">
    <p:cBhvr><p:cTn id="31" dur="2000"/>
      <p:tgtEl><p:spTgt spid="BUBBLE_ID"/></p:tgtEl></p:cBhvr>
  </p:animEffect></p:childTnLst>
</p:cTn></p:par>
```

> 일반 "끝내기-페이드"는 `<p:set>`으로 visibility를 hidden으로 잠그지만, 무한 반복
> 루프에서는 **p:set을 생략**해야 매 사이클 시작 시 도형이 다시 나타난다.

### 1.6 맞물려 도는 기어 (Spin, 시계/반시계)

영상 [17:54–21:53]: 영상은 PPT에서 아이콘 도형 병합이 안 되어 **Inkscape 우회**
(Trace Bitmap → Path Difference → SVG 재반입)를 썼다.
**코드 구현에서는 불필요** — OOXML 프리셋 지오메트리에 `gear6`, `gear9`가 내장되어
있어 도형 하나로 기어를 그릴 수 있다.

```xml
<p:sp useBgFill="1"> ... <a:prstGeom prst="gear6"><a:avLst/></a:prstGeom> ... </p:sp>
```

스핀 애니메이션 (7초, 360°, 슬라이드 끝까지 반복):

```xml
<p:par><p:cTn id="40" presetID="8" presetClass="emph" presetSubtype="0"
       repeatCount="indefinite" fill="hold" nodeType="withEffect">
  <p:stCondLst><p:cond delay="0"/></p:stCondLst>
  <p:childTnLst><p:animRot by="21600000">   <!-- 360° × 60000. 반시계 = -21600000 -->
    <p:cBhvr><p:cTn id="41" dur="7000" fill="hold"/>
      <p:tgtEl><p:spTgt spid="GEAR_ID"/></p:tgtEl>
      <p:attrNameLst><p:attrName>r</p:attrName></p:attrNameLst></p:cBhvr>
  </p:animRot></p:childTnLst>
</p:cTn></p:par>
```

두 기어가 맞물리려면: 기어1 `by="21600000"`(시계), 기어2 `by="-21600000"`(반시계),
톱니가 닿도록 배치 + 기어2를 30° 사전 회전(`rot="1800000"`)해 톱니를 엇갈리게.

### 1.7 배경 줌인 효과 (숨 쉬는 배경)

영상 [13:53–14:25]: 배경 사진에 크게/작게 110%, 부드럽게, 자동 되돌리기, 반복.
bgPr(슬라이드 배경)은 애니메이션 대상이 될 수 없으므로, **사진을 p:pic으로 슬라이드
위에 삽입**하고 (캔버스 사각형 바로 위, 텍스트 아래 z-order) 1.4의 animScale을
`x=110000 y=110000`으로 적용한다. 중심 기준 확대이므로 사진을 슬라이드보다
약간 크게(±2%) 깔면 가장자리 노출이 없다.

### 1.8 모핑(Morph) 전환 + 0초 자동 전환 (줌인 인트로)

영상 [05:49–06:19]: 섹션 첫 슬라이드(작은 원) → 0초 자동 전환 → 둘째 슬라이드
(큰 원)에 모핑. 모핑은 **도착 슬라이드**에, 자동 전환은 **출발 슬라이드**에 건다.

모핑은 MS 확장(p159)이므로 mc:AlternateContent로 감싸고 구버전용 폴백을 제공한다:

```xml
<!-- 도착 슬라이드 (slide3.xml), p:clrMapOvr 다음 위치에 -->
<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">
  <mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">
    <p:transition xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"
                  spd="slow" p14:dur="1500">
      <p159:morph option="byObject"/>
    </p:transition>
  </mc:Choice>
  <mc:Fallback>
    <p:transition spd="slow"><p:fade/></p:transition>
  </mc:Fallback>
</mc:AlternateContent>

<!-- 출발 슬라이드 (slide2.xml): 0초 후 자동 전환 -->
<p:transition advClick="1" advTm="0"/>
```

**모핑 매칭 규칙**: 두 슬라이드에서 같은 개체로 인식되어야 부드럽게 변형된다.
PowerPoint는 도형 이름이 `!!`로 시작하면 이름으로 강제 매칭한다.
→ 주입 시 양쪽 슬라이드의 대응 도형/텍스트박스 이름을 `!!sec-circle`,
`!!sec-title`처럼 **동일하게 부여**한다 (html2pptx가 만든 텍스트박스는
텍스트 내용 매칭으로 찾아 rename).

### 1.9 섹션 줌 → 하이퍼링크 내비게이션 대체 (한계와 우회)

PowerPoint 섹션 줌(Section Zoom)은 독점 확장 파트(슬라이드 썸네일 임베드 +
zoom 전용 XML)가 필요해 **수기 OOXML 생성이 비현실적**이다 (LibreOffice도 미지원).
동일한 UX는 다음 조합으로 구현한다:

1. 홈 슬라이드의 내비 도형에 슬라이드 점프 하이퍼링크:
   `<p:cNvPr ...><a:hlinkClick r:id="rIdN" action="ppaction://hlinksldjump"/></p:cNvPr>`
   (관계 타입 `.../slide`, Target=`slideN.xml`, **TargetMode 없음=내부**)
2. 섹션 첫 슬라이드 `advTm="0"` + 둘째 슬라이드 모핑 → 클릭 즉시 줌인 연출
3. 점선 연결선: `<a:ln w="88900" cap="rnd"><a:prstDash val="dash"/><a:round/></a:ln>`
   (7pt = 88900 EMU, 둥근 끝/연결 — 영상 [22:20] 설정 그대로)

---

## 2. 주입기 매니페스트 (animations.json)

`inject_animations.py`는 슬라이드 번호 → 작업 목록 매니페스트로 구동된다:

```json
{
  "slides": {
    "1": {
      "background_image": "images/home.png",
      "picture_layer": {"image": "images/home.png", "name": "bg-photo",
                        "overscan": 0.02,
                        "effects": [{"type": "grow_shrink", "sx": 1.10, "sy": 1.10,
                                     "dur": 4000, "auto_rev": true, "smooth": true,
                                     "repeat": "indefinite"}]},
      "shapes": [
        {"kind": "line", "name": "dash-1", "x": 330, "y": 420, "w": 140, "h": -60,
         "line": {"w_pt": 7, "dash": "dash", "cap": "rnd", "color": "FFFFFF"}},
        {"kind": "ellipse", "name": "nav-opportunity", "x": 180, "y": 430, "w": 150, "h": 150,
         "use_bg_fill": true, "link_to_slide": 2,
         "line": {"w_pt": 4, "color": "FFFFFF"}}
      ]
    },
    "2": {"transition": {"type": "auto", "adv_ms": 0},
          "shapes": [{"kind": "ellipse", "name": "!!sec-circle-opp", ...}],
          "rename_for_morph": [{"contains": "기회", "name": "!!sec-title-opp"}]},
    "3": {"transition": {"type": "morph", "dur_ms": 1500},
          "background_image": "images/opportunity.png",
          "shapes": [{"kind": "roundRect", "name": "float-1", "use_bg_fill": true,
                      "rot_deg": -15,
                      "effects": [{"type": "motion_line", "dy": -0.08, "dur": 2000,
                                   "auto_rev": true, "smooth": true,
                                   "repeat": "indefinite", "delay_ms": 0}]}]}
  }
}
```

효과 타입: `motion_line` (1.3) · `grow_shrink` (1.4/1.7) · `fade_out` (1.5) ·
`spin` (1.6). 도형 kind: `ellipse` · `roundRect` · `rect` · `gear6` · `gear9` · `line`.

---

## 3. 검증 프로토콜 (Phase F-Verify)

PowerPoint가 없는 환경에서의 3중 검증:

1. **패키지 무결성**: `python-pptx`로 재오픈 — zip/관계 손상 검출.
2. **스키마 계약 검사** (`validate_pptx.py`):
   - `p:sld` 자식 순서 (cSld → clrMapOvr → transition → timing)
   - timing 트리 내 `cTn/@id` 유일성
   - 모든 `spTgt/@spid`가 spTree의 실제 도형 id를 참조하는지
   - hlinksldjump 관계가 유효한 슬라이드 파트를 가리키는지
   - useBgFill 도형의 spPr에 fill 요소가 중복되지 않는지
3. **ECMA-376 XSD 검증 (가장 강력 — 필수)**: 공식 `pml.xsd`로 각 슬라이드 XML을
   `lxml.XMLSchema`로 검증한다. 검증 전에 `mc:AlternateContent`를 Fallback으로
   치환(MCE 해석)해야 strict 스키마에 걸리지 않는다. LibreOffice는 관대해서
   통과시키는 오류(예: `p:by` 자식 형태 오류)를 XSD만이 잡아낸다.
   스키마 출처: `python-openxml/python-docx` 저장소 `ref/xsd/pml.xsd`.
4. **렌더러 교차 검증**: `soffice --headless --convert-to pdf` — LibreOffice가
   XML 오류에 엄격하므로 변환 성공 = 구조 건전성의 강한 신호. PDF → PNG 렌더로
   useBgFill 트릭(배경 이미지가 도형 창으로 보이는지)을 시각 확인.

> 한계: 애니메이션 **재생**은 정적 렌더로 검증 불가. timing XML은 PowerPoint
> 원본 출력과 동일한 구조를 사용하므로 구조 검증으로 갈음한다.

---

## 4. 알려진 함정 (트러블슈팅)

| 증상 | 원인 → 처방 |
|---|---|
| PowerPoint "복구" 프롬프트 | cTn id 중복 / 요소 순서 위반 / 죽은 spid 참조 → §0 계약 + validate_pptx.py |
| 모핑이 페이드로 강등 | 대응 도형 이름 불일치 → `!!` 접두 동일 이름 부여 (§1.8) |
| useBgFill 도형이 캔버스색으로 보임 | bgPr 미설정 또는 spPr에 solidFill 잔존 → §1.1 |
| 막대가 위아래로 동시에 늘어남 | 보정 경로 누락 → §1.4 콤보 필수 |
| 버블이 한 번만 터지고 사라짐 | exit 프리셋의 p:set 포함 → 무한 루프에선 p:set 생략 (§1.5) |
| 자동 전환이 즉시 안 넘어감 | advTm을 도착 슬라이드에 설정 → **출발** 슬라이드에 설정 |
| LibreOffice 변환 실패 | mc 네임스페이스 미선언 → AlternateContent 요소에 xmlns:mc 선언 |
| 배경 이미지가 전면 노출 + useBgFill 도형이 안 보임 | html2pptx 캔버스 = bgPr 단색(도형 아님) → 어두운 커버 pic 레이어 필수 (§1.1 b′) |
| animScale에서 XSD 위반 / 복구 프롬프트 | `<p:by>`를 a:pt 자식 형태로 작성 → `<p:by x=".." y=".."/>` 속성 형태로 (§1.4) |
