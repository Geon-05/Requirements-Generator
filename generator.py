import os
import ast
import json
import subprocess
import urllib.request
import urllib.error

# === 1) pip freeze 결과 파싱하여 설치된 패키지 목록 반환 ===
def get_installed_packages():
    """
    'pip freeze' 결과를 기반으로
    { 패키지명(소문자): 버전, ... } 형태의 딕셔너리를 반환합니다.
    """
    result = subprocess.run(['pip', 'freeze'], stdout=subprocess.PIPE, text=True)
    installed = {}
    for line in result.stdout.splitlines():
        if '==' in line:
            name, version = line.split('==', maxsplit=1)
            installed[name.lower()] = version
    return installed

# === 2) module_to_package.json 로드/저장 ===
def load_module_to_package_mapping(json_file="module_to_package.json"):
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_module_to_package_mapping(mapping, json_file="module_to_package.json"):
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)

# === 3) Python 파일에서 import 구문 추출 (AST 기반) ===
def extract_imports_from_file(filepath):
    """
    해당 파이썬 파일을 AST로 파싱하여
    import / from import 구문에 등장하는 최상위 모듈명을 추출합니다.
    """
    libraries = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return libraries  # 구문 오류가 있으면 무시

    for node in ast.walk(tree):
        # import x, y, z
        if isinstance(node, ast.Import):
            for n in node.names:
                libraries.add(n.name.split('.')[0])

        # from x.y.z import a, b
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                libraries.add(node.module.split('.')[0])

    return libraries

# === 4) 프로젝트 폴더 내 모든 py 파일 스캔 및 import 분석 ===
def scan_project_for_imports(project_path):
    project_libraries = set()
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                project_libraries.update(extract_imports_from_file(filepath))
    return project_libraries

# === 5) 표준 라이브러리 필터링 ===
def filter_standard_libraries(libraries):
    """
    추출된 라이브러리 중, Python 표준 라이브러리(예: os, sys 등)는 제외합니다.
    """
    standard_libraries = {
        'os', 'sys', 're', 'math', 'json', 'time', 'datetime', 'subprocess', 'unittest', 'random',
        'logging', 'argparse', 'collections', 'itertools', 'functools', 'operator', 'abc', 'pathlib',
        'copy', 'csv', 'ctypes', 'enum', 'hashlib', 'heapq', 'inspect', 'io', 'pickle', 'queue',
        'shutil', 'statistics', 'string', 'tempfile', 'threading', 'traceback', 'types', 'uuid',
        'concurrent', 'urllib'
    }
    return {lib for lib in libraries if lib and lib not in standard_libraries}

# === 6) 프로젝트 내부 모듈인지 확인 ===
def is_project_module(lib, project_path):
    """
    라이브러리 이름과 동일한 폴더 또는 파이썬 파일이 있으면
    프로젝트 내부 모듈로 간주 (설치 불필요)
    """
    if os.path.isdir(os.path.join(project_path, lib)):
        return True
    if os.path.isfile(os.path.join(project_path, f"{lib}.py")):
        return True
    return False

# === 7) PyPI에 패키지가 실제 존재하는지 확인(동적 검색) ===
def check_package_exists_on_pypi(package_name):
    """
    https://pypi.org/pypi/<package_name>/json 에 요청을 보내
    200 OK이면 존재하는 것으로 판단, 아니면 False 반환
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(url) as resp:
            if resp.status == 200:
                return True
    except urllib.error.HTTPError as e:
        # 404 등
        return False
    except:
        return False
    return False

# === 8) 라이브러리 설치 시도 ===
def try_install_library(lib):
    """
    lib 이름 그대로 pip install을 시도합니다.
    성공하면 True, 실패하면 False를 반환합니다.
    """
    try:
        subprocess.run(['pip', 'install', lib], check=True)
        print(f"[설치 성공] '{lib}'")
        return True
    except subprocess.CalledProcessError:
        print(f"[설치 실패] '{lib}'")
        return False

# === 9) requirements.txt 생성 ===
def generate_requirements(project_path, requirements_file, mapping_file="module_to_package.json"):
    """
    아래 로직으로 동작:
    1) 프로젝트 내 import 스캔 -> 표준 라이브러리/이미 설치/내부 모듈 제외
    2) module_to_package.json 매핑 적용
    3) 매핑 없으면:
       - (A) 모듈명 그대로 설치 시도(1차)
       - (B) 실패 시 PyPI 동적 검색 -> 존재하면 재시도
       - (C) 그래도 실패면 사용자 입력 후 설치
    4) 성공 시 JSON 매핑 정보 갱신
    5) 최종적으로 requirements_make.txt 작성
    """
    print(f"[1] 프로젝트 내 라이브러리 스캔...")
    project_libraries = scan_project_for_imports(project_path)
    filtered_libraries = filter_standard_libraries(project_libraries)

    print(f"[2] module_to_package.json 로드...")
    module_to_package = load_module_to_package_mapping(mapping_file)
    installed_packages = get_installed_packages()

    mapped_libraries = set()
    unresolved_libraries = []  # 마지막에 사용자 입력 받을 라이브러리

    # === 라이브러리 매핑 및 설치 시도 ===
    for lib in filtered_libraries:
        # 1) 프로젝트 내부 모듈이면 제외
        if is_project_module(lib, project_path):
            print(f" - '{lib}' → 프로젝트 내부 모듈이므로 스킵.")
            continue

        # 2) 이미 설치되어 있다면 스킵
        if lib.lower() in installed_packages:
            print(f" - '{lib}'은(는) 이미 설치됨 (버전: {installed_packages[lib.lower()]}).")
            mapped_libraries.add(lib)
            continue

        # 3) JSON 매핑 파일에 있으면 해당 패키지명 사용
        if lib in module_to_package:
            mapped_libraries.add(module_to_package[lib])
            continue

        # 4) 매핑 정보가 없으므로, 우선 모듈명 그대로 설치 시도(1차)
        success = try_install_library(lib)
        if success:
            # 성공하면 곧바로 매핑 반영
            module_to_package[lib] = lib
            mapped_libraries.add(lib)
        else:
            # 설치 실패 시 → PyPI 동적 검색
            if check_package_exists_on_pypi(lib):
                print(f" - PyPI에 '{lib}'이(가) 존재하므로 재시도합니다.")
                success2 = try_install_library(lib)
                if success2:
                    module_to_package[lib] = lib
                    mapped_libraries.add(lib)
                else:
                    # 재시도마저 실패하면 → 사용자 입력 대상
                    unresolved_libraries.append(lib)
            else:
                # 아예 PyPI에 없는 이름이라면 바로 사용자 입력 대상
                unresolved_libraries.append(lib)

    # === 사용자 입력 로직 ===
    for lib in unresolved_libraries:
        package_name = input(
            f"\n[사용자 입력] '{lib}' 모듈에 해당하는 PyPI 패키지명을 입력하세요 (엔터=건너뛰기): "
        ).strip()
        if package_name:
            success = try_install_library(package_name)
            if success:
                module_to_package[lib] = package_name
                mapped_libraries.add(package_name)

    # === 매핑 테이블 저장 ===
    save_module_to_package_mapping(module_to_package, mapping_file)

    # === 최종 requirements.txt 생성 ===
    print("\n[3] requirements_make.txt 생성 중...")
    installed_packages = get_installed_packages()  # 최신 freeze
    with open(requirements_file, 'w', encoding='utf-8') as f:
        # mapped_libraries에는 “실제 설치해야 할 패키지 이름”이 들어 있음
        for lib in mapped_libraries:
            lib_lower = lib.lower()
            if lib_lower in installed_packages:
                version = installed_packages[lib_lower]
                f.write(f"{lib}=={version}\n")
            else:
                # 혹시 설치 실패한 경우
                f.write(f"{lib}\n")

    print(f"\n[완료] {requirements_file} 생성이 완료되었습니다.\n"
          f"프로젝트 경로: {project_path}\n")


# === 메인 실행부 ===
if __name__ == '__main__':
    project_path = input("프로젝트 폴더 경로를 입력하세요: ").strip()
    if not os.path.isdir(project_path):
        print("유효하지 않은 폴더 경로입니다. 스크립트를 종료합니다.")
    else:
        requirements_file = os.path.join(project_path, 'requirements_make.txt')
        generate_requirements(project_path, requirements_file)
