from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass
from email.parser import Parser
from pathlib import Path


LICENSE_FILE_PATTERN = re.compile(
    r"^(license|licence|copying|copyright|notice|authors?)(\.|$|[-_])",
    re.IGNORECASE,
)


@dataclass
class PackageLicense:
    name: str
    version: str
    declared_license: str
    license_classifiers: list[str]
    homepage: str
    metadata_directory: str
    license_files: list[str]
    review: str


def clean_field(value: str | None) -> str:
    if not value:
        return ""
    compact = " ".join(value.split())
    if len(compact) > 180:
        return "See license text embedded in package metadata"
    return compact


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "package"


def declared_license(metadata) -> tuple[str, list[str]]:
    expression = clean_field(metadata.get("License-Expression"))
    license_field = clean_field(metadata.get("License"))
    classifiers = [
        item.removeprefix("License :: ").strip()
        for item in metadata.get_all("Classifier", [])
        if item.startswith("License :: ")
    ]
    declared = expression or license_field or "; ".join(classifiers)
    return declared or "NOT DECLARED", classifiers


def review_category(declared: str, classifiers: list[str]) -> str:
    text = " ".join((declared, *classifiers)).upper()
    if declared == "NOT DECLARED":
        return "manual review: license not declared"
    if "AGPL" in text or "AFFERO" in text:
        return "manual review: strong copyleft"
    if ("GPL" in text or "GENERAL PUBLIC LICENSE" in text) and "LGPL" not in text and "LESSER" not in text:
        return "manual review: strong copyleft"
    if any(term in text for term in ("LGPL", "LESSER GENERAL", "MPL", "MOZILLA PUBLIC", "EPL", "CDDL")):
        return "manual review: weak copyleft"
    if any(term in text for term in ("PROPRIETARY", "COMMERCIAL", "NON-COMMERCIAL")):
        return "manual review: restrictive or unclear"
    if "UNKNOWN" in text and not classifiers:
        return "manual review: restrictive or unclear"
    return "declared permissive or public-domain"


def find_license_files(dist_info: Path, metadata) -> list[Path]:
    candidates: set[Path] = set()
    for relative in metadata.get_all("License-File", []):
        path = dist_info / relative
        if path.is_file():
            candidates.add(path)
    for path in dist_info.rglob("*"):
        if path.is_file() and LICENSE_FILE_PATTERN.match(path.name):
            candidates.add(path)
    return sorted(candidates, key=lambda item: str(item).lower())


def copy_license_material(
    package_name: str,
    version: str,
    dist_info: Path,
    metadata,
    license_files: list[Path],
    destination_root: Path,
) -> list[str]:
    package_directory = destination_root / f"{safe_name(package_name)}-{safe_name(version)}"
    copied: list[str] = []
    for source in license_files:
        relative = source.relative_to(dist_info)
        destination = package_directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(str(destination.relative_to(destination_root)).replace("\\", "/"))

    license_field = metadata.get("License", "")
    if not copied and ("\n" in license_field or len(license_field) > 180):
        destination = package_directory / "METADATA-License.txt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(license_field.strip() + "\n", encoding="utf-8")
        copied.append(str(destination.relative_to(destination_root)).replace("\\", "/"))
    return copied


def audit(site_packages: Path, license_output: Path) -> list[PackageLicense]:
    if not site_packages.is_dir():
        raise FileNotFoundError(f"site-packages 폴더를 찾을 수 없습니다: {site_packages}")
    if license_output.exists():
        shutil.rmtree(license_output)
    license_output.mkdir(parents=True)

    packages: list[PackageLicense] = []
    for metadata_path in sorted(site_packages.glob("*.dist-info/METADATA"), key=lambda item: str(item).lower()):
        metadata = Parser().parsestr(metadata_path.read_text(encoding="utf-8", errors="replace"))
        name = metadata.get("Name") or metadata_path.parent.name
        version = metadata.get("Version") or "unknown"
        declared, classifiers = declared_license(metadata)
        files = find_license_files(metadata_path.parent, metadata)
        copied = copy_license_material(
            name,
            version,
            metadata_path.parent,
            metadata,
            files,
            license_output,
        )
        homepage = clean_field(metadata.get("Home-page"))
        if not homepage:
            project_urls = metadata.get_all("Project-URL", [])
            homepage = "; ".join(project_urls[:2])
        packages.append(
            PackageLicense(
                name=name,
                version=version,
                declared_license=declared,
                license_classifiers=classifiers,
                homepage=homepage,
                metadata_directory=metadata_path.parent.name,
                license_files=copied,
                review=review_category(declared, classifiers),
            )
        )
    return packages


def markdown_report(packages: list[PackageLicense], display_site_packages: str) -> str:
    counts: dict[str, int] = {}
    for package in packages:
        counts[package.review] = counts.get(package.review, 0) + 1
    lines = [
        "# Python package license inventory",
        "",
        "이 문서는 공개 배포에 사용하는 휴대용 AI Python 환경의 설치 메타데이터를 기준으로 자동 생성했다.",
        "패키지의 라이선스 선언과 실제 적용 범위가 다를 수 있으므로 `manual review` 항목은 공개 전에 별도 확인해야 한다.",
        "",
        f"- 검사 위치: `{display_site_packages}`",
        f"- 패키지 수: {len(packages)}",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"- {category}: {count}")
    lines.extend(
        (
            "",
            "동봉된 라이선스·NOTICE 파일은 배포 폴더의 `licenses/python/`에 복사한다.",
            "",
            "| Package | Version | Declared license | Review | Included license files |",
            "| --- | --- | --- | --- | --- |",
        )
    )
    for package in sorted(packages, key=lambda item: item.name.lower()):
        license_text = package.declared_license.replace("|", "\\|")
        copied = "<br>".join(package.license_files) if package.license_files else "MISSING"
        lines.append(
            f"| {package.name} | {package.version} | {license_text} | "
            f"{package.review} | {copied} |"
        )
    lines.extend(
        (
            "",
            "이 목록은 법률 자문이 아니며, 공개 Release 직전의 실제 배포 폴더로 다시 생성해야 한다.",
            "",
        )
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="휴대용 Python 환경 라이선스 목록 생성")
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--license-output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument(
        "--display-site-packages",
        default="audiosep/env/Lib/site-packages",
        help="보고서에 표시할 공개용 경로",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packages = audit(args.site_packages.resolve(), args.license_output.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        markdown_report(packages, args.display_site_packages), encoding="utf-8"
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps([asdict(package) for package in packages], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"패키지 {len(packages)}개 라이선스 목록 생성 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
