# Sejong Dental QR 운영 가이드

## 프로젝트 개요 (개발자용)

이 도구는 세종시 치과의사회 정회원(official member)을 환자에게 신뢰성 있게 안내하고,
전화/지도/홈페이지로 자연스럽게 행동(CTA)을 유도하기 위한 정적 사이트(static site) 생성기입니다.
입력 데이터는 치과 목록과 영구 ID 매핑을 기반으로 하며, 환자 개인정보는 수집/저장하지 않습니다.

### 입력 → 처리 → 출력 파이프라인
- 입력(Input)
  - `data/clinics.xlsx`: 치과 목록(치과명/주소/전화/대표원장/홈페이지)
  - `data/id_map.csv`: 치과명 ↔ clinic_id 매핑(지속성 저장소, persistent mapping)
- 처리(Processing)
  - 치과명 정규화 + 중복 검증(중복이면 즉시 실패)
  - id_map 기반 clinic_id 유지/신규 발급
  - ACTIVE/INACTIVE 판정(이번 입력에 존재하면 ACTIVE)
- 출력(Output)
  - `docs/`: GitHub Pages 배포용 정적 사이트
  - `output/qr/`: QR 이미지(및 캡션 포함 버전)
  - `output/delivery/`, `output/outbox/`: 운영자 전달 패키지 및 ZIP 묶음
  - `output/mapping.csv`, `output/changes.csv`: 운영 리포트

### Policy (정책)
- clinic_id는 치과 기준으로 영구 고정(치과명 기준 매핑)
- ACTIVE/INACTIVE 기준은 “이번 입력(엑셀)에 존재하는가”
- 중복 치과명/필수 컬럼 누락 등은 즉시 실패(fail-fast)
- 환자 개인정보를 수집/저장하지 않음(정적 정보 + 링크 제공)

### 운영(Ops)
- `docs/`는 GitHub Pages 배포 루트
- outbox ZIP은 운영자가 신규/복귀 치과에 전달하는 패키지

### 디렉토리 구조 요약
- `docs/` (정적 사이트)
  - `docs/c/<clinic_id>/index.html`: 치과별 랜딩 페이지
  - `docs/outbox/index.html`: outbox 다운로드 페이지
- `output/` (운영 산출물)
  - `output/qr/`, `output/delivery/`, `output/outbox/zips/`
  - `output/mapping.csv`, `output/changes.csv`

운영자가 바로 실행할 수 있도록 순서대로 안내합니다.

## 1) 가상환경 생성 및 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

폰트 설치(캡션 포함 QR 생성용):

```bash
sudo apt install -y fonts-noto-cjk
```

## 2) 입력 엑셀 준비

- 파일 위치: `data/clinics.xlsx`
- 첫 번째 시트(sheet_index=0) 사용
- 헤더 컬럼명: `치과명`, `주소`, `전화`, `대표원장`, `홈페이지`
- 값은 비어있을 수 있지만, 헤더는 반드시 존재해야 합니다.

## 3) config.toml 설정

`config.toml`에서 `base_url`을 GitHub Pages URL로 설정합니다.

```toml
base_url = "https://<your-username>.github.io/<repo-name>"
```

Google Sheets에서 관리하는 경우:

```toml
clinics_source = "url"
clinics_xlsx_url = "https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=xlsx"
```

## 4) build 실행

```bash
python -m sejong_dental_qr build --config config.toml
```

## 5) preview 실행 (로컬 확인)

```bash
python -m sejong_dental_qr preview --port 8000
```

브라우저에서 `http://localhost:8000` 접속.

## 산출물 위치

- 정적 사이트: `docs/`
- QR 이미지: `output/qr/<id>.png`, `output/qr/<id>_named.png`
- 전달 패키지: `output/delivery/`
- Outbox: `output/outbox/sendlist.csv`, `output/outbox/zips/*.zip`
- 매핑 CSV: `output/mapping.csv`
- 변경 내역 CSV: `output/changes.csv`

## GitHub Pages 설정

레포지토리 Settings → Pages에서 Source를 `/docs`로 설정합니다.

## 운영 팁

`base_url`이 확정된 뒤에는 QR이 달라지므로 반드시 다시 `build`를 실행해 QR을 재생성하세요.

`build` 이후에는 `output/outbox/zips`의 ZIP만 확인해 NEW/REACTIVATED 치과에 전달하면 됩니다.

`홈페이지` 값이 `http://` 또는 `https://`로 시작하지 않으면 자동으로 `https://`를 붙여 링크합니다.

## Google Sheets 운영 가이드

1) 시트 헤더: `치과명`, `주소`, `전화`, `대표원장`, `홈페이지`
2) Google Sheets에서 File → Share → Publish to web으로 공개 설정
3) XLSX 내보내기 링크 확보 후 `clinics_xlsx_url`에 입력
4) GitHub Actions가 1시간마다 실행되어 변경이 있을 때만 Pages가 갱신됩니다.
5) Outbox 다운로드 주소: `https://<pages>/outbox/`
