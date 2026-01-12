# Sejong Dental QR 운영 가이드

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
- 헤더 컬럼명: `치과명`

## 3) config.toml 설정

`config.toml`에서 `base_url`을 GitHub Pages URL로 설정합니다.

```toml
base_url = "https://<your-username>.github.io/<repo-name>"
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
