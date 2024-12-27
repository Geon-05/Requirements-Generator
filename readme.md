# Requirements-Generator

Python 프로젝트를 개발할 때, 라이브러리 설치(`pip install`)와 `requirements.txt` 관리를 매번 수동으로 하다 보면 누락되거나 번거롭기 쉽습니다.  
이 스크립트는 **프로젝트 내 import된 라이브러리를 자동으로 스캔**하여,  
**누락된 라이브러리를 설치**하고 최종적으로 `requirements.txt` (또는 `requirements_make.txt`) 파일을 생성해줍니다.

---

## 주요 기능 (Features)

1. **자동 라이브러리 스캔**  
   - 프로젝트 폴더를 탐색하면서 `.py` 파일에 등장하는 모든 `import` / `from import` 문을 AST로 분석  
   - 표준 라이브러리는 제외하고, 3rd-party 라이브러리만 추려냄

2. **자동 설치**  
   - 아직 설치되지 않은 라이브러리에 대해 `pip install`을 시도  
   - (옵션) `pip` 설치 실패 시, 동적 검색 또는 사용자 입력으로 패키지명을 확인

3. **`requirements.txt` 생성**  
   - 최종적으로 설치가 완료된 라이브러리를 `패키지==버전` 형태로 기록  
   - 이후 환경 재현을 용이하게 하여, 협업 시에도 편리

4. **JSON 매핑 관리**  
   - “프로젝트 내 모듈명”과 “PyPI 패키지명”이 다른 경우, JSON 파일에 매핑 정보를 저장해 다음부터는 자동 인식

---

## 사용 방법 (Usage)

### 1) 설치/사전 준비

- Python 3.7 이상(권장), pip 최신 버전 권장  
- (선택) 가상환경(venv 또는 conda)을 만든 뒤 활성화

```bash
python -m pip install --upgrade pip
