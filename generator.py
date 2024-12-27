import os
import re
import subprocess
from collections import defaultdict

# 현재 설치된 라이브러리 목록 가져오기
def get_installed_packages():
    result = subprocess.run(['pip', 'list'], stdout=subprocess.PIPE, text=True)
    installed_packages = {}
    for line in result.stdout.splitlines()[2:]:  # 첫 두 줄은 헤더
        package, version = line.split()[:2]
        installed_packages[package.lower()] = version
    return installed_packages

# Python 파일에서 import 문 및 from 문 파싱
def extract_imports_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # import 문 및 from 문 모두 파싱
    imports = re.findall(r'^(?:from|import)\s+([a-zA-Z0-9_\.]+)', content, re.MULTILINE)
    libraries = set(import_.split('.')[0] for import_ in imports)  # 최상위 모듈만 추출
    return libraries

# 프로젝트 폴더 내 모든 Python 파일 색인 및 라이브러리 추출
def scan_project_for_imports(project_path):
    project_libraries = set()
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                project_libraries.update(extract_imports_from_file(filepath))
    return project_libraries

# 기본 라이브러리 필터링
def filter_standard_libraries(libraries):
    # Python 표준 라이브러리 목록
    standard_libraries = {
        'os', 'sys', 're', 'math', 'json', 'time', 'datetime', 'subprocess', 'unittest', 'random',
        'logging', 'argparse', 'collections', 'itertools', 'functools', 'operator', 'abc', 'pathlib',
        'copy', 'csv', 'ctypes', 'enum', 'hashlib', 'heapq', 'inspect', 'io', 'pickle', 'queue',
        'shutil', 'statistics', 'string', 'tempfile', 'threading', 'traceback', 'types', 'uuid'
    }
    return {lib for lib in libraries if lib not in standard_libraries}

# 필요한 라이브러리 설치 및 requirements.txt 생성
def generate_requirements(project_path, requirements_file):
    installed_packages = get_installed_packages()
    project_libraries = scan_project_for_imports(project_path)
    filtered_libraries = filter_standard_libraries(project_libraries)

    missing_libraries = {lib for lib in filtered_libraries if lib.lower() not in installed_packages}

    # 필요한 라이브러리 설치
    for lib in missing_libraries:
        subprocess.run(['pip', 'install', lib])

    # requirements.txt 생성
    with open(requirements_file, 'w') as f:
        for lib in filtered_libraries:
            version = installed_packages.get(lib.lower(), '')
            f.write(f"{lib}=={version}\n")

    print(f"requirements.txt 생성 완료: {requirements_file}")

if __name__ == '__main__':
    project_path = input("프로젝트 폴더 경로를 입력하세요: ")
    requirements_file = os.path.join(project_path, 'requirements.txt')
    generate_requirements(project_path, requirements_file)
